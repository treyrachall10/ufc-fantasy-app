## Parent PRD

`issues/prd.md`

## What to build

Extend the Event Watcher so newly discovered listing rows publish one message each to `event-scrape-jobs`, with no event persistence and no fights-in-event handoff.

Wire local Pub/Sub topic/subscription resources, env vars, identity-set discovery edge cases (same-date events, duplicate listing rows, unknown URL with same date/different name), payload shape, and publish-failure behavior on `EventSyncJob`. See PRD sections **Pub/Sub design**, **Idempotency and deduplication rules**, and **Event Watcher responsibilities**.

## Acceptance criteria

- [ ] Topic `event-scrape-jobs` and subscription `event-scrape-jobs-sub` are created in Compose `pubsub-init` and `init_pubsub_emulator`
- [ ] `.env.example` documents `PUBSUB_EVENT_SCRAPE_TOPIC` and `PUBSUB_EVENT_SCRAPE_SUBSCRIPTION`
- [ ] Watcher publishes one JSON message per unknown event with `event_url`, `event_name`, `event_date`, and optional `location`
- [ ] Watcher publishes nothing when every scraped row is already known
- [ ] Same-date unknown events each get a message; duplicate listing rows collapse to one publish
- [ ] Matching URL is treated as known even if the listing name changed; no rename-driven republish
- [ ] Watcher never inserts/updates `Events`, never publishes to `fights-in-event`, and never calls scraper Python APIs
- [ ] Pub/Sub publish failure surfaces on `EventSyncJob` and fails the command appropriately
- [ ] Tests cover one new event, multiple new events, same-date events, duplicate listing rows, same date/different name/unknown URL, and publish failure

## Blocked by

- Blocked by `issues/025-run-event-watcher-with-no-work.md`

## User stories addressed

- User story 8
- User story 10
- User story 11
- User story 12
- User story 13
- User story 14
- User story 16
- User story 17
- User story 40
- User story 42
- User story 45
