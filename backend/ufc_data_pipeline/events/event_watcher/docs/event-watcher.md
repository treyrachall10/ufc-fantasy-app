# Event Watcher (`event_watcher`)

Discovers new completed UFC events from the UFC Stats listing, upserts missing `Events` through the main API (not Django ORM), and publishes `{"url", "event_id"}` to `fights-in-event` for the Fights In Event Scraper. One `EventSyncJob` row tracks each `watch_events` run.

## Purpose

- Replace the retired combined ORM path (`event_page_sync` / `enqueue_event_sync`) with API-backed discovery and persistence.
- Hand off new events downstream via Pub/Sub without a separate Event Scraper or `event-scrape-jobs` topic.

## Where This Lives

- Feature root: `backend/ufc_data_pipeline/events/event_watcher/`
- Shared listing parser/config: `backend/ufc_data_pipeline/events/shared/`
- Management command: `backend/ufc_data_pipeline/management/commands/watch_events.py`
- Job model: `backend/ufc_data_pipeline/models.py` (`EventSyncJob`)
- Architecture: `backend/ufc_data_pipeline/instructions/ARCHITECTURE.md` (section 1. Event Watcher)

## Main Files

- `service.py` — Orchestrates discovery, identity comparison, upsert, publish, and `EventSyncJob` status.
- `api_client.py` — Pipeline-authenticated `GET /api/events/DiscoverySource` and `PATCH /api/events/SetEvent`.
- `scraper.py` — Playwright load of the completed-events listing → BeautifulSoup.
- `publisher.py` — Publishes `{"url", "event_id"}` to `PUBSUB_FIGHTS_IN_EVENT_TOPIC`.
- `config.py` — API base URL/key, Pub/Sub topic, Playwright timeouts, listing URL re-export from `events/shared`.

## How It Works

- **Entry point:** `python manage.py watch_events` → `watch_events()` in `service.py`.
- **Run tracking:** Creates `EventSyncJob` with status `RUNNING`; marks `COMPLETED` (including no work) or `FAILED` with `error_msg`.
- **Discovery:** `GET DiscoverySource` returns stored event identities; listing scrape uses shared `parse_completed_events`.
- **Identity compare:** Unknown if URL and `(name, date)` are both absent from the discovery snapshot; duplicate listing rows collapse before upsert.
- **Persist:** Each unknown event is upserted via `PATCH SetEvent` (URL match first, then name+date on the API side).
- **Publish:** After each successful upsert, `publish_fights_in_event(event_id, url)` sends one Pub/Sub message.
- **Failures:** Upsert or publish errors fail the job/command immediately. Partial progress is recorded in `error_msg` (`completing X of Y event(s); failed on url=...`). Retries rely on idempotent SetEvent + identity comparison (no outbox).

## Data Flow

```mermaid
flowchart TB
  CMD["manage.py watch_events"]
  SVC["event_watcher.service.watch_events"]
  API["Main API\nDiscoverySource + SetEvent"]
  LIST["UFC Stats listing\nPlaywright"]
  SHARED["events/shared/parser"]
  JOB[("EventSyncJob")]
  TOPIC["Pub/Sub\nfights-in-event"]
  DOWN["fights_in_event consumer"]

  CMD --> SVC
  SVC --> JOB
  SVC --> API
  SVC --> LIST --> SHARED
  SVC -->|after each upsert| TOPIC --> DOWN
```

- **Input:** Discovery API snapshot + completed-events HTML.
- **Output (database):** Upserted `Events` via API; one `EventSyncJob` per run.
- **Output (messaging):** Absolute event URL + `event_id` on `fights-in-event`.

## External Dependencies

- **Main API:** DiscoverySource and SetEvent (Api-Key auth).
- **UFC Stats:** Completed-events listing via Playwright/Chromium.
- **GCP Pub/Sub:** `publish_json` to `PUBSUB_FIGHTS_IN_EVENT_TOPIC`.
- **Shared parser:** `ufc_data_pipeline.events.shared.parser`.

## Environment Variables

```text
PIPELINE_API_BASE_URL
PIPELINE_SERVICE_API_KEY
GOOGLE_CLOUD_PROJECT
PUBSUB_FIGHTS_IN_EVENT_TOPIC
```

Local Compose examples commonly use:

```text
PIPELINE_API_BASE_URL=http://web:8000
GOOGLE_CLOUD_PROJECT=local-project
PUBSUB_FIGHTS_IN_EVENT_TOPIC=fights-in-event
PUBSUB_EMULATOR_HOST=pubsub:8085
```

There is no `PUBSUB_EVENT_SCRAPE_*` or `event-scraper-worker` for this stage.

## How to Run Locally

```bash
docker compose exec web python manage.py watch_events
```

Requires Django settings, DB, Playwright Chromium, pipeline API key, and Pub/Sub (emulator or GCP) for publish when unknown events exist.

**Tests:**

```bash
cd backend
python manage.py test ufc_data_pipeline.events.event_watcher.tests --keepdb
```

## Common Errors / Gotchas

- Missing `PIPELINE_API_BASE_URL` / `PIPELINE_SERVICE_API_KEY` → `RuntimeError` from `api_client`.
- Listing/API/parser failures mark `EventSyncJob` `FAILED` and raise `CommandError` from the management command.
- Publish failure after a successful upsert still fails the run; retry is safe because SetEvent is idempotent.
- Must not write `fantasy.Events` through Django ORM from this package.

## Notes for Future Developers

- Listing fields (name, date, location, URL) are enough to persist an Event; do not add an Event Scraper or detail-page scrape for Event persistence.
- Shared listing code stays under `events/shared/`; do not reintroduce `events/event_page_sync/`.
- Downstream fight discovery remains `fights_in_event` (see its feature doc).
- Cloud Scheduler → Cloud Run Job packaging is covered by production scheduling readiness issues, not this package’s runtime.
