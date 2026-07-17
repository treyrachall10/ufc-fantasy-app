## Parent PRD

`issues/prd-score-fight-worker.md`

## What to build

Wire local ops for the Score Fight Worker: Docker Compose `score-fight-worker` service (topic/sub already exist), management command `enqueue_score_fight --fight-id`, feature doc, and architecture doc update so ScoreFight is described as this implemented design (no longer stub / out of scope). Confirm env vars match career-stats-style workers. See PRD: Wiring / ops.

## Acceptance criteria

- [ ] Compose service runs `python -m ufc_data_pipeline.fantasy.score_fight.score_fight_worker` with correct emulator host and API base URL
- [ ] `enqueue_score_fight` publishes `{"fight_id"}` to `score-fight-jobs`
- [ ] Feature doc covers payload, env, local run, ack/nack, and API contracts
- [ ] `ARCHITECTURE.md` ScoreFight section updated to match this stage
- [ ] No new Pub/Sub topic/sub required beyond existing emulator init (verify present)

## Blocked by

- Blocked by `issues/022-score-fight-consumer-and-worker.md`

## User stories addressed

- User story 30
- User story 31
- User story 32
- User story 33
- User story 36
