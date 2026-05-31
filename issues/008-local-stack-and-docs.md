## Parent PRD

`issues/prd.md`

## What to build

Make the fight-stats worker **runnable in local Docker** and **documented** for future contributors and upstream integrators.

Deliverables:

- Docker Compose: `fight-stats-worker` service (same backend image as fighter-profile-worker)
- `pubsub-init`: create `fight-stats-jobs` topic and `fight-stats-jobs-sub` subscription; create `career-stats-jobs` topic if not present
- Feature doc covering: purpose, Pub/Sub contract, env vars, how to run locally, idle shutdown, common errors, API endpoints used
- Update pipeline ARCHITECTURE sections 6–7: watcher publishes only; consumer creates job rows; two FightStats rows per fight; persistence via API

End-to-end local demo: `docker compose up fight-stats-worker`, manually publish a test message, confirm stats in DB and job row COMPLETED.

See parent PRD: **Infrastructure**, **Documentation updates**, **Local development before upstream exists**.

## Acceptance criteria

- [ ] `fight-stats-worker` service defined in docker-compose with correct env (`PUBSUB_EMULATOR_HOST`, API base URL)
- [ ] Pub/Sub emulator init creates fight-stats and career-stats topics/subscriptions
- [ ] Feature doc exists under the fight_stats feature folder
- [ ] ARCHITECTURE.md sections 6–7 updated to match implemented design
- [ ] README or feature doc includes manual publish command for local testing without Fight Results Watcher

## Blocked by

- `issues/007-career-stats-publish.md`

## User stories addressed

- User story 22
- User story 23
- User story 25
