## Parent PRD

`issues/prd.md`

## What to build

Complete the stats ingestion path by persisting **per-round stats** for each fighter through the API layer.

End-to-end behavior:

1. Parser extended to extract per-round stat rows for each fighter (totals + significant-strikes sections per round)
2. **Create or reuse an API endpoint** to bulk upsert `RoundStats` rows keyed by `(fight_stats_id, round_number)` or equivalent `(fight_id, fighter_id, round_number)` contract
3. `api_client` sends round stat payloads; service orchestrates fight-stats ID resolution if needed via API read or bundled upsert
4. Full scrape path: metadata + FightStats totals + RoundStats in one `process_fight_stats` call
5. Job `COMPLETED` only after all API writes succeed

Parser fixture tests cover multi-round fights. Old fights with missing stats should fail gracefully with a logged error (not silent empty rows).

See parent PRD: **Parsing and data mapping** (round portion), **Persistence**.

## Acceptance criteria

- [ ] Parser returns per-round stat lists for both fighters from fixture HTML
- [ ] Parser tests cover round count and field mapping for at least one multi-round fight fixture
- [ ] API endpoint bulk upserts RoundStats without direct pipeline ORM writes to fantasy tables
- [ ] End-to-end: message → FightStats rows from slice 004 plus RoundStats rows for each round per fighter
- [ ] Natural key upsert: re-running scrape updates existing round rows rather than duplicating

## Blocked by

- `issues/004-fightstats-totals-via-api.md`

## User stories addressed

- User story 12
- User story 14
