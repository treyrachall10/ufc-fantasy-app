## Parent PRD

`issues/prd-score-fight-worker.md`

## What to build

Relocate fantasy scoring out of `scripts/` into `ufc_data_pipeline/fantasy/score_fight/scoring.py` as a pure module (no Pub/Sub, HTTP, ORM, or env). Preserve existing formulas and batch edge cases exactly (round multipliers, winner bonuses, no-winner method allowlist). Update `scripts/db_population.py` to import from the new module and delete `scripts/scoring.py`. Add focused regression tests for known examples, both fighters, draws, finishes, totals, and invalid/unscoreable inputs. See PRD: Pure scoring; Testing Decisions (pure scoring).

## Acceptance criteria

- [ ] Pure scoring module lives under `ufc_data_pipeline/fantasy/score_fight/` and has no I/O side effects
- [ ] Behavior matches previous `scripts/scoring.py` + `populate_round_score` / `populate_fight_score` rules (no silent formula changes)
- [ ] `db_population` imports the relocated module; `scripts/scoring.py` is removed
- [ ] Unit tests cover wins, losses, draws, finish bonuses, round totals, fight totals, and invalid/unscoreable inputs
- [ ] Short comments document preserved allowlist / bonus edge cases where non-obvious

## Blocked by

None - can start immediately

## User stories addressed

- User story 16
- User story 17
- User story 18
- User story 19
- User story 20
- User story 21
