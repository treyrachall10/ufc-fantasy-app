## Parent PRD

`issues/prd.md`

## What to build

Deliver the Event Scraper happy path end-to-end: consume one `event-scrape-jobs` message, create/claim an `EventScrapeJob`, scrape the individual event detail page with Playwright, upsert the event through a pipeline-authenticated API, mark the job `COMPLETED` only after persistence commits, then publish the existing `{"url","event_id"}` payload to `fights-in-event`.

Include the `EventScrapeJob` model/migration, scraper package layers, API upsert contract, Compose worker service, and fixture-based detail-page parser tests. See PRD sections **Event Scraper responsibilities**, **API contracts → Event upsert**, **Job ownership and status transitions**, and **Proposed module shape**.

## Acceptance criteria

- [ ] `EventScrapeJob` model exists (separate from `EventSyncJob`) with URL-oriented claim fields and status lifecycle compatible with other pipeline jobs
- [ ] Pipeline-authenticated event upsert endpoint matches URL first, then `(name, date)`; creates or updates metadata; returns persisted `event_id` and `url`
- [ ] Scraper API client upserts via `PIPELINE_API_BASE_URL` + `PIPELINE_SERVICE_API_KEY`; no ORM writes to `fantasy.Events`
- [ ] Consumer/service scrapes the event detail page, parses name/date/location/canonical URL, upserts, completes the job, then publishes to `fights-in-event`
- [ ] Job is marked `COMPLETED` only after successful upsert commit; fights-in-event publish happens after that commit
- [ ] Compose service `event-scraper-worker` runs with the existing backend image and required env vars
- [ ] Fixture-based tests cover detail-page parser selectors and the happy-path service/API contract (auth, create, URL match update, name/date match update)

## Blocked by

- Blocked by `issues/026-publish-discovered-events.md`

## User stories addressed

- User story 15
- User story 16
- User story 17
- User story 18
- User story 21
- User story 22
- User story 23
- User story 24
- User story 31
- User story 32
- User story 33
- User story 34
- User story 35
- User story 36
- User story 41
- User story 43
- User story 46
