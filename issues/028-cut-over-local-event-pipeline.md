## Parent PRD

`issues/prd.md`

## What to build

Cut local operators over to the watcher-only event ingress: verify the full local path, retire `sync_event_page()` / `enqueue_event_sync`, and update architecture/feature docs so the combined ORM sync path and any Event Scraper references are no longer the documented production design.

Confirm env/Compose stay free of `event-scrape-jobs` / `event-scraper-worker`. See PRD sections **Rollout sequence**, **Out of Scope**, and **Issue breakdown change log**.

## Acceptance criteria

- [ ] Local path works: `watch_events` → discovery API → listing scrape → event upsert API → `fights-in-event` message
- [ ] `sync_event_page()` / `enqueue_event_sync` are deleted or hard-disabled so operators cannot run the old combined path
- [ ] Shared listing parser remains under `events/shared/`; `event_page_sync` production path is retired
- [ ] No `event-scrape-jobs` topic/subscription, no `PUBSUB_EVENT_SCRAPE_*`, and no `event-scraper-worker` in Compose/emulator/env examples
- [ ] `ARCHITECTURE.md` and watcher docs describe watcher-only Event ingress (upsert via API, publish fights-in-event)
- [ ] Follow-ups remain out of implementation scope here (rename-repair, outbox, fights-in-event idempotency hardening, deployment IaC)

## Blocked by

- Blocked by `issues/027-watcher-upsert-publish-failures.md`

## User stories addressed

- User story 26
- User story 27
- User story 28
- User story 33
- User story 34

## Issue change note

**Rewritten.** Former content (`028-event-scrape-idempotency-and-failures.md` scraper consumer claim/ack/nack) is deleted. Absorbs the cut-over goals previously in `029-cut-over-local-event-pipeline.md`.
