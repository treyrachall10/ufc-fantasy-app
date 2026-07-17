## Parent PRD

`issues/prd-score-fight-worker.md`

## What to build

Add at least one verifiable end-to-end local integration path: publish/enqueue a `fight_id` → worker receives message → GET ScoringSource → pure score → PATCH SetFightScoring → FightScore and RoundScore stored → ScoreFightJob COMPLETED. Document the exact operator steps (or automate with an integration test if the repo pattern supports it). See PRD: Testing Decisions (integration); User story 36.

## Acceptance criteria

- [ ] Documented or automated flow covers publish → source → score → persist → job COMPLETED
- [ ] Asserts fight scores and round scores exist for both fighters after success
- [ ] Covers or documents that unscoreable fights fail the job without writing scores
- [ ] Instructions are runnable against local Compose + emulator

## Blocked by

- Blocked by `issues/023-score-fight-compose-enqueue-docs.md`

## User stories addressed

- User story 36
