## Parent PRD

`issues/prd.md`

## What to build

Extend the Event Watcher so each unknown listing event is persisted through a pipeline-authenticated upsert API using listing fields (name, date, location, URL), then publish `{"url", "event_id"}` to the existing `fights-in-event` topic.

This replaces the former plan to publish `event-scrape-jobs` or run a separate Event Scraper. Do not add `EventScrapeJob`, detail-page scraping, or a scraper worker. See PRD sections **API contracts → Event upsert**, **Event Watcher responsibilities**, and **Pub/Sub design**.

## Acceptance criteria

- [ ] Pipeline-authenticated event upsert endpoint exists (`HasAPIKey` + `IsPipelineService`)
- [ ] Upsert matches URL first, then `(event, date)`; creates or updates metadata; returns persisted `event_id` and `url`
- [ ] Watcher API client upserts via `PIPELINE_API_BASE_URL` + `PIPELINE_SERVICE_API_KEY`; no ORM writes to `fantasy.Events`
- [ ] For each unknown listing event, watcher upserts then publishes `{"url", "event_id"}` to `PUBSUB_FIGHTS_IN_EVENT_TOPIC`
- [ ] Watcher publishes/upserts nothing when every scraped row is already known
- [ ] Same-date unknown events each get an upsert + publish; duplicate listing rows collapse to one
- [ ] Matching URL is treated as known even if the listing name changed; no rename-driven re-upsert/republish
- [ ] No `event-scrape-jobs` topic/subscription/env vars and no `event-scraper-worker`
- [ ] Tests cover: upsert API auth/create/URL-match/name-date-match; one new event; multiple new events; same-date events; duplicate listing rows; same date/different name/unknown URL

## Blocked by

- Blocked by `issues/025-run-event-watcher-with-no-work.md`

## User stories addressed

- User story 8
- User story 9
- User story 10
- User story 11
- User story 12
- User story 13
- User story 14
- User story 18
- User story 19
- User story 20
- User story 21
- User story 22
- User story 24
- User story 27
- User story 28
- User story 30
- User story 31

## Issue change note

**Rewritten.** Former content (publish to `event-scrape-jobs` only) is deleted. Merges the persistence/publish responsibilities previously planned for issues 026–027 under the separate Event Scraper design.
