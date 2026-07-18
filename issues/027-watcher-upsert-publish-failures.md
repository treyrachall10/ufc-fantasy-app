## Parent PRD

`issues/prd.md`

## What to build

Harden the Event Watcher upsert + fights-in-event publish path so persistence and publish failures are recorded on `EventSyncJob` and fail the command according to the existing watcher retry/failure policy.

No outbox and no per-event scrape job. After a successful upsert, publish immediately; if publish fails, fail the run so Cloud Run/Scheduler can retry. Retries must remain safe because upsert is idempotent. See PRD sections **Retry and failure behavior** and **Idempotency and deduplication rules**.

## Acceptance criteria

- [ ] Upsert API failure surfaces on `EventSyncJob` and fails `watch_events` (non-zero / `CommandError`)
- [ ] Successful upsert then failed fights-in-event publish surfaces on `EventSyncJob` and fails the command
- [ ] Listing/API/parser/network timeouts continue to mark the run failed as in issue 025
- [ ] Partial progress (some events upserted/published before a later failure) is documented and covered by tests; retries do not create conflicting Event rows
- [ ] No scraper consumer ack/nack, `EventScrapeJob`, or `event-scrape-jobs` behavior is introduced
- [ ] Tests cover: upsert failure mid-run, publish failure after upsert, and command failure messaging

## Blocked by

- Blocked by `issues/026-upsert-and-publish-discovered-events.md`

## User stories addressed

- User story 15
- User story 19
- User story 20
- User story 30
- User story 34

## Issue change note

**Rewritten and retitled.** Former content (`027-scrape-and-persist-one-event.md` Event Scraper happy path: `EventScrapeJob`, detail-page scrape, scraper worker) is deleted entirely.
