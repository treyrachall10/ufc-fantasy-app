## Parent PRD

`issues/prd.md`

## What to build

Extend the scrape path to persist **per-fighter fight totals** (two `FightStats` rows per fight) through the API layer.

End-to-end behavior:

1. Parser extended to extract summary/totals stat blocks for both fighters (KD, sig strikes, total strikes, takedowns, sub attempts, reversals, control time, significant-strike breakdown fields)
2. Pure helpers parse compound strings (`"19 of 32"`, `"1:23"`) into integer fields
3. **Create or reuse an API endpoint** to upsert fight-level stats for both fighters in one call (or two calls) by `fight_id` + `fighter_id`
4. `api_client` sends parsed totals; service does not write to fantasy tables directly
5. Job `COMPLETED` only after API upsert succeeds

Two rows per fight (one per fighter), keyed by `(fight_id, fighter_id)`. Fighter IDs resolved from the existing fight record — do not create new fighters.

Parser fixture tests cover totals sections. Port behavioral knowledge from the legacy batch scraper library.

See parent PRD: **Parsing and data mapping**, **Persistence** (upsert via API).

## Acceptance criteria

- [ ] Parser returns two fighter summary stat bundles from fixture HTML
- [ ] Parser tests assert landed/attempted parsing and control-time conversion
- [ ] API endpoint upserts two `FightStats` rows per fight (create or update)
- [ ] Pipeline service uses `api_client` only — no direct fantasy ORM writes
- [ ] End-to-end: message for a known fight → two `FightStats` rows exist with correct totals
- [ ] Per-fighter `result` (W/L/D) set on each FightStats row

## Blocked by

- `issues/003-fight-metadata-via-api.md`

## User stories addressed

- User story 11
- User story 14
