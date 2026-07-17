## Parent PRD

`issues/prd-score-fight-worker.md`

## What to build

Add `api_client.py` and `service.py` under `ufc_data_pipeline/fantasy/score_fight/`. Client performs one GET ScoringSource and one PATCH SetFightScoring per fight, mapping `error_code` to typed errors (incomplete → retryable; unscoreable → permanent). Service loads source, calls pure scoring, builds the write payload, and persists once; does not persist when scoring or source fails. See PRD: Package and layers; Read/Write API; Testing Decisions (service).

## Acceptance criteria

- [ ] `api_client` uses pipeline base URL + API key headers like career-stats
- [ ] Incomplete (`SCORING_SOURCE_INCOMPLETE`) and unscoreable (`SCORING_SOURCE_UNSCOREABLE`) map to distinct exception types
- [ ] Service orchestration: fetch → score → single persist; no persist on failure
- [ ] Exactly one read and one write HTTP call on the success path
- [ ] Unit tests cover happy path, source failures, scoring failure, and write failure

## Blocked by

- Blocked by `issues/017-relocate-pure-scoring-module.md`
- Blocked by `issues/019-scoring-source-api.md`
- Blocked by `issues/020-set-fight-scoring-api.md`

## User stories addressed

- User story 10
- User story 15
- User story 22
