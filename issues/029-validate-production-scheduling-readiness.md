## Parent PRD

`issues/prd.md`

## What to build

Validate production-oriented readiness for the scheduled watcher without checking in Cloud Scheduler/Cloud Run Terraform unless explicitly expanded later.

Manually verify live UFC Stats listing selectors against fixture contracts, and document/verify the Cloud Scheduler → Cloud Run Job → existing backend image → `watch_events` → exit model, including command override, service account permissions, API auth env vars, Playwright/Chromium, timeouts, Pub/Sub publish on `fights-in-event`, and job retry/exit expectations. See PRD sections **Scheduling and Cloud Run deployment** and **Testing Decisions**.

## Acceptance criteria

- [ ] Manual live check confirms listing-page selectors used by `events/shared/` still match UFC Stats
- [ ] No event-detail selector validation is required for Event persistence (listing fields are sufficient)
- [ ] Relative vs absolute event URLs are normalized as required before identity comparison, upsert, and publish
- [ ] Operator-facing notes document Cloud Run Job command override, required env vars, Pub/Sub publish permission on `fights-in-event`, API key auth, Chromium dependency, and timeout expectations
- [ ] Notes state the command is one-shot (no internal sleep loop) and empty work exits successfully
- [ ] No deployment IaC is required for this slice unless product explicitly expands scope
- [ ] Findings from selector drift or URL normalization gaps are recorded as follow-up if they block cutover

## Blocked by

- Blocked by `issues/028-cut-over-local-event-pipeline.md`

## User stories addressed

- User story 29
- User story 32
- User story 34

## Issue change note

**Rewritten.** Former cut-over content moved to `028-cut-over-local-event-pipeline.md`. This file now holds the former `030` scheduling-readiness scope, updated to remove Event Scraper / event-detail scrape requirements.
