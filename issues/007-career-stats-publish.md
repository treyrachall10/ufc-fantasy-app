## Parent PRD

`issues/prd.md`

## What to build

Add **downstream handoff** after a successful scrape: publish a message to `career-stats-jobs` so the future Career Stats Worker can react without polling.

End-to-end behavior:

1. After all API writes succeed and the job is marked `COMPLETED`, publish `{"fight_id": <int>}` to the `career-stats-jobs` topic
2. Publish **after** the database/API transaction commits — not inside it — so rolled-back failures do not trigger downstream work
3. Add career-stats topic ID to config; publisher helper in service layer

Verify locally by subscribing to the topic (or inspecting emulator) after processing a test message.

See parent PRD: **Downstream handoff**.

## Acceptance criteria

- [ ] Successful scrape publishes `{"fight_id": <int>}` to `career-stats-jobs`
- [ ] Failed scrape (job not COMPLETED) does not publish
- [ ] Publish occurs after commit, not inside the same atomic block as job completion
- [ ] Config includes `CAREER_STATS_TOPIC_ID` (or env equivalent)
- [ ] Manual test documents how to verify the published message locally

## Blocked by

- `issues/006-consumer-reliability.md`

## User stories addressed

- User story 15
