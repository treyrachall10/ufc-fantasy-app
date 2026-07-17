## Parent PRD

`issues/prd-score-fight-worker.md`

## What to build

Add pipeline-only `GET /api/fights/{fight_id}/ScoringSource` that returns one complete scoreable snapshot (fight metadata, both fighters, fight-level stats, per-round stats). Return 200 only when fully scoreable. Return 404 for missing fight; 409 with `error_code=SCORING_SOURCE_INCOMPLETE` + `detail` when not ready; 422 with `error_code=SCORING_SOURCE_UNSCOREABLE` + `detail` for NC and other unscoreable outcomes (preserve existing no-winner allowlist). Require pipeline auth. Short comments on every scoreable vs incomplete vs unscoreable branch. See PRD: Read API; Agreed product decisions.

## Acceptance criteria

- [ ] Endpoint registered and gated with `HasAPIKey` + `IsPipelineService`
- [ ] 200 response includes all fields needed to score without further reads
- [ ] 404 / 409 / 422 responses include human-readable `detail`; 409/422 include `error_code`
- [ ] Incomplete stats / not completed → 409; NC/unscoreable → 422; no score writes from this endpoint
- [ ] API tests cover auth, happy path, incomplete, unscoreable, and missing fight
- [ ] Classification branches have short clarifying comments

## Blocked by

None - can start immediately

## User stories addressed

- User story 10
- User story 11
- User story 12
- User story 13
- User story 14
- User story 17
- User story 18
- User story 37
