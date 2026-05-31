## Parent PRD

`issues/prd.md`

## What to build

Stand up the fight-stats worker as a **thin vertical messaging path**: Pub/Sub message in → job row created → job marked complete. No scraping or fantasy data writes yet.

Deliverables:

- Feature folder scaffold with `config.py` (timeouts, retry limits, topic/subscription IDs, page-ready selector placeholders)
- `fight_stats_worker.py` — Django bootstrap, SIGTERM/SIGINT, delegates to subscriber
- `consumer.py` — parse payload `{"fight_id": int, "fight_url": str}`, create `FightStatsScrapeJob` row (`RUNNING`), call stub service, mark `COMPLETED`, ack
- Stub `service.py` — `process_fight_stats(fight_id, fight_url)` no-op (returns immediately)
- Invalid payload → log + ack (drop)
- Basic consumer tests: valid payload creates job + acks; invalid payload acks without job row

This slice proves the Pub/Sub → consumer → pipeline job table path works before Playwright or API integration.

See parent PRD: **Architectural pattern**, **Modules**, **Retry and messaging lifecycle** (happy path only; full retry rules come in slice 006).

## Acceptance criteria

- [ ] Worker starts via `python -m ufc_data_pipeline.fights.fight_stats.fight_stats_worker`
- [ ] Valid Pub/Sub message creates a `FightStatsScrapeJob` row and marks it `COMPLETED`
- [ ] Invalid JSON or missing fields are acked and dropped
- [ ] Config centralizes subscription ID, retry limit, idle shutdown constants
- [ ] Consumer tests pass for payload validation and happy-path job creation

## Blocked by

- `issues/001-fight-stats-job-model.md`

## User stories addressed

- User story 1
- User story 3
- User story 17
- User story 18
- User story 21
