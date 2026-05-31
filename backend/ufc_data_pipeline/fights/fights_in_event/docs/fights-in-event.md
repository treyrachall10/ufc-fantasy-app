# Fights in event (`fights_in_event`)

This feature consumes **Pub/Sub** messages that point at a UFC Stats **event detail** page, downloads the HTML, parses fight rows and fighter links, upserts **`Fighters`** rows (by normalized name), bulk-inserts **`Fights`** rows for that event, and records each delivery in **`FightCreationJob`**. It is the downstream step after **`event_page_sync`** publishes new events (see related doc below).

When new fighters are created or an existing fighter receives a backfilled `profile_url`, it publishes `{fighter_id, fighter_url}` to the **`fighter-profile-jobs`** topic for the fighter profile worker. It does **not** create or update `FighterProfileScrapeJob` rows (see `backend/ufc_data_pipeline/fighters/fighter_profile/docs/fighter-profile.md`).

## Purpose

- Turn “scrape this event page” jobs into persisted `Fights` (and supporting `Fighters` rows) for fantasy/pipeline use.
- Give each Pub/Sub message a durable **`FightCreationJob`** row keyed by `pubsub_message_id` for idempotency across retries.

## Where This Lives

- Feature root: `backend/ufc_data_pipeline/fights/fights_in_event/`
- Job model: `backend/ufc_data_pipeline/models.py` (`FightCreationJob`)
- Upstream publisher: `backend/ufc_data_pipeline/events/event_page_sync/service.py`
- Related developer doc: `backend/ufc_data_pipeline/events/event_page_sync/docs/event-page-sync.md`

## Main Files

- `consumer.py` — Pub/Sub subscriber: payload parsing, HTTP fetch, `FightCreationJob` lifecycle, `scrape_fights_in_event`, `Fights` bulk create, ack/nack rules, `run_subscriber()` entry point and `__main__`.
- `parser.py` — `scrape_fights_in_event`, `ensure_fighters_exist`, row parsing helpers, and `_publish_fighter_profile_message` (Pub/Sub publish only for downstream fighter profile scraping).

## How It Works

- **Primary entry point:** `run_subscriber()` in `consumer.py`; module `__main__` calls it with logging configured.
- **Django bootstrap:** `ensure_django()` sets `DJANGO_SETTINGS_MODULE` to `ufc_fantasy.settings` and calls `django.setup()` before DB use.
- **Env guard:** `run_subscriber()` exits with a message if `GOOGLE_CLOUD_PROJECT` or `PUBSUB_FIGHTS_IN_EVENT_SUBSCRIPTION` is missing.
- **Subscription:** `SubscriberClient.subscribe(subscription_path, callback=callback)`; outer loop uses `result(timeout=5)` and `TimeoutError` to detect **idle** time (`_LAST_MESSAGE_AT`); after `_IDLE_SHUTDOWN_S` (60s) without traffic, cancels the pull future and exits.
- **Per-message `callback`:**
  - Parses JSON body → `url` (non-empty string) and `event_id` (int). Bad payloads are **acked** (dropped) after logging.
  - Loads or creates `FightCreationJob` with `pubsub_message_id=message.message_id`, `url`, `event` FK via `event_id`, `RUNNING`, etc. DB create failure → **nack**.
  - If job already `COMPLETED` or `FAILED` → **ack** (no reprocessing).
  - Else: `fetch_soup(job.url)` → `scrape_fights_in_event(soup, job.event_id)` → in `transaction.atomic()`, optional `Fights.objects.bulk_create(fights)`, then job `COMPLETED`, `completed_at`, clear `error_msg` → **ack**.
  - On exception: increment `retry_count`, set `error_msg`; if `retry_count >= 3` → `FAILED` and **ack**; else `RETRYING` and **nack** (redelivery).
- **Parser path:** `scrape_fights_in_event` collects fight rows, builds unsaved `Fights` with `event_id`, `url` from `data-link`, `bout`, `weight_class`; calls `ensure_fighters_exist` which bulk-creates missing `Fighters` and bulk-updates `profile_url` when empty; returns pending `Fights` list (may be empty).

## Data Flow

- **Input:** Pub/Sub message bytes: JSON `{"url": "<event page>", "event_id": <int>}` (same shape produced by `event_page_sync` when publishing).
- **Processing:** HTTP GET → BeautifulSoup → table rows → `Fighters` upsert logic → list of `Fights` → optional bulk insert.
- **Output (database):** `fight_creation_job` row updates; new/updated `fantasy_fighters`; new `fantasy_fights` rows when parse returns fights.
- **Output (messaging):** Publishes `{"fighter_id": <int>, "fighter_url": "<profile URL>"}` to `PUBSUB_FIGHTER_PROFILE_TOPIC` when new fighters are created or `profile_url` is backfilled.

```mermaid
flowchart TB
  subgraph in_msg [Inbound messaging]
    T["Pub/Sub topic\nPUBSUB_FIGHTS_IN_EVENT_TOPIC\n(publisher: event_page_sync)"]
    Sub["Subscription\nPUBSUB_FIGHTS_IN_EVENT_SUBSCRIPTION"]
    CB["consumer.callback"]
  end
  subgraph external [External]
    UFC["UFC Stats HTTP\njob.url"]
  end
  subgraph db [Database]
    J[("FightCreationJob")]
    F[("Fighters")]
    FT[("Fights")]
  end
  subgraph planned [Not implemented in repo]
    TProf["Topic PUBSUB_FIGHTER_PROFILE_TOPIC"]
    Svc["Fighter profile subscriber\nnot present in this repo"]
  end
  T --> Sub --> CB
  CB -->|GET| UFC
  CB -->|parse + ORM| F
  CB --> FT
  J --> CB
  F -.->|would publish if enabled| TProf
  TProf -.->|no consumer in this repo| Svc
```

## External Dependencies

- **HTTP:** `requests.get(url, timeout=60)` on the event page URL from the message (must be fetchable as given; relative URLs depend on what upstream publishes).
- **HTML parsing:** `beautifulsoup4`.
- **Django ORM:** `FightCreationJob`, `Fights`, `Fighters`, transactions, timezone.
- **GCP Pub/Sub (inbound):** `google.cloud.pubsub_v1.SubscriberClient` for the fights-in-event subscription.
- **GCP Pub/Sub (outbound):** `PublisherClient` in `_publish_fighter_profile_message` publishes `{fighter_id, fighter_url}` to `PUBSUB_FIGHTER_PROFILE_TOPIC` when new fighters need profile scraping.
- **Shared util:** `shared.utils.normalize_name` for fighter deduplication keys.

## Environment Variables

**Consumer (`consumer.py`):**

```text
GOOGLE_CLOUD_PROJECT
PUBSUB_FIGHTS_IN_EVENT_SUBSCRIPTION
```

**Fighter profile publish helper (`parser.py`):**

```text
GOOGLE_CLOUD_PROJECT
PUBSUB_FIGHTER_PROFILE_TOPIC
```

Example values are deployment-specific and not defined in this repository.

## How to Run Locally

- **Subscriber process:** `consumer.py` is runnable as a script (`if __name__ == "__main__"`). From the `backend` directory, ensure Django can import `ufc_fantasy` (usually cwd is `backend` on `sys.path`, or set `PYTHONPATH` to `backend`).

```bash
cd backend
python ufc_data_pipeline/fights/fights_in_event/consumer.py
```

Requires Django settings, database, valid GCP credentials for the subscriber client, and the env vars above. **Ask before running** if you are unsure about side effects (network, GCP, DB writes).

- **Unit tests:** `tests/test_parser.py` covers fight row parsing, winner resolution, and scrape behavior (with `_publish_fighter_profile_message` mocked).

## Common Errors / Gotchas

- **Invalid JSON or missing keys:** Payload errors are **acked**; the message is dropped (by design in `callback`).
- **Relative `url`:** If upstream sends a path-only URL, `requests.get` may fail unless the URL is absolute; behavior depends on the published payload.
- **`wc_td` indexing:** Parser uses `wc_td = wc_td[1]` after `find_all`; if fewer than two matching `td` elements exist, this can raise and drive retries/failure.
- **Debug `print` in `parser.py`:** None in current `ensure_fighters_exist` publish path; use logging if adding diagnostics.
- **Fighter profile downstream:** Consumer lives in `ufc_data_pipeline/fighters/fighter_profile/`; see that module's doc for job lifecycle owned by the fighter profile worker.

## Notes for Future Developers

- Acking/Nacking **must** be called in the callback function or it may not be respected according to PubSub's official docs.
- Align **URL** publishing in `event_page_sync` with what `requests.get` needs (absolute vs relative) if you see fetch failures in `fetch_soup`.
- Consider tests for `parse_message_payload`, `ensure_fighters_exist`, and `scrape_fights_in_event` similar to `events/tests/test_parser.py` for `event_page_sync`.
