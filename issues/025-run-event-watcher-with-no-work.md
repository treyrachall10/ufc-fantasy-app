## Parent PRD

`issues/prd.md`

## What to build

Deliver the Event Watcher no-work path end-to-end: a pipeline-authenticated discovery snapshot API, a watcher API client, shared completed-events listing parser under `events/shared/`, identity comparison against stored URL and `(name, date)` sets, `EventSyncJob` run tracking, and `python manage.py watch_events` that completes successfully and exits when nothing new is found.

This slice must not insert `Events` rows, must not publish to `fights-in-event`, and must not invoke the Event Scraper. See PRD sections **Event Watcher responsibilities**, **API contracts → Discovery snapshot**, **Proposed module shape**, and **Idempotency and deduplication rules**.

## Acceptance criteria

- [ ] `GET /api/events/DiscoverySource` exists, requires `HasAPIKey` + `IsPipelineService`, and returns `latest_event` plus the full stored identity set including `event_id`, name, date, and URL
- [ ] Empty database returns `200` with `latest_event: null` and `events: []`
- [ ] Shared listing parser and listing URL/config live under `events/shared/` (not inside watcher or scraper packages)
- [ ] Existing listing parser tests move/replace into `events/shared/tests/` and cover fixture-based selector contracts
- [ ] Watcher loads discovery via API client only; no direct ORM reads of `fantasy.Events`
- [ ] Watcher scrapes the completed-events listing, compares by URL and `(name, date)`, and publishes nothing when all rows are known
- [ ] Each command run creates/updates an `EventSyncJob`; no-work success marks it `COMPLETED` and the command exits 0
- [ ] Tests cover: no stored events, no newly discovered events, existing name+date match, existing URL match, API discovery failure, UFC Stats timeout, parser failure, and command exits cleanly with no work

## Blocked by

None - can start immediately

## User stories addressed

- User story 1
- User story 2
- User story 3
- User story 4
- User story 5
- User story 6
- User story 7
- User story 9
- User story 10
- User story 11
- User story 12
- User story 29
- User story 30
- User story 35
- User story 37
- User story 38
- User story 45
- User story 46
