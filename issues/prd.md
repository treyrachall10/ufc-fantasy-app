## Problem Statement

The UFC data pipeline still discovers and persists events through one combined path, `sync_event_page()`, which reads and writes `fantasy.Events` through Django ORM and publishes straight to `fights-in-event`.

Operators need a scheduled, one-shot Event Watcher that:

- Loads stored event identities through the authenticated API
- Scrapes the completed-events listing
- Upserts each missing Event through the API (listing fields are sufficient)
- Publishes `{"url", "event_id"}` to `fights-in-event`
- Exits

A separate Event Scraper stage, `EventScrapeJob`, `event-scrape-jobs` topic, and per-event detail-page scrape are unnecessary: the listing already provides name, date, location, and URL.

## Solution

Replace the combined ORM sync with a single scheduled stage:

```text
watch_events
→ load stored event identities through the API
→ scrape the completed-events listing
→ identify unknown events
→ upsert each missing Event through the API
→ publish {"url", "event_id"} to fights-in-event
→ exit
```

- `EventSyncJob` remains one durable row per `watch_events` execution.
- Fantasy/domain event reads and writes go through pipeline-authenticated API contracts only.
- Downstream fight import continues on the existing `fights-in-event` topic.
- `sync_event_page()` / `enqueue_event_sync` are retired so only one discovery path remains.
- No `EventScrapeJob`, no `event-scrape-jobs`, no `event-scraper-worker`, and no event-detail scrape for Event persistence.

## User Stories

1. As a pipeline operator, I want a scheduled Event Watcher command that runs once and exits, so that Cloud Scheduler can trigger discovery without a long-running sleep loop.
2. As a pipeline operator, I want `python manage.py watch_events` as the watcher entry point, so that local and Cloud Run Job execution use the same command.
3. As a pipeline operator, I want each watcher execution recorded in `EventSyncJob`, so that I can audit scheduled runs, failures, and retries.
4. As a pipeline operator, I want the watcher to succeed and exit cleanly when there is no work, so that empty schedules are not treated as failures.
5. As a pipeline operator, I want the watcher to call the main API for stored event identities, so that workers do not query fantasy/domain tables directly for discovery.
6. As a pipeline operator, I want the watcher to scrape `http://ufcstats.com/statistics/events/completed?page=all`, so that newly completed UFC events are discovered from the source of truth.
7. As a pipeline operator, I want listing scrape/parse logic reused from `events/shared/`, so that watcher and tests share one parser contract.
8. As a pipeline operator, I want each unknown listing row upserted through the API using listing name, date, location, and URL, so that Event persistence does not require a detail-page scrape.
9. As a pipeline operator, I want the watcher to publish nothing and upsert nothing when every listing row is already known, so that idle schedules create no load.
10. As a pipeline operator, I want identity comparison by URL and `(name, date)`, so that same-date events are not skipped by a date-only cutoff.
11. As a pipeline operator, I want matching URLs treated as known even if UFC renamed the event, so that renames do not endlessly re-upsert or republish in this stage.
12. As a pipeline operator, I want the watcher never to insert `Events` rows through ORM, so that fantasy/domain persistence stays behind the API.
13. As a pipeline operator, I want `{"url", "event_id"}` published to `fights-in-event` only after a successful upsert returns those values, so that fight import starts against a stored event.
14. As a pipeline operator, I want one fights-in-event message per successfully upserted unknown event, so that downstream work stays per-event.
15. As a pipeline operator, I want persistence or publish failures surfaced on `EventSyncJob` with a failing command exit, so that Cloud Run/Scheduler retries are actionable.
16. As an API service, I want a pipeline-authenticated discovery snapshot endpoint, so that the watcher can compare against latest and stored identities in one read.
17. As an API service, I want that discovery response to include `event_id`, name, date, and URL for every stored event plus `latest_event`, so that identity comparison does not need a second read.
18. As an API service, I want a pipeline-authenticated event upsert endpoint, so that the watcher never writes `fantasy.Events` through ORM.
19. As an API service, I want upsert matching to prefer URL, then fall back to `(event, date)`, so that duplicate deliveries converge on one row.
20. As an API service, I want upsert to create missing events and update name/date/location/URL on match, so that re-runs refresh metadata safely.
21. As an API service, I want the upsert response to return the persisted `event_id` and URL, so that the watcher can publish the existing fights-in-event contract.
22. As an API service, I want both event endpoints protected by `HasAPIKey` + `IsPipelineService`, so that only the pipeline service key can use them.
23. As a developer, I want `EventSyncJob` retained for watcher runs only, so that run history remains meaningful for the scheduled command.
24. As a developer, I want no `EventScrapeJob` model or migration, so that watcher-run state is not conflated with a removed scraper stage.
25. As a developer, I want shared listing parsing under `events/shared/`, so that selector logic is not forked.
26. As a developer, I want `sync_event_page()` and `enqueue_event_sync` retired in the same rollout, so that operators cannot accidentally run the old combined path.
27. As a developer, I want no `event-scrape-jobs` topic/subscription or `event-scraper-worker`, so that local Compose stays aligned with the simplified architecture.
28. As a developer, I want `.env.example` to document only the existing fights-in-event publish vars needed by the watcher, so that configuration stays discoverable.
29. As a developer, I want selector/contract fixtures for the listing parser, so that regressions are caught without live UFC Stats in CI.
30. As a developer, I want watcher tests for no-work, one/multiple new events, same-date events, duplicate listing rows, identity matches, API failure, UFC Stats timeout, parser failure, upsert failure, and publish failure, so that discovery edge cases are explicit.
31. As a developer, I want API tests for discovery and upsert auth/contracts, so that the worker/API boundary stays stable.
32. As a platform operator, I want the watcher packaged as Cloud Scheduler → Cloud Run Job → existing backend image → `watch_events` → exit, so that scheduling does not require a sleeping service.
33. As a platform operator, I want architecture docs updated for the watcher-only event ingress, so that `ARCHITECTURE.md` no longer describes a separate Event Scraper.
34. As a future maintainer, I want rename-repair and transactional outbox called out as follow-up, so that deferred reliability work is not mistaken for accidental omission.

## Implementation Decisions

### Verified current-state findings

These are repository facts, not recommendations:

- Production discovery/persistence is still partially combined in `events/event_page_sync/service.py` (`sync_event_page()`), while issue 025 has landed the watcher no-work path.
- Entry points: `python manage.py watch_events` (new) and legacy `enqueue_event_sync`.
- `EventSyncJob` exists; `EventScrapeJob` does not and must not be added.
- Shared listing parser/config live under `events/shared/`.
- Listing URL is `http://ufcstats.com/statistics/events/completed?page=all`.
- Listing rows already include name, URL, location, and date.
- Event uniqueness in DB is `(event, date)`; `url` is stored.
- `GET /api/events/DiscoverySource` exists (pipeline auth) from issue 025.
- No Event upsert API exists yet.
- Downstream fights-in-event payload is `{"url": ..., "event_id": ...}` on topic `fights-in-event`.
- Backend Docker image installs Chromium; Cloud Run must supply the command override.
- No Cloud Scheduler / Cloud Run Job IaC exists in-repo.

### Locked product/architecture decisions

- Single stage: Event Watcher owns discovery, Event upsert via API, and fights-in-event publish.
- No separate Event Scraper stage.
- No `EventScrapeJob`, no `event-scrape-jobs` / `event-scrape-jobs-sub`, no `event-scraper-worker`.
- No event-detail page scrape for Event persistence; listing fields are the persistence source.
- Retain `EventSyncJob` for each scheduled watcher execution.
- Discovery snapshot API remains the watcher read contract.
- Event upsert matches URL first, then `(event, date)`; returns `event_id` and `url`.
- Watcher discovery uses identity-set comparison against stored URLs and `(name, date)` pairs; date-only cutoff is not the sole gate.
- URL match means known; no rename-driven re-upsert/republish in this PRD.
- After each successful upsert, publish `{"url", "event_id"}` to `fights-in-event` via existing `PUBSUB_FIGHTS_IN_EVENT_TOPIC`.
- No outbox. Upsert then publish per unknown event; any persistence or publish failure fails the run and is recorded on `EventSyncJob` per the existing watcher retry/failure policy.
- Shared listing parser stays under `events/shared/`.
- One-rollout retirement of `sync_event_page()` / `enqueue_event_sync`.

### Final architecture

```text
Cloud Scheduler
  → Cloud Run Job (existing backend image)
    → python manage.py watch_events
      → EventSyncJob RUNNING
      → GET DiscoverySource (API)
      → Playwright listing scrape
      → identity compare (URL and name+date)
      → for each unknown event:
          → API event upsert (listing fields)
          → publish {"url","event_id"} to fights-in-event
      → EventSyncJob COMPLETED/FAILED
      → process exits

fights-in-event / fights-in-event-sub
  → existing fights-in-event worker (unchanged)
```

### Command execution flow

- Command: `watch_events` under `ufc_data_pipeline.management.commands`.
- One run per invocation; no internal sleep/timer loop.
- Create `EventSyncJob(status=RUNNING)`.
- Perform discovery; upsert and publish for each unknown event.
- On success, including zero unknown events: `COMPLETED` and exit 0.
- On failure: record error on `EventSyncJob`, apply existing retry/final failure semantics, non-zero exit for Cloud Run visibility.
- Replace `enqueue_event_sync` rather than keeping both commands.

### Event Watcher responsibilities

- Own scheduled discovery, Event persistence (via API), and fights-in-event handoff.
- Read stored identities through API discovery snapshot.
- Scrape and parse completed-events listing via `events/shared/`.
- Compare scraped rows to stored URL set and `(name, date)` set.
- Deduplicate duplicate listing rows before upsert/publish.
- Upsert each unknown event through the API using listing name, date, location, and normalized URL.
- Publish one `{"url", "event_id"}` message per successful upsert to `fights-in-event`.
- Update `EventSyncJob` status/logging for start, success, skip, and failure.
- Must not: write `fantasy.Events` via ORM; scrape event detail pages for Event persistence; publish to any `event-scrape-jobs` topic; create scrape job rows.

### Removed: Event Scraper stage

Do not implement:

- `events/event_scraper/` package
- `EventScrapeJob` model/migration
- `event-scrape-jobs` topic/subscription/env vars
- Compose `event-scraper-worker`
- Event-detail parser/selectors for Event ingress
- Consumer ack/nack lifecycle for event scrape messages

### API contracts

#### Discovery snapshot — exists (issue 025)

Route: `GET /api/events/DiscoverySource`

- Auth: `HasAPIKey` + `IsPipelineService`
- 200 body: `latest_event` plus full `events[]` identities (`event_id`, `event`, `date`, `url`)
- Empty DB: `latest_event: null`, `events: []`

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
- Response must include at least `event_id` and `url`.
- API owns uniqueness constraint handling; watcher treats successful upsert as idempotent.

### Repository / API client architecture

- No new repository abstraction layer.
- Watcher `api_client`: `get_discovery_source()` and `upsert_event(payload)`.
- Both use `PIPELINE_API_BASE_URL` and `PIPELINE_SERVICE_API_KEY`.
- Pipeline job models remain direct ORM (`EventSyncJob` only for this stage).

### Pub/Sub design

| Item | Value |
| --- | --- |
| Watcher outbound topic | existing `fights-in-event` |
| Topic env | `PUBSUB_FIGHTS_IN_EVENT_TOPIC` |
| Payload | `{"url": "<absolute event url>", "event_id": <int>}` |
| Publisher | Event Watcher (after each successful upsert) |
| Consumer | existing fights-in-event worker (unchanged) |
| New topics | none |
| Ordering | none |
| Dead letter | none in this PRD |

Do **not** add `event-scrape-jobs`, `PUBSUB_EVENT_SCRAPE_*`, or related emulator/Compose resources.

### Job ownership and status transitions

- `EventSyncJob`: one row per watcher command execution; not tied to a single event.
- No per-event scrape job.
- Watcher owns create → RUNNING → COMPLETED / FAILED (and any existing retry transitions used by the command/service).

### Idempotency and deduplication rules

- Known-event rule: scraped URL in stored URL set **or** `(name, date)` in stored pair set → skip.
- Duplicate listing rows collapse to one upsert/publish.
- Multiple events on one date: each unknown identity is upserted and published separately.
- UFC rename with same URL: known; no re-upsert/republish in this PRD.
- Same date / different name: unknown if URL also unknown → upsert + publish.
- Successful upsert then failed publish: fail the run on `EventSyncJob`; retries must remain safe because upsert is idempotent. Note: fights-in-event still lacks strong logical idempotency by `event_id` (follow-up).
- Do not treat `event_date > latest.date` as sufficient.

### Retry and failure behavior

- Watcher: durable `EventSyncJob` failure/retry visibility; command failure surfaces to Cloud Run Job.
- API/network/UFC Stats/parser/upsert/publish failures are retryable run failures unless clearly permanent configuration errors.
- No transactional outbox in this stage.
- Prefer failing the command if any unknown event’s upsert or publish fails after partial progress; document partial-success behavior in implementation notes/tests.

### Scheduling and Cloud Run deployment

```text
Cloud Scheduler → Cloud Run Job → existing backend image → python manage.py watch_events → exit
```

Required runtime concerns (IaC still absent from repo):

- Command override on the Cloud Run Job.
- Service account with Pub/Sub publish on `fights-in-event` and network access to UFC Stats + API.
- Env: `GOOGLE_CLOUD_PROJECT`, `PUBSUB_FIGHTS_IN_EVENT_TOPIC`, `PIPELINE_API_BASE_URL`, `PIPELINE_SERVICE_API_KEY`, DB settings.
- Playwright/Chromium already installed in `backend/Dockerfile`.
- Timeout must cover listing fetch + N upserts + N publishes.
- One-shot command; empty work exits successfully.

### Proposed module shape

```text
events/
  shared/                 # listing parser + listing URL/config
  event_watcher/
    service.py
    api_client.py
    scraper.py
    publisher.py          # optional thin wrapper around publish_json
    config.py
    tests/
    docs/
ufc_data_pipeline/management/commands/watch_events.py
```

Do not create `events/event_scraper/`. Retire `events/event_page_sync/` as the production path once watcher upsert/publish lands.

### Migration / model changes

- Keep `EventSyncJob`.
- Do **not** add `EventScrapeJob`.
- No required change to `fantasy.Events` uniqueness for this PRD; upsert must honor `(event, date)` and URL matching carefully when updating names.

### Issue breakdown change log

| Issue | Action |
| --- | --- |
| `025-run-event-watcher-with-no-work.md` | Keep (landed). Wording updated to remove Event Scraper references. |
| `026-publish-discovered-events.md` | **Rewrite** — was publish-to-`event-scrape-jobs`; now upsert API + upsert unknown events + publish to `fights-in-event`. |
| `027-scrape-and-persist-one-event.md` | **Rewrite** — delete Event Scraper happy path; become watcher upsert/publish failure and partial-run safety. |
| `028-event-scrape-idempotency-and-failures.md` | **Rewrite** — delete scraper consumer ack/nack work; become cut-over / retire old sync path. |
| `029-cut-over-local-event-pipeline.md` | **Rewrite** — become production scheduling readiness (former 030). |
| `030-validate-production-scheduling-readiness.md` | **Cancel** — content moved into 029; file marked superseded. |

### Rollout sequence

1. Keep issue 025 (discovery + no-work watcher) as foundation.
2. Add event upsert API and extend watcher to upsert unknowns then publish fights-in-event.
3. Harden failure/partial-run behavior on `EventSyncJob`.
4. Retire `sync_event_page()` / `enqueue_event_sync`; update docs and env examples.
5. Validate Cloud Scheduler / Cloud Run Job readiness and listing selectors manually.

## Testing Decisions

Good tests assert external behavior: HTTP contracts, publish payloads, job status transitions, and command exit behavior.

Modules under test:

- Shared listing parser under `events/shared/`
- Watcher service / command
- Discovery and upsert API endpoints
- Watcher API clients
- Fights-in-event publishing from the watcher

Do **not** add:

- Event-detail parser/selector tests for Event ingress
- Event scraper consumer/ack/nack tests
- `EventScrapeJob` model tests
- Compose worker tests for a non-existent scraper worker

Prior art:

- `events/shared/tests/`
- `events/event_watcher/tests/`
- `api/tests/test_discovery_source.py`
- Pipeline API tests under `api/tests/`
- `ufc_data_pipeline/tests/test_pubsub_publish.py`

Required scenarios:

| Scenario | Level |
| --- | --- |
| No stored events / empty listing | Watcher (025) |
| No newly discovered events | Watcher + command (025) |
| One new event → upsert + publish | Watcher |
| Multiple new events → upsert + publish each | Watcher |
| Multiple events on same date | Watcher |
| Duplicate listing rows | Watcher |
| Existing event matching name+date | Watcher |
| Existing event matching URL | Watcher |
| API discovery failure | Watcher |
| UFC Stats timeout / parser failure | Watcher |
| Upsert API failure | Watcher + API |
| Publish failure after successful upsert | Watcher |
| Command exits successfully with no work | Command |
| Discovery/upsert auth and body contracts | API tests |

## Out of Scope

- Separate Event Scraper stage / worker / topic / job model.
- Event-detail scrape solely to persist Events.
- Rename-driven metadata repair by the watcher.
- Transactional outbox / publish-marker table.
- Dead-letter topics and Pub/Sub retry-policy IaC.
- Redesigning fights-in-event ORM persistence into API-owned writes.
- DB Event Watcher, Fight Results Watcher, or later pipeline stages.
- Checking in Cloud Scheduler / Cloud Run Terraform unless a later issue expands scope.
- Legacy `refresh_ufc_data` / CSV bulk populate path changes beyond noting it remains legacy.

## Further Notes

### Open risks

- Relative vs absolute event hrefs must be normalized before identity comparison, upsert, and publish.
- Partial success (some events upserted/published before a later failure) can leave downstream work started; upsert idempotency helps, but fights-in-event may still duplicate on republish until that stage is hardened.
- Upsert name changes can interact with the `(event, date)` unique constraint if URL match updates a name onto another row’s pair; API must define deterministic conflict handling and tests.
- Full discovery identity payload may grow large over years of events; revisit windowing only if measured as a problem.

### Follow-up work

- Optional rename-repair job or watcher metadata refresh.
- Outbox if publish-after-upsert loss becomes operationally painful.
- Harden fights-in-event idempotency by `event_id`.
- Add deployment manifests for Scheduler + Cloud Run Job.
- Consider discovery snapshot pagination/windowing if payload size warrants it.
