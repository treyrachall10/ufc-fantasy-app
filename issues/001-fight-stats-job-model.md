## Parent PRD

`issues/prd.md`

## What to build

Add the pipeline job tracking model for fight-stats scraping so downstream slices can record audit state per scrape attempt.

This slice establishes only the **pipeline-owned** job table (`FightStatsScrapeJob` extending the shared base job model). It does not touch fantasy application tables or API endpoints.

Fields: `fight_id`, `fight_url`, plus standard job fields (`ran_at`, `completed_at`, `status`, `retry_count`, `error_msg`). Index on `(fight_id, status)`.

Create and apply the Django migration. Verify a row can be created and queried from the Django shell.

See parent PRD: **Implementation Decisions → Job model and dedup**.

## Acceptance criteria

- [ ] `FightStatsScrapeJob` model exists extending `BaseJobModel` with `fight_id` and `fight_url`
- [ ] Migration created and applies cleanly
- [ ] Index on `(fight_id, status)` exists
- [ ] A test or shell verification confirms a job row can be created with status `RUNNING`

## Blocked by

None — can start immediately.

## User stories addressed

- User story 2
- User story 24
