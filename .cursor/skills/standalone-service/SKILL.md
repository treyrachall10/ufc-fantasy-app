---
name: standalone-service
description: Implements isolated pipeline services with worker, consumer, service, and parser layers. Use when adding a new UFC data pipeline stage, microservice portion, Pub/Sub worker, scraper service, or background job processor in ufc_data_pipeline.
---

# Standalone Service Implementation

Use when adding a new isolated pipeline stage or worker to `backend/ufc_data_pipeline/`.

Each service owns **one clear job** (discover events, scrape fights in an event, scrape a fighter profile, etc.). Inspect an existing feature folder before creating files.

**Reference implementations:**
- Entry + consumer worker: `fighters/fighter_profile/` (`fighter_profile_worker.py` → `consumer.py` → `service.py`)
- Scheduled one-shot + API upsert + publish: `events/event_watcher/` (`watch_events` → `service.py` → `api_client` / `publisher`)
- Consumer + downstream publish: `fights/fights_in_event/` (consumes event jobs, publishes fighter-profile messages)

For Pub/Sub ack/nack, retries, and callback rules, also read [pubsub-processing.md](../pubsub/pubsub-processing.md). For scraping, read [scraper-implementation.md](../web-scraping/scraper-implementation.md).

---

## Folder Layout

Place each feature under a domain path inside `ufc_data_pipeline/`:

```text
ufc_data_pipeline/<domain>/<feature_name>/
├── <feature>_worker.py   # process entry (Pub/Sub workers only)
├── consumer.py           # Pub/Sub subscriber + callback (if message-driven)
├── service.py            # orchestration: fetch, parse, persist/publish
├── parser.py             # pure HTML/data parsing (no DB, no HTTP clients)
├── config.py             # URLs, selectors, timeouts, topic/subscription names
├── api_client.py         # optional — HTTP calls to main API service
├── tests/
└── docs/<feature>.md     # optional feature doc
```

Job tracking models live in `ufc_data_pipeline/models.py` (extend `BaseJobModel`). Ask before adding or changing models/migrations.

---

## Layer Responsibilities

| Layer | Owns | Must not own |
|-------|------|--------------|
| **Worker** | Django bootstrap, logging, SIGTERM/SIGINT shutdown, call `run_subscriber()` | Business logic, scraping, parsing, DB writes, ack/nack |
| **Consumer** | Payload parse, job load/create, call service, job status updates, ack/nack, `run_subscriber()` loop | Heavy scraping, HTML parsing, bulk persistence logic |
| **Service** | Fetch page data, invoke parser, persist via ORM or `api_client`, publish downstream messages | Pub/Sub callback wiring, signal handling |
| **Parser** | Pure transforms (BeautifulSoup → dataclasses/dicts) | Playwright, requests, Django ORM, Pub/Sub, API calls |
| **api_client** | Authenticated HTTP to main app API | Scraping or job lifecycle |

---

## Worker Entry Point

One worker file per long-running Pub/Sub process. Keep it thin.

```python
# <feature>_worker.py
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ufc_fantasy.settings")
django.setup()

def main() -> None:
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)
    run_subscriber()  # from consumer.py
```

Register in `docker-compose.yml` as `python -m ufc_data_pipeline.<domain>.<feature>.<feature>_worker`.

Scheduled or one-shot jobs (no long-running subscriber) may expose a `service.py` function instead of a worker — see `event_watcher/watch_events()` and `python manage.py watch_events`.

---

## Consumer Pattern

Module docstring: expected JSON payload, required env vars, ack/nack ownership note.

```python
def parse_message_payload(raw: bytes) -> ...:
    """Parse and validate; raise on bad shape."""

def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    # 1. parse payload — invalid → log, ack (drop)
    # 2. load/create job row — skip duplicates per stage rules
    # 3. call service function (e.g. process_fighter_profile(...))
    # 4. update job status in transaction
    # 5. ack on success / max retries; nack when retries remain

def run_subscriber() -> None:
    ensure_django()
    # validate PROJECT_ID + SUBSCRIPTION_ID from config
    # subscribe + idle shutdown loop (see fighter_profile consumer)
```

All `ack()` / `nack()` calls stay in `callback` only.

---

## Service Pattern

Service functions are the unit of work the consumer calls.

```python
def process_fighter_profile(fighter_id: int, fighter_url: str) -> None:
    soup = fetch_profile_soup(fighter_url)       # fetch lives here or in helper
    profile_data = parse_fighter_profile(soup)   # parser.py
    payload = profile_data_to_api_payload(profile_data)
    api_client.update_fighter_profile(fighter_id, payload)  # not direct ORM on main app tables
```

Publisher-side orchestration (no consumer) follows the same split: fetch + parse in service, persist via API, then publish:

```python
# event_watcher/service.py — after successful SetEvent upsert:
publish_fights_in_event(event_id, event_url)  # {"url", "event_id"} → fights-in-event
```

---

## Service Boundaries

- **Do not** import another feature's internal functions (`service`, `parser`, private helpers).
- **Do** trigger downstream work by publishing a Pub/Sub message with a documented JSON contract, or call an approved API endpoint.
- **Do not** read/write main fantasy application tables directly — use `api_client` (see `fighters/fighter_profile/api_client.py`).
- Pipeline-owned tables (`ufc_data_pipeline` job models, pipeline staging data) may use Django ORM from the service layer.
- Downstream consumers create their own job rows; upstream publishers publish messages only (see fights_in_event → fighter_profile flow).

---

## Config

Centralize in `config.py`:

- Source URLs and CSS ready selectors
- Timeouts, retry limits, idle shutdown seconds
- Pub/Sub topic/subscription IDs (read from env with sensible local defaults)
- API base URL and service key env vars

---

## Job Tracking

Extend `BaseJobModel` for new job tables. Consumer owns status transitions:

`RUNNING` → `COMPLETED` | `RETRYING` | `FAILED`

Follow project retry rules: increment `retry_count`, nack while retries remain, ack when `FAILED` after max retries. Dedup rules are stage-specific (document in the feature doc).

---

## Implementation Checklist

Before coding, inspect the nearest existing feature and confirm:

- [ ] Single responsibility — one job type, one subscription or one scheduled entry
- [ ] Worker is startup/shutdown only (Pub/Sub workers)
- [ ] Consumer delegates work to `service.py`
- [ ] Parser is pure — no side effects
- [ ] Writes to main app go through `api_client` or approved API
- [ ] Downstream handoff uses Pub/Sub or API, not cross-imports
- [ ] `config.py` holds env-driven settings
- [ ] Tests cover parser, payload parse, and callback/job lifecycle
- [ ] Schema changes approved before migrations

---

## Anti-Patterns

- Scraping or large ORM logic inside `callback`
- Business logic in the worker file
- Calling `fighters.fighter_profile.service.process_fighter_profile` from another feature — publish `{fighter_id, fighter_url}` instead
- Direct `Fighters.objects.update(...)` from pipeline when an API endpoint exists
- Mixing publisher and subscriber setup in one file without clear separation
