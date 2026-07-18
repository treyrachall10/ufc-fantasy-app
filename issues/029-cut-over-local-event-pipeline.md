## Parent PRD

`issues/prd.md`

## What to build

Cut local operators over to the watcher → scraper pipeline: verify the full local path, retire `sync_event_page()` / `enqueue_event_sync`, and update architecture/feature docs so the combined event sync path is no longer the documented or runnable production entry point.

Confirm Compose/emulator/env wiring from prior slices works together for a demoable local flow. See PRD sections **Rollout sequence**, **Out of Scope**, and **Further Notes → Follow-up work**.

## Acceptance criteria

- [ ] Local path works: `watch_events` → `event-scrape-jobs` → event-scraper-worker → event upsert → `fights-in-event` message
- [ ] `sync_event_page()` / `enqueue_event_sync` are deleted or hard-disabled so operators cannot run the old combined path
- [ ] Shared listing parser remains only under `events/shared/`; `event_page_sync` production path is retired
- [ ] `.env.example`, Compose, and emulator resources remain consistent for the new topic/subscription/worker
- [ ] `ARCHITECTURE.md` describes watcher publishing scrape work (not creating scrape jobs) and scraper owning `EventScrapeJob`
- [ ] Component docs for watcher/scraper exist or replace stale `event_page_sync` docs
- [ ] Follow-ups called out in docs/PRD notes remain out of implementation scope here (rename-repair, outbox, fights-in-event idempotency hardening, deployment IaC)

## Blocked by

- Blocked by `issues/028-event-scrape-idempotency-and-failures.md`

## User stories addressed

- User story 39
- User story 40
- User story 41
- User story 42
- User story 49
- User story 50
