## Problem Statement

After fight stats and career stats are finalized, the pipeline publishes a `score-fight-jobs` message, but nothing consumes it. Fantasy `FightScore` and `RoundScore` rows are still produced only by batch ORM scripts under `scripts/`, which cannot run as a scale-to-zero Pub/Sub worker and must not be how the live pipeline writes fantasy tables.

Operators need a Score Fight Worker that loads one fight’s scoring inputs through the API, applies the existing fantasy scoring rules without changing formulas, persists fight and round scores atomically through the API, and records job completion only after those writes succeed—without ever connecting the worker directly to fantasy tables.

## Solution

Add a terminal pipeline stage under `ufc_data_pipeline/fantasy/score_fight/` that:

1. Consumes `{"fight_id": <int>}` from `score-fight-jobs` / `score-fight-jobs-sub` (already published by career-stats after success; topic/sub already exist locally).
2. Tracks each run in a `ScoreFightJob` row keyed by `fight_id` (same RUNNING / RETRYING / COMPLETED / FAILED lifecycle as career-stats).
3. Loads a complete scoring snapshot via one pipeline-only `GET .../ScoringSource` call.
4. Scores the fight with a relocated pure scoring module (moved out of `scripts/`, shared with batch population).
5. Persists the full result via one pipeline-only `PATCH .../SetFightScoring` call that upserts fight and round scores and deletes stale round scores in one transaction (at most three bounded DB operations; no ORM-in-loops).
6. Marks the job `COMPLETED` only after the write succeeds.

The worker never writes fantasy tables via ORM. Incomplete source data is retryable; no-contest and other unscoreable outcomes permanently fail with no score writes. Every classification branch in this stage carries a short comment explaining why.

## User Stories

1. As a pipeline operator, I want a Score Fight Worker that consumes `score-fight-jobs`, so that career-stats handoff actually produces fantasy scores.
2. As a pipeline operator, I want one job row per fight scoring run, so that I can see status, retries, and errors for the fight as a whole.
3. As a pipeline operator, I want concurrent deliveries for the same `fight_id` to skip when a job is already `RUNNING`, so that two workers cannot double-score the same fight.
4. As a pipeline operator, I want `RETRYING` jobs to be reused, so that retries do not create confusing duplicate job histories for the same in-flight attempt.
5. As a pipeline operator, I want a new job allowed after `COMPLETED` or `FAILED`, so that re-scoring after corrected stats is possible.
6. As a pipeline operator, I want invalid Pub/Sub payloads acknowledged and dropped, so that bad messages do not block the subscription.
7. As a pipeline operator, I want retryable failures to nack with incremented retry_count, so that transient API/network issues recover automatically.
8. As a pipeline operator, I want exhausted retries to mark the job `FAILED` and ack, so that poison messages stop looping forever.
9. As a pipeline operator, I want the job marked `COMPLETED` only after score persistence succeeds, so that “completed” always means scores exist.
10. As a scoring service, I want a single `ScoringSource` GET that returns all fight metadata, both fighters’ fight stats, and both fighters’ round stats needed to score, so that I make one read per fight.
11. As a scoring service, I want `ScoringSource` to return 200 only when the fight is fully scoreable, so that I never invent partial scores.
12. As a scoring service, I want incomplete source data to return HTTP 409 with `error_code=SCORING_SOURCE_INCOMPLETE` and a human-readable `detail`, so that the worker can retry.
13. As a scoring service, I want unscoreable outcomes (including NC / Could Not Continue and other no-winner cases outside the existing draw allowlist) to return HTTP 422 with `error_code=SCORING_SOURCE_UNSCOREABLE` and `detail`, so that the worker fails permanently without writing scores.
14. As a scoring service, I want a missing fight to return HTTP 404 with `detail`, so that unknown ids are distinguishable.
15. As an API client, I want typed errors mapped from `error_code`, so that the consumer can choose retry vs permanent fail without parsing prose.
16. As a fantasy product owner, I want existing scoring formulas preserved exactly (including winner round/time bonuses and the no-winner method allowlist), so that live pipeline scores match historical batch behavior.
17. As a fantasy product owner, I want draws (and the existing no-winner allowlist methods) scored with round points only and zero win/round/time bonuses, so that draw behavior stays consistent.
18. As a fantasy product owner, I want NC and other unscoreable fights to produce no `FightScore` / `RoundScore` rows, so that fantasy totals are not polluted with zeros.
19. As a developer, I want pure scoring relocated beside the worker and `scripts/scoring.py` removed, so that there is one implementation.
20. As a developer, I want `db_population` updated to import the relocated module, so that batch backfills use the same formulas.
21. As a developer, I want focused unit tests on pure scoring (wins, losses, draws, finishes, totals, invalid inputs), so that formula regressions are caught.
22. As a pipeline service, I want one `SetFightScoring` PATCH per fight that accepts both fight scores and round scores, so that persistence is a single network call.
23. As a pipeline service, I want `SetFightScoring` to require pipeline API auth, so that only the pipeline can write scores.
24. As a pipeline service, I want the write endpoint to validate that supplied fighters belong to the fight, so that cross-fight contamination is rejected.
25. As a pipeline service, I want round scores keyed by `fighter_id` + `round_number`, resolved via `RoundStats → FightStats → Fighter` for the endpoint `fight_id`, so that the worker does not depend on unstable `round_stats_id` write keys.
26. As a pipeline service, I want fight and round score upserts plus stale round-score deletion in one DB transaction, so that partial score states cannot commit.
27. As a pipeline service, I want the write endpoint limited to three bounded DB operations (resolve RoundStats once, bulk upsert scores, delete stale RoundScores), with no ORM queries inside loops, so that a 12-fight event stays at 24 API calls and predictable DB cost.
28. As a pipeline service, I want retries of `SetFightScoring` to upsert deterministically, so that redelivery after a successful write but before ack is safe.
29. As a pipeline service, I want stale `RoundScore` rows for the fight that are not in the new payload deleted in the same transaction, so that re-scores cannot leave orphan round points.
30. As a pipeline operator, I want Docker Compose to run `score-fight-worker` like other workers, so that local end-to-end scoring works.
31. As a pipeline operator, I want idle shutdown and `WORKER_MAX_MESSAGES` to follow existing worker settings, so that ops behavior matches career-stats / fight-stats.
32. As a pipeline operator, I want an `enqueue_score_fight` management command, so that I can test scoring without re-running career-stats.
33. As a pipeline operator, I want architecture and feature docs updated for Score Fight, so that the terminal stage is no longer “out of scope / unimplemented.”
34. As a developer, I want consumer tests covering valid/invalid payload, RUNNING skip, retry, exhaustion, completion, and ack/nack, so that lifecycle regressions are caught.
35. As a developer, I want API tests for auth, upsert, rollback, stale cleanup, invalid fighter/round, and missing fight, so that the write contract stays solid.
36. As a developer, I want at least one documented local e2e path (publish → source → score → persist → job COMPLETED), so that the stage can be verified manually.
37. As a scoring service, I want short comments above every permanent-vs-retryable and scoreable-vs-unscoreable decision in this stage, so that future readers know why each branch exists.
38. As a league scoring system, I want existing `FightScore.fight_total_points` semantics preserved (round totals + fight bonuses), so that team applied scoring continues to read the same field.

## Implementation Decisions

### Package and layers

- New feature package: `ufc_data_pipeline/fantasy/score_fight/` with `score_fight_worker.py`, `consumer.py`, `service.py`, `api_client.py`, `scoring.py` (pure), `config.py`, `tests/`, and optional `docs/score-fight.md`.
- Mirror career-stats layering: worker = process lifecycle only; consumer = Pub/Sub + job table + ack/nack; service = orchestration; api_client = HTTP; scoring = pure transforms.
- No direct ORM access to fantasy `FightScore` / `RoundScore` / stats tables from the worker process (job model ORM only).

### Pure scoring

- Move helpers and fight/round orchestration out of `scripts/scoring.py` into the feature package.
- Update `scripts/db_population.py` imports; delete `scripts/scoring.py`.
- Preserve behavior exactly:
  - Round: KD×10, sig strikes 1:1, TD×3, sub×2, ctrl×0.05, reversals 1:1.
  - Fight: sum of round totals; winner gets +20, `score_round_finish`, `score_time`; non-winners get 0 fight bonuses.
  - No-winner scoreable only when method ∈ {`Decision - Split`, `Decision - Majority`, `Draw`} (existing batch allowlist).
  - Winner identity via fighter id (preferred) / stable fighter identity from source—not fragile string compare when ids are available.
- Do not “fix” decision full-distance bonuses or the allowlist in this PRD.

### Read API — Option A (selected)

- `GET /api/fights/{fight_id}/ScoringSource`
- Auth: `HasAPIKey` + `IsPipelineService`
- 200 body: one snapshot with fight metadata (method, round, time, winner_id, fight_status), both fighters, fight-level stats fields needed for scoring context, and per-round stats for both fighters (including fields the round scorer needs).
- Errors:
  - 404 missing fight (`detail`)
  - 409 `error_code=SCORING_SOURCE_INCOMPLETE` + `detail` (missing/partial stats, not completed, missing required finish fields for a decisive winner path, etc.) → worker retryable
  - 422 `error_code=SCORING_SOURCE_UNSCOREABLE` + `detail` (NC / Could Not Continue / no-winner outside allowlist / unsupported outcome) → worker permanent fail, no writes
- API owns readiness and scoreability gates; worker maps `error_code` first.

### Write API — atomic SetFightScoring (selected)

- `PATCH /api/fights/{fight_id}/SetFightScoring`
- Auth: `HasAPIKey` + `IsPipelineService`
- Request shape uses real model field names, e.g.:
  - `fight_scores[]`: `fighter_id`, `points_win`, `points_round`, `points_time`, `fight_total_points`
  - `round_scores[]`: `fighter_id`, `round_number`, category point fields, `round_total_points`
- Round identity for writes: `fighter_id` + `round_number` resolved for the path `fight_id` through `RoundStats → FightStats → Fighter`.
- Single transaction:
  1. Resolve all needed `RoundStats` in one query.
  2. Bulk upsert all submitted `FightScore` and `RoundScore` rows.
  3. Delete stale `RoundScore` rows for this fight’s round-stats set that were not in the request.
- No per-fighter or per-round HTTP endpoints; no ORM queries inside Python loops.
- Validate fighters belong to the fight; reject invalid rounds; upsert on `(fight, fighter)` and `(round_stats)`.

### Job model

- `ScoreFightJob(BaseJobModel)` with `fight_id`, index on `(fight_id, status)`.
- One row per scoring execution target (fight), never per fighter or per round.
- Lifecycle identical to `CareerStatsJob`: skip if RUNNING; reuse RETRYING; new row after COMPLETED/FAILED.
- COMPLETED only after successful `SetFightScoring`.

### Consumer / Pub/Sub

- Payload: `{"fight_id": <int>}` only (already published by career-stats).
- Topic `score-fight-jobs`, subscription `score-fight-jobs-sub` (already initialized).
- Invalid payload → log + ack.
- RUNNING skip → ack.
- Success → COMPLETED + ack (no downstream publish; terminal stage).
- Retryable exception → RETRYING + nack until max retries, then FAILED + ack.
- Permanent unscoreable (`SCORING_SOURCE_UNSCOREABLE`) → FAILED + ack without writing scores (does not burn useless retries, or burns retries only if implemented as non-retryable exception that fails immediately—prefer immediate FAILED + ack).
- Idle shutdown and `MAX_MESSAGES` via existing worker settings / config env vars.
- Short comments on every retry vs permanent branch.

### Wiring / ops

- Compose service `score-fight-worker` analogous to `career-stats-worker`.
- Env: project, subscription, `PIPELINE_API_BASE_URL`, API key, idle shutdown, max messages, `PUBSUB_SCORE_FIGHT_*` as needed.
- Management command `enqueue_score_fight --fight-id`.
- Update architecture doc ScoreFight section from stub to this design; add feature doc.

### Performance budget

- Per fight: 1 GET + 1 PATCH (24 API calls for a 12-fight event).
- Per PATCH: ≤3 bounded DB operations as above.

## Testing Decisions

- Prefer testing external behavior (HTTP contracts, job status transitions, ack/nack, persisted score fields), not private helpers.
- Prior art: `fighters/career_stats/tests/` (consumer, service, counters, publish) and `api/tests/test_career_stats_source.py` / `test_set_fighter_career_stats.py`.
- Required coverage:
  - Pure scoring: known examples, both fighters, round totals, fight totals, draws, NC/unscoreable inputs, finish rounds/times, invalid inputs.
  - Service: load source, call scoring, build write payload, persist once, no persist on scoring/source failure, API failures.
  - Consumer: valid/invalid payload, RUNNING duplicate, retryable failure, exhaustion, success, permanent unscoreable, ack/nack and status transitions.
  - API: authz, ScoringSource 200/409/422/404, SetFightScoring upsert, transaction rollback, idempotent retry, stale round cleanup, invalid fighter/round, missing fight.
  - Integration: documented local flow with enqueue → worker → scores → COMPLETED.
- Worker `main()` smoke optional if career-stats pattern is followed.

## Out of Scope

- Changing fantasy scoring formulas or point weights.
- Team / league applied scoring (`TeamAppliedFightScore`, `ScoringRun`, `populate_team_scores`).
- Downstream Pub/Sub after score-fight (terminal stage).
- Go rewrite of scoring.
- Direct worker ORM writes to fantasy tables.
- Separate read endpoints for fight stats vs round stats for this worker.
- Separate write endpoints for fight scores vs round scores.
- Per-fighter or per-round job rows.
- Fight Results Watcher or re-scraping stats.
- Frontend UI changes.
- Backfilling historical scores in bulk beyond reusing `db_population` against the shared module.

## Further Notes

### Agreed product decisions (grill-me)

1. NC / unscoreable → permanent fail, no score writes.
2. Incomplete/not-ready → retryable; unscoreable → permanent; every branch commented.
3. Round write keys: `fighter_id` + `round_number` with FightStats traversal.
4. One GET + one PATCH per fight; write endpoint ≤3 bounded DB ops; replace-set stale round scores; no ORM-in-loops.
5. ScoringSource gatekeeper with `error_code` + `detail`; 409 incomplete, 422 unscoreable, 404 missing.
6. Preserve existing batch scoring edge cases exactly.
7. Single scoring module; update `db_population`; delete `scripts/scoring.py`.
8. Module layout and test set approved as proposed.

### Recommended API contracts (summary)

**GET** `/api/fights/{fight_id}/ScoringSource` → scoreable snapshot or 409/422/404 with `error_code` + `detail`.

**PATCH** `/api/fights/{fight_id}/SetFightScoring` → body with `fight_scores` and `round_scores`; transactional upsert + stale round-score delete; pipeline auth.
