## Parent PRD

`issues/prd.md`

## What to build

Validate production-oriented readiness for the scheduled watcher without checking in Cloud Scheduler/Cloud Run Terraform unless explicitly expanded later.

Manually verify live UFC Stats listing and event-detail selectors against fixture contracts, and document/verify the Cloud Scheduler → Cloud Run Job → existing backend image → `watch_events` → exit model, including command override, service account permissions, API auth env vars, Playwright/Chromium, timeouts, and job retry/exit expectations. See PRD sections **Scheduling and Cloud Run deployment**, **Testing Decisions** (no live UFC Stats in CI), and **Further Notes → Open risks**.

## Acceptance criteria

- [ ] Manual live check confirms listing-page selectors used by `events/shared/` still match UFC Stats
- [ ] Manual live check confirms event-detail selectors used by the Event Scraper still match one real event page
- [ ] Relative vs absolute event URLs are normalized as required before identity comparison and persistence
- [ ] Operator-facing notes document Cloud Run Job command override, required env vars, Pub/Sub publish permission, API key auth, Chromium dependency, and timeout expectations
- [ ] Notes state the command is one-shot (no internal sleep loop) and empty work exits successfully
- [ ] No deployment IaC is required for this slice unless product explicitly expands scope
- [ ] Findings from selector drift or URL normalization gaps are recorded as follow-up if they block cutover

## Blocked by

- Blocked by `issues/029-cut-over-local-event-pipeline.md`

## User stories addressed

- User story 43
- User story 47
- User story 48
