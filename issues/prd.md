## Problem Statement

The UFC data pipeline still discovers and persists events through one combined path, `sync_event_page()`, instead of the Event Watcher → Event Scraper split described in `ARCHITECTURE.md`.

That combined path:

- Creates an `EventSyncJob`
- Reads `fantasy.Events` directly through Django ORM
- Scrapes the completed-events listing
- Inserts `Events` rows directly
- Publishes straight to `fights-in-event`

Operators cannot schedule discovery independently from event persistence, cannot scale or retry event scrapes as their own jobs, and cannot keep fantasy/domain event writes behind the authenticated API boundary used by newer stages. The current date-only cutoff also skips legitimate same-date discoveries, and a failed fights-in-event publish after `Events` commit can permanently lose downstream work.

## Solution

Split the combined event sync into two stages that match the architecture:

1. **Event Watcher** — a one-shot scheduled Django management command (`watch_events`) that loads a discovery snapshot from the API, scrapes the completed-events listing, compares by stored identities, publishes one `event-scrape-jobs` message per unknown event, records the run in `EventSyncJob`, and exits.
2. **Event Scraper** — a Pub/Sub worker that owns `EventScrapeJob`, scrapes one event detail page, upserts the `Events` row through the main API, marks the job completed only after persistence succeeds, then publishes the existing `fights-in-event` payload.

Fantasy/domain event reads and writes go through pipeline-authenticated API contracts. Pipeline job rows remain ORM-owned. `sync_event_page()` / `enqueue_event_sync` are retired in the same rollout so only one discovery path remains.

## User Stories

1. As a pipeline operator, I want a scheduled Event Watcher command that runs once and exits, so that Cloud Scheduler can trigger discovery without a long-running sleep loop.
2. As a pipeline operator, I want `python manage.py watch_events` as the watcher entry point, so that local and Cloud Run Job execution use the same command.
3. As a pipeline operator, I want each watcher execution recorded in `EventSyncJob`, so that I can audit scheduled runs, failures, and retries.
4. As a pipeline operator, I want the watcher to succeed and exit cleanly when there is no work, so that empty schedules are not treated as failures.
5. As a pipeline operator, I want the watcher to call the main API for stored event identities, so that workers do not query fantasy/domain tables directly for discovery.
6. As a pipeline operator, I want the watcher to scrape `http://ufcstats.com/statistics/events/completed?page=all`, so that newly completed UFC events are discovered from the source of truth.
7. As a pipeline operator, I want listing scrape/parse logic reused from `events/shared/`, so that watcher and any transitional code share one parser contract.
8. As a pipeline operator, I want newly discovered events published to `event-scrape-jobs`, so that event persistence is decoupled from discovery.
9. As a pipeline operator, I want the watcher to publish nothing when every listing row is already known, so that idle schedules create no scraper load.
10. As a pipeline operator, I want identity comparison by URL and `(name, date)`, so that same-date events are not skipped by a date-only cutoff.
11. As a pipeline operator, I want matching URLs treated as known even if UFC renamed the event, so that renames do not endlessly republish scrape work in this stage.
12. As a pipeline operator, I want the watcher never to insert `Events` rows, so that discovery cannot bypass the Event Scraper / API boundary.
13. As a pipeline operator, I want the watcher never to publish directly to `fights-in-event`, so that downstream fight import only starts after an event is stored.
14. As a pipeline operator, I want the watcher never to call the Event Scraper Python service directly, so that stages remain independently deployable.
15. As a pipeline operator, I want an Event Scraper worker subscribed to `event-scrape-jobs-sub`, so that each discovered event is processed asynchronously.
16. As a pipeline operator, I want each scraper message to include `event_url`, `event_name`, and `event_date`, so that the worker can navigate, claim work, and log identity without another discovery pass.
17. As a pipeline operator, I want optional listing `location` in the message when already parsed, so that diagnostics remain useful even if detail parsing fails later.
18. As a pipeline operator, I want the Event Scraper to create/claim `EventScrapeJob` rows, so that scrape lifecycle is owned by the consumer that does the work.
19. As a pipeline operator, I want duplicate in-flight scrapes for the same event URL skipped when a job is already `RUNNING`, so that concurrent deliveries do not double-scrape.
20. As a pipeline operator, I want `RETRYING` scrape jobs reused, so that retries continue the same logical attempt.
21. As a pipeline operator, I want a new scrape job allowed after `COMPLETED` or `FAILED`, so that intentional reprocessing remains possible.
22. As a pipeline operator, I want the scraper to load the individual event detail page with Playwright, so that persisted event metadata comes from the event page rather than listing-only fields.
23. As a pipeline operator, I want the scraper to upsert the event through the API before completing the job, so that “completed” means the event exists in the API-owned store.
24. As a pipeline operator, I want fights-in-event published only after successful event persistence and job completion commit, so that fight import does not start against a missing event.
25. As a pipeline operator, I want publish failures after upsert to mark the scrape job `RETRYING` and nack, so that missing downstream messages can recover through idempotent reprocessing.
26. As a pipeline operator, I want invalid Pub/Sub payloads acknowledged and dropped, so that poison messages do not block the subscription.
27. As a pipeline operator, I want retryable scraper failures to nack with incremented `retry_count`, so that transient UFC Stats or API issues recover automatically.
28. As a pipeline operator, I want exhausted retries to mark the scrape job `FAILED` and ack, so that permanent failures stop looping.
29. As an API service, I want a pipeline-authenticated discovery snapshot endpoint, so that the watcher can compare against latest and stored identities in one read.
30. As an API service, I want that discovery response to include enough fields for identity comparison (`event_id`, name, date, URL) plus latest-event convenience data, so that the watcher does not need a second event read.
31. As an API service, I want a pipeline-authenticated event upsert endpoint, so that the scraper never writes `fantasy.Events` through ORM.
32. As an API service, I want upsert matching to prefer URL, then fall back to `(name, date)`, so that duplicate deliveries converge on one row.
33. As an API service, I want upsert to create missing events and update name/date/location/URL on match, so that re-scrapes refresh metadata safely.
34. As an API service, I want the upsert response to return the persisted `event_id` and URL, so that the scraper can publish the existing fights-in-event contract.
35. As an API service, I want both new event endpoints protected by `HasAPIKey` + `IsPipelineService`, so that only the pipeline service account/key can use them.
36. As a developer, I want `EventScrapeJob` introduced as its own model, so that watcher-run state and per-event scrape state are not conflated.
37. As a developer, I want `EventSyncJob` retained for watcher runs only, so that existing run history remains meaningful for the scheduled command.
38. As a developer, I want shared listing parsing extracted once under `events/shared/`, so that watcher and tests do not fork selector logic.
39. As a developer, I want `sync_event_page()` and `enqueue_event_sync` retired in the same rollout, so that operators cannot accidentally run the old combined path.
40. As a developer, I want Docker Compose and the Pub/Sub emulator initializer to create `event-scrape-jobs` / `event-scrape-jobs-sub`, so that local end-to-end discovery works.
41. As a developer, I want an `event-scraper-worker` Compose service using the existing backend image, so that local workers match production packaging.
42. As a developer, I want `.env.example` updated with the new topic/subscription variables, so that required configuration is discoverable.
43. As a developer, I want selector/contract fixtures for the listing and event-detail parsers, so that scraper regressions are caught without live UFC Stats in CI.
44. As a developer, I want consumer tests covering claim/skip/retry/exhaustion/completion and ack/nack, so that lifecycle behavior matches later pipeline stages.
45. As a developer, I want watcher tests for no stored events, no new events, one/multiple new events, same-date events, duplicate listing rows, API failure, UFC Stats timeout, parser failure, and publish failure, so that discovery edge cases are explicit.
46. As a developer, I want API tests for discovery and upsert auth/contracts, so that the worker/API boundary stays stable.
47. As a platform operator, I want the watcher packaged as Cloud Scheduler → Cloud Run Job → existing backend image → `watch_events` → exit, so that scheduling does not require a sleeping service.
48. As a platform operator, I want the PRD to document required publisher permissions, API auth env vars, Playwright/Chromium needs, and timeouts, so that Cloud Run Job setup is actionable even though repo IaC is not present yet.
49. As a platform operator, I want architecture docs updated to match the implemented watcher/scraper split, so that `ARCHITECTURE.md` stops describing unimplemented job creation by the watcher.
50. As a future maintainer, I want rename-repair and transactional outbox called out as follow-up, so that deferred reliability work is not mistaken for accidental omission.

## Implementation Decisions

### Verified current-state findings

These are repository facts, not recommendations:

- Production discovery/persistence is combined in `ufc_data_pipeline/events/event_page_sync/service.py` (`sync_event_page()`).
- Entry point today is `python manage.py enqueue_event_sync`.
- `EventSyncJob` exists; `EventScrapeJob` does not.
- No `events/event_scraper/` or `events/event_watcher/` package exists.
- Listing URL is `http://ufcstats.com/statistics/events/completed?page=all`.
- Listing parser returns events with `event_date > cutoff` only; tests explicitly assert same-date exclusion.
- Event uniqueness in DB is `(event, date)`; `url` is stored but omitted from public `EventSerializer`.
- Public `GET /events` is unordered, unauthenticated, and not a latest-event contract.
- No Event create/update/upsert API exists.
- Newer stages persist domain data through `PIPELINE_API_BASE_URL` + `Authorization: Api-Key ...` with `HasAPIKey` + `IsPipelineService`.
- There is no repository/interface layer; stage-local `api_client.py` modules are the persistence boundary.
- Downstream fights-in-event payload is `{"url": ..., "event_id": ...}` on topic `fights-in-event`.
- Local Pub/Sub resources are hard-coded in Compose `pubsub-init` and `init_pubsub_emulator`.
- Backend Docker image installs Chromium; image has no default CMD, so Cloud Run must supply the command.
- No Cloud Scheduler / Cloud Run Job / Terraform manifests exist in-repo.
- No dead-letter topic configuration exists for Python pipeline subscriptions.
- No local web-scraping skill exists under `.cursor/skills`; selector validation for this PRD is fixture/static-contract testing plus a manual pre-rollout check.

### Locked product/architecture decisions

- Retain `EventSyncJob` for each scheduled watcher execution.
- Add one pipeline-authenticated discovery snapshot endpoint; do not rely on latest-event-only reads.
- Watcher publishes Pub/Sub only; Event Scraper exclusively owns `EventScrapeJob` create/claim/status transitions.
- Event Scraper scrapes the individual event detail page, then upserts via API; message fields are navigation/identity input, not the sole persistence source.
- Event upsert matches URL first, then `(name, date)`; creates or updates metadata; returns persisted `event_id`.
- Watcher discovery uses identity-set comparison against stored URLs and `(name, date)` pairs; date-only cutoff is not the sole gate.
- URL match means known; no rename-driven republish in this PRD.
- No outbox. Mark scrape job `COMPLETED` after successful API upsert commit, then publish fights-in-event; publish failure → `RETRYING` + nack; rely on upsert idempotency.
- One-rollout replacement: retire `sync_event_page()` / `enqueue_event_sync`; put the shared listing parser in `events/shared/` without duplication.
- Topic/subscription: `event-scrape-jobs` / `event-scrape-jobs-sub`.
- Env vars: `PUBSUB_EVENT_SCRAPE_TOPIC`, `PUBSUB_EVENT_SCRAPE_SUBSCRIPTION`.
- Message payload: `event_url`, `event_name`, `event_date`; optional `location`.
- No ordering key and no dead-letter topic in this PRD.

### Final architecture

```text
Cloud Scheduler
  → Cloud Run Job (existing backend image)
    → python manage.py watch_events
      → EventSyncJob RUNNING
      → GET discovery snapshot (API)
      → Playwright listing scrape
      → identity compare
      → publish N messages to event-scrape-jobs (or none)
      → EventSyncJob COMPLETED/FAILED
      → process exits

event-scrape-jobs / event-scrape-jobs-sub
  → event-scraper-worker
    → claim/create EventScrapeJob
    → Playwright event detail scrape
    → API event upsert
    → EventScrapeJob COMPLETED
    → publish {"url","event_id"} to fights-in-event
```

### Command execution flow

- Command: `watch_events`.
- One run per invocation; no internal sleep/timer loop.
- Create `EventSyncJob(status=RUNNING)`.
- Perform discovery + optional publishes.
- On success, including zero new events: `COMPLETED` and exit 0.
- On failure: follow existing watcher-style retry/final failure semantics on `EventSyncJob`, then non-zero exit for Cloud Run visibility.
- Replace `enqueue_event_sync` rather than keeping both commands.

### Event Watcher responsibilities

- Own scheduled discovery only.
- Read stored identities through API discovery snapshot.
- Scrape and parse completed-events listing.
- Compare scraped rows to stored URL set and `(name, date)` set.
- Deduplicate duplicate listing rows before publish.
- Publish one message per unknown event to `event-scrape-jobs` via shared `publish_json`.
- Update `EventSyncJob` status/logging for start/success/skip/failure.
- Must not: insert/update `Events` via ORM, scrape event detail pages, publish fights-in-event, or invoke scraper Python APIs.

### Event Scraper responsibilities

- Consume one discovered-event message.
- Claim work with fight-stats-style rules keyed by event URL:
  - skip + ack if `RUNNING`
  - reuse latest `RETRYING`
  - create new row after `COMPLETED`/`FAILED`
- Scrape event detail page with Playwright/Chromium.
- Parse event name, date, location, and canonical URL from the detail page.
- Upsert through API.
- Mark `EventScrapeJob` `COMPLETED` only after upsert succeeds and commits.
- Publish existing fights-in-event message afterward.
- On retryable failure: `RETRYING` + nack until max retries (3), then `FAILED` + ack.
- Invalid payload: ack and drop.
- Idle shutdown / max messages follow existing worker settings.

### API contracts

#### Discovery snapshot — new endpoint required

Recommended route: `GET /api/events/DiscoverySource`

- Auth: `HasAPIKey` + `IsPipelineService`
- Purpose: watcher comparison input; API owns fantasy/domain read.
- 200 response shape:

```json
{
  "latest_event": {
    "event_id": 123,
    "event": "UFC Fight Night: Example",
    "date": "2026-07-12",
    "url": "http://ufcstats.com/event-details/..."
  },
  "events": [
    {
      "event_id": 123,
      "event": "UFC Fight Night: Example",
      "date": "2026-07-12",
      "url": "http://ufcstats.com/event-details/..."
    }
  ]
}
```

- Empty DB: `latest_event: null`, `events: []`, status 200.
- Include every stored event identity needed for authoritative comparison. If payload size becomes a concern later, a follow-up may narrow to a date window; this PRD keeps the full identity set because same-date and backfill gaps make latest-only unsafe.
- Do not reuse public `GET /events` for pipeline auth/contract reasons and because it omits `url` and has no ordering guarantees.

#### Event upsert — new endpoint required

Recommended route: `POST /api/events/SetEvent` or `PATCH /api/events/SetEvent`

- Auth: `HasAPIKey` + `IsPipelineService`
- Request:

```json
{
  "event": "UFC Fight Night: Example",
  "date": "2026-07-12",
  "location": "Las Vegas, Nevada, USA",
  "url": "http://ufcstats.com/event-details/..."
}
```

- Match order: non-empty URL first; else `(event, date)`.
- Create when unmatched; update name/date/location/url when matched.
- 200/201 response must include at least `event_id` and `url`.
- Conflict/validation errors return 400 with `detail`; auth failures follow existing pipeline endpoint behavior.
- API owns uniqueness constraint handling; scraper treats successful upsert as idempotent.

### Repository / API client architecture

- No new repository abstraction layer.
- Watcher gets `api_client.get_discovery_source()`.
- Scraper gets `api_client.upsert_event(payload)`.
- Both use `PIPELINE_API_BASE_URL` and `PIPELINE_SERVICE_API_KEY`.
- Pipeline job models remain direct ORM.

### Pub/Sub design

| Item | Value |
| --- | --- |
| Topic | `event-scrape-jobs` |
| Subscription | `event-scrape-jobs-sub` |
| Topic env | `PUBSUB_EVENT_SCRAPE_TOPIC` |
| Subscription env | `PUBSUB_EVENT_SCRAPE_SUBSCRIPTION` |
| Publisher | Event Watcher |
| Consumer entry | `python -m ufc_data_pipeline.events.event_scraper.event_scraper_worker` |
| Downstream topic | existing `fights-in-event` via `PUBSUB_FIGHTS_IN_EVENT_TOPIC` |
| Local emulator | add topic/sub to Compose `pubsub-init` and `init_pubsub_emulator` |
| Ordering | none |
| Dead letter | none in this PRD |
| Ack/nack | invalid/RUNNING-skip/terminal fail → ack; retryable → nack |

### Job ownership and status transitions

- `EventSyncJob`: one row per watcher command execution; not tied to a single event.
- `EventScrapeJob`: new `BaseJobModel` subclass with event URL (and parsed identity fields as useful), indexed for active-job lookup by URL/status.
- Watcher never creates scrape jobs.
- Scraper never creates watcher jobs.
- Scraper status transitions mirror fight-stats/career-stats conventions.

### Idempotency and deduplication rules

- Watcher known-event rule: scraped URL in stored URL set **or** `(name, date)` in stored pair set → skip.
- Duplicate listing rows collapse to one publish.
- Multiple events on one date: each unknown identity publishes separately.
- UFC rename with same URL: known; no republish.
- Same date / different name: unknown if URL also unknown → publish.
- Duplicate Pub/Sub delivery: scraper RUNNING skip or RETRYING reuse; API upsert converges rows.
- Persistence then publish failure: retry whole scrape path; upsert remains safe; fights-in-event consumer has its own job row by message id / existing conventions.
- Do not treat `event_date > latest.date` as sufficient.

### Retry and failure behavior

- Watcher: retain durable `EventSyncJob` failure/retry visibility; command failure should surface to Cloud Run Job.
- Scraper: max retries 3; RETRYING + nack; FAILED + ack.
- API/network/UFC Stats/parser/publish failures are retryable unless payload is invalid.
- No transactional outbox in this stage.

### Scheduling and Cloud Run deployment

Documented target:

```text
Cloud Scheduler → Cloud Run Job → existing backend image → python manage.py watch_events → exit
```

Required runtime concerns even though IaC is absent from the repo:

- Command override on the Cloud Run Job.
- Service account with Pub/Sub publish on `event-scrape-jobs` and network access to UFC Stats + API.
- Env: `GOOGLE_CLOUD_PROJECT`, `PUBSUB_EVENT_SCRAPE_TOPIC`, `PIPELINE_API_BASE_URL`, `PIPELINE_SERVICE_API_KEY`, DB settings already used by manage.py commands.
- Playwright/Chromium already installed in `backend/Dockerfile`.
- Timeout must cover listing page fetch + publish fanout; no idle long-poll.
- Job retries are platform-level; application still writes `EventSyncJob` outcomes.
- Event Scraper remains a pull worker like other Compose workers; this PRD does not redesign pull workers into push HTTP services.

### Proposed module shape

Recommended packages after conventions inspection:

```text
events/
  shared/                     # shared completed-events listing parser + listing URL/config
    parser.py
    config.py
    tests/
  event_watcher/
    service.py
    api_client.py
    scraper.py
    publisher.py
    config.py
    management/commands/watch_events.py   # or fantasy/management/commands if that remains the established command home
    tests/
    docs/
  event_scraper/
    event_scraper_worker.py
    consumer.py
    service.py
    api_client.py
    scraper.py
    parser.py
    publisher.py
    config.py
    tests/
    docs/
```

The shared listing parser must live under `events/shared/`, not inside `event_watcher` or `event_scraper`. Watcher imports from `events.shared`; do not duplicate listing selectors in either feature package.

Combine other files when a split adds no value. Prefer the existing management-command home under `fantasy/management/commands/` if that remains the repo convention for pipeline commands; keep watcher business logic inside `events/event_watcher/`.

Retire `events/event_page_sync/` as the production path once watcher/scraper land.

### Migration / model changes

- Add `EventScrapeJob` migration under `ufc_data_pipeline`.
- Keep `EventSyncJob` table/model.
- No change required to `fantasy.Events` uniqueness for this PRD; upsert must honor `(event, date)` and URL matching rules carefully when updating names.
- Update architecture docs to say watcher publishes scrape work rather than creating scrape job rows.

### Rollout sequence

1. Add API discovery + upsert endpoints and tests.
2. Extract shared listing parser into `events/shared/` and add watcher command/tests; stop using combined sync in docs/commands.
3. Add `EventScrapeJob`, scraper worker, Compose/emulator/env wiring, consumer/service tests.
4. Point local operators at `watch_events` + `event-scraper-worker`.
5. Delete or hard-disable `sync_event_page()` / `enqueue_event_sync`.
6. Update `ARCHITECTURE.md` and feature docs.
7. Configure Cloud Scheduler + Cloud Run Job out of repo if needed.
8. Manual pre-rollout selector verification against live UFC Stats listing and one event detail page.

## Testing Decisions

Good tests assert external behavior: HTTP contracts, publish payloads, job status transitions, ack/nack, and command exit behavior. Avoid locking private helper structure.

Modules under test:

- Shared listing parser under `events/shared/`
- Watcher service / command
- Event Scraper consumer and service
- Discovery and upsert API endpoints
- API clients

Prior art:

- `events/tests/test_parser.py` (migrate/replace into `events/shared/tests/` when the shared package lands)
- `fighters/fighter_profile/tests/`
- `fights/fight_stats/tests/`
- `fighters/career_stats/tests/`
- `fantasy/score_fight/tests/`
- `api/tests/test_career_stats_source.py` and related pipeline API tests
- `fantasy/tests/test_enqueue_commands.py`

Required scenarios:

| Scenario | Level |
| --- | --- |
| No stored events | Watcher service |
| No newly discovered events | Watcher service + command |
| One new event | Watcher service |
| Multiple new events | Watcher service |
| Multiple events on same date | Watcher service + parser |
| Duplicate listing rows | Watcher service |
| Existing event matching name+date | Watcher service |
| Existing event matching URL | Watcher service |
| Same date, different name, unknown URL | Watcher service |
| API discovery failure | Watcher service |
| UFC Stats timeout | Watcher scraper/service |
| Parser failure | Parser/service |
| Pub/Sub publish failure | Watcher service |
| Duplicate Pub/Sub delivery / RUNNING skip | Scraper consumer |
| Event upsert success then downstream publish failure | Scraper consumer |
| Retry exhaustion | Scraper consumer |
| Command exits successfully with no work | Command test |
| Discovery/upsert auth and body contracts | API tests |
| Upsert create vs URL match vs name/date match | API tests |

No live UFC Stats calls in CI. Use HTML fixtures for selectors. Manual pre-rollout selector check is required because no in-repo scraping skill was available to automate live validation.

## Out of Scope

- Implementing code in this PRD task.
- Rename-driven metadata repair by the watcher.
- Transactional outbox / publish-marker table.
- Dead-letter topics and Pub/Sub retry-policy IaC.
- Redesigning fights-in-event ORM persistence into API-owned writes.
- DB Event Watcher, Fight Results Watcher, or later pipeline stages.
- Converting pull workers to Cloud Run push/HTTP consumers.
- Checking in Cloud Scheduler / Cloud Run Terraform in this PRD’s implementation unless a later issue explicitly adds it.
- Legacy `refresh_ufc_data` / CSV bulk populate path changes beyond noting it remains legacy.

## Further Notes

### Open risks

- Event detail-page selectors are not implemented yet; listing selectors exist but docs for `event_page_sync` are stale relative to Playwright usage.
- Relative vs absolute event hrefs are not guaranteed by current parser tests; scraper/upsert should normalize to an absolute UFC Stats URL before identity comparison and persistence.
- Full discovery identity payload may grow large over years of events; revisit windowing only if measured as a problem.
- Upsert name changes can interact with the `(event, date)` unique constraint if URL match updates a name onto another row’s pair; API must define deterministic conflict handling and tests.
- Fights-in-event still lacks strong logical idempotency by `event_id`; scraper retries that republish new Pub/Sub messages can create duplicate fight-import work until that stage is hardened.
- Pull-based Event Scraper will not auto scale from zero on Cloud Run Services without a separate worker runtime strategy.

### Follow-up work

- Optional rename-repair job or watcher metadata refresh.
- Outbox if publish-after-complete loss becomes operationally painful.
- Harden fights-in-event idempotency by `event_id`.
- Add deployment manifests for Scheduler + Cloud Run Job.
- Consider discovery snapshot pagination/windowing if payload size warrants it.
- Update stale `event_page_sync` docs during deletion/retirement.
