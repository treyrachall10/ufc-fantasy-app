## Parent PRD

`issues/prd-score-fight-worker.md`

## What to build

Add pipeline-only `PATCH /api/fights/{fight_id}/SetFightScoring` that atomically persists `FightScore` and `RoundScore` for one fight. Round rows are identified by `fighter_id` + `round_number` and resolved via `RoundStats → FightStats → Fighter` for the path `fight_id`. In one transaction, use at most three bounded DB operations: resolve RoundStats once, bulk upsert all submitted scores, delete stale `RoundScore` rows not in the payload. No ORM-in-loops; no per-fighter/per-round endpoints. Validate fighters belong to the fight; upsert on existing uniqueness constraints. See PRD: Write API; Performance budget.

## Acceptance criteria

- [ ] Endpoint registered and gated with `HasAPIKey` + `IsPipelineService`
- [ ] Request uses real model field names (`points_win`, `points_round`, `points_time`, `fight_total_points`, round category fields, `round_total_points`)
- [ ] Round scores resolve via fight_id + fighter_id + round_number (FightStats traversal)
- [ ] All writes + stale RoundScore deletes commit in one transaction; invalid input rolls back
- [ ] ≤3 bounded DB query patterns; no ORM queries inside Python loops
- [ ] Retry/idempotent upsert updates existing rows; stale round scores removed
- [ ] API tests cover auth, valid upsert, rollback, idempotent retry, stale cleanup, invalid fighter/round, missing fight

## Blocked by

None - can start immediately

## User stories addressed

- User story 22
- User story 23
- User story 24
- User story 25
- User story 26
- User story 27
- User story 28
- User story 29
- User story 35
