## Parent PRD

`issues/prd.md`

## What to build

Harden the consumer and service for **production-grade job lifecycle** without adding new persistence scope. All scrape + API behavior from slices 003–005 must remain working.

Consumer dedup rules (fighter-profile pattern):

- Skip and ack if a `RUNNING` job exists for the same `fight_id`
- Reuse and promote `RETRYING` job to `RUNNING`, refresh URL, clear error
- Allow new job when prior job is `COMPLETED` or `FAILED` (re-scrape supported)

Retry rules:

- Transient failure → increment `retry_count`, set `RETRYING`, **nack**
- `retry_count >= 3` → `FAILED`, **ack**
- Invalid payload → **ack** (drop)

Operational behavior:

- Idle shutdown after 60s without messages
- SIGTERM/SIGINT cancels streaming pull gracefully
- All ack/nack only inside callback

Re-scrape idempotency: second successful run after `COMPLETED` updates data via API upserts without duplicate rows.

Full consumer test suite: skip-on-RUNNING, RETRYING reuse, nack vs ack on failure, max-retry FAILED, re-scrape after COMPLETED.

See parent PRD: **Job model and dedup**, **Retry and messaging lifecycle**, **Testing Decisions → Consumer**.

## Acceptance criteria

- [ ] Duplicate message while RUNNING is acked without double-scrape
- [ ] RETRYING job reused on redelivery, not duplicated
- [ ] New job created after COMPLETED; API upsert refreshes stats idempotently
- [ ] Failure under max retries nacks; failure at max retries marks FAILED and acks
- [ ] Idle shutdown exits after configured timeout with no messages
- [ ] Consumer test suite covers all dedup and retry scenarios above

## Blocked by

- `issues/005-roundstats-via-api.md`

## User stories addressed

- User story 4
- User story 5
- User story 6
- User story 7
- User story 8
- User story 9
- User story 10
- User story 20
