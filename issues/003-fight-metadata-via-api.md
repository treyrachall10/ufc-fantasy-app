## Parent PRD

`issues/prd.md`

## What to build

First **real scrape vertical**: load a fight detail page, parse fight-level metadata, and persist it through the **main API service** — not direct fantasy ORM writes from the pipeline service.

End-to-end behavior for this slice:

1. Playwright loads the fight detail page and waits for a ready selector
2. Pure parser extracts metadata: method, round, time, round format, fighter names, W/L/D results
3. Service maps parser output to an API payload
4. **Create or reuse an API endpoint** (e.g. patch fight result metadata by `fight_id`) if one does not exist; implement `api_client.py` with authenticated HTTP calls matching the fighter-profile pattern
5. Consumer calls real `process_fight_stats` instead of the stub
6. Job marked `COMPLETED` only after API call succeeds

Parser tests use saved HTML fixtures (metadata section only). No FightStats or RoundStats in this slice.

See parent PRD: **Parsing and data mapping** (metadata portion), **Persistence** (via API, not ORM).

## Acceptance criteria

- [ ] Parser returns structured fight metadata from a fixture HTML file
- [ ] Parser tests pass without network or database
- [ ] Playwright fetch with retry loads a fight detail page in the service layer
- [ ] API endpoint exists for updating fight result metadata by `fight_id`
- [ ] `api_client` calls the endpoint with service API key auth; pipeline service does not import fantasy ORM models for writes
- [ ] End-to-end: valid message → fight metadata updated in DB via API → job `COMPLETED`
- [ ] Scrape failure or API failure leaves job not `COMPLETED` (basic error propagation; full retry rules in slice 006)

## Blocked by

- `issues/002-pubsub-job-consumer-skeleton.md`

## User stories addressed

- User story 13
- User story 16
- User story 19
