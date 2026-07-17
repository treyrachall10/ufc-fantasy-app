## Parent PRD

`issues/prd-score-fight-worker.md`

## What to build

Add a `ScoreFightJob` pipeline job model extending `BaseJobModel`, keyed by `fight_id` (one job per fight scoring run, never per fighter or round). Include migration and `(fight_id, status)` index following `CareerStatsJob`. See PRD: Job model.

## Acceptance criteria

- [ ] `ScoreFightJob` exists with `fight_id`, status lifecycle fields from `BaseJobModel`, and index on `(fight_id, status)`
- [ ] Migration applies cleanly
- [ ] Model tests cover creation and basic field defaults (same depth as career-stats job model tests)
- [ ] No fantasy-table foreign keys on the job row

## Blocked by

None - can start immediately

## User stories addressed

- User story 2
- User story 3
- User story 4
- User story 5
- User story 9
