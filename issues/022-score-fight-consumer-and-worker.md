## Parent PRD

`issues/prd-score-fight-worker.md`

## What to build

Add Pub/Sub consumer, worker entrypoint, and config for score-fight, mirroring career-stats: parse `{"fight_id"}`, claim/create `ScoreFightJob`, call service, update job status, ack/nack per conventions. Skip RUNNING; reuse RETRYING; new row after COMPLETED/FAILED. Invalid payload → ack. Retryable failures → RETRYING + nack until max, then FAILED + ack. Permanent unscoreable → FAILED + ack immediately with no score writes. COMPLETED only after successful persist. No downstream publish (terminal stage). Short comments on every retry vs permanent branch. See PRD: Consumer / Pub/Sub; Job model.

## Acceptance criteria

- [ ] `config.py`, `consumer.py`, and `score_fight_worker.py` exist and follow standalone-service / pubsub-processing conventions
- [ ] Job lifecycle matches career-stats (RUNNING skip, RETRYING reuse, post-COMPLETED/FAILED new row)
- [ ] Ack/nack rules match PRD (invalid, skip, success, retry, exhaustion, permanent unscoreable)
- [ ] Job marked COMPLETED only after successful SetFightScoring
- [ ] Idle shutdown and max_messages wired via existing worker settings / env
- [ ] Consumer tests cover valid/invalid payload, RUNNING duplicate, retryable failure, exhaustion, success, permanent unscoreable, and status transitions
- [ ] Retry vs permanent branches have short clarifying comments

## Blocked by

- Blocked by `issues/018-score-fight-job-model.md`
- Blocked by `issues/021-score-fight-api-client-and-service.md`

## User stories addressed

- User story 1
- User story 2
- User story 3
- User story 4
- User story 5
- User story 6
- User story 7
- User story 8
- User story 9
- User story 13
- User story 34
- User story 37
