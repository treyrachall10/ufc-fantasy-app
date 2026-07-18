## Parent PRD

`issues/prd.md`

## What to build

Make Event Scraper processing duplicate-safe and failure-safe across consumer claim rules, ack/nack behavior, retries, API upsert idempotency, and downstream fights-in-event publish recovery.

No outbox in this slice: after successful upsert, mark `EventScrapeJob` `COMPLETED`, then publish; publish failure moves the job to `RETRYING` and nacks so reprocessing remains safe. See PRD sections **Retry and failure behavior**, **Idempotency and deduplication rules**, and **Testing Decisions** consumer scenarios.

## Acceptance criteria

- [ ] Claim rules keyed by event URL: skip + ack if `RUNNING`; reuse latest `RETRYING`; create a new job after `COMPLETED`/`FAILED`
- [ ] Invalid Pub/Sub payloads are logged, acknowledged, and dropped
- [ ] Retryable scrape/API/network/parser failures increment `retry_count`, set `RETRYING`, and nack
- [ ] After max retries (3), job is `FAILED` and the message is acked
- [ ] Successful upsert then failed fights-in-event publish sets `RETRYING` and nacks; reprocessing does not create conflicting event rows
- [ ] Duplicate deliveries for an in-flight URL do not double-scrape
- [ ] Consumer tests cover: valid payload success, invalid payload, RUNNING skip, RETRYING reuse, retryable failure, exhaustion, and persistence-then-publish failure

## Blocked by

- Blocked by `issues/027-scrape-and-persist-one-event.md`

## User stories addressed

- User story 19
- User story 20
- User story 25
- User story 26
- User story 27
- User story 28
- User story 32
- User story 33
- User story 44
- User story 50
