# PRD: Fight Stats Scraper

## Problem Statement

The UFC data pipeline can discover events, scrape fight cards, and update fighter profiles, but it cannot yet ingest per-fight performance data (totals and round-by-round stats) from completed bouts. Without this stage, the pipeline cannot populate `FightStats` and `RoundStats`, which blocks downstream career-stat recalculation and fantasy fight scoring.

Today, fight result summaries may be captured at the event-page level when a card is scraped, but detailed strike, grappling, and control metrics live only on individual fight detail pages on UFC Stats. There is no automated worker that reacts when a fight completes, scrapes that detail page, persists structured stats, and hands work to the next pipeline stage.

Operators also lack durable job tracking for fight-stats scraping: there is no job log table, no retry semantics, and no scale-to-zero worker wired into the existing Pub/Sub infrastructure.

## Solution

Build a **Fight Stats Scraper** as an isolated pipeline stage that mirrors the established fighter-profile worker pattern. An upstream **Fight Results Watcher** (built separately) will publish a Pub/Sub message when a fight's result becomes available. The fight-stats worker will:

1. Subscribe to `fight-stats-jobs` and create or resume a `FightStatsScrapeJob` row per message.
2. Load the fight detail page with Playwright, parse totals and per-round stats for both fighters, and upsert fantasy database records inside a transaction.
3. Mark the job complete only after all dependent writes succeed.
4. Publish a minimal message to `career-stats-jobs` so the Career Stats Worker (future) can recalculate cumulative fighter metrics.
5. Shut down after idle timeout (scale-to-zero), matching other pipeline workers.

Re-scraping the same fight is supported: completed jobs do not block new runs, but persistence must upsert idempotently so duplicate messages or intentional re-runs do not corrupt data.

## User Stories

1. As a **pipeline operator**, I want a Pub/Sub message to trigger fight-stats scraping for a completed fight, so that downstream stages start automatically without manual intervention.

2. As a **pipeline operator**, I want each scrape attempt recorded in a dedicated job log table, so that I can audit status, retries, and failures.

3. As a **pipeline operator**, I want invalid Pub/Sub payloads dropped with an ack, so that poison messages do not block the subscription indefinitely.

4. As a **pipeline operator**, I want transient scrape failures retried up to three times with nack/redelivery, so that temporary network or page-load issues self-heal.

5. As a **pipeline operator**, I want jobs that exceed max retries marked FAILED and acked, so that the subscription does not retry forever.

6. As a **pipeline operator**, I want duplicate in-flight scrapes for the same fight skipped when a RUNNING job already exists, so that parallel workers do not double-scrape the same page.

7. As a **pipeline operator**, I want RETRYING jobs reused on redelivery rather than creating duplicate rows, so that retry state stays coherent.

8. As a **pipeline operator**, I want to re-scrape a fight after a prior COMPLETED job when needed, so that corrected or missing data can be refreshed without manual DB edits.

9. As a **pipeline operator**, I want the worker to idle-shutdown after 60 seconds without messages, so that local and cloud resources are not held open unnecessarily.

10. As a **pipeline operator**, I want SIGTERM/SIGINT handled gracefully, so that container orchestration can stop the worker cleanly.

11. As a **fantasy application**, I want two FightStats rows persisted per completed fight (one per fighter), so that head-to-head comparisons and scoring have per-fighter totals.

12. As a **fantasy application**, I want RoundStats rows persisted per fighter per round, so that round-level scoring can use accurate strike and grappling breakdowns.

13. As a **fantasy application**, I want fight-level metadata (method, round, time, winner, per-fighter result) updated from the detail page when event-page data is incomplete, so that fight records stay authoritative.

14. As a **fantasy application**, I want fight stats writes to be transactional with job completion, so that a job is never marked COMPLETED if stats persistence partially failed.

15. As a **downstream Career Stats Worker**, I want a Pub/Sub message published after successful stats persistence containing at least fight_id, so that I can recalculate cumulative fighter metrics without polling the database.

16. As a **developer**, I want parsing logic isolated in a pure module with no HTTP, ORM, or messaging side effects, so that HTML parsing can be unit-tested with fixtures.

17. As a **developer**, I want scraping orchestration separated from Pub/Sub callback wiring, so that each layer has a single responsibility matching existing pipeline conventions.

18. As a **developer**, I want configuration centralized (timeouts, retry limits, topic names, selectors), so that environment-specific values are not hardcoded across modules.

19. As a **developer**, I want parser tests backed by saved HTML fixtures, so that UFC Stats markup changes are caught in CI without live network calls.

20. As a **developer**, I want consumer tests covering payload validation, job dedup rules, and ack/nack behavior, so that messaging lifecycle regressions are caught early.

21. As a **developer**, I want a documented Pub/Sub message contract for upstream publishers, so that the Fight Results Watcher can integrate without guessing payload shape.

22. As a **developer**, I want Docker Compose to include the fight-stats topic, subscription, and worker service, so that the full pipeline can be exercised locally with the Pub/Sub emulator.

23. As a **developer**, I want a feature doc describing data flow, env vars, and common errors, so that future contributors can operate and extend the stage safely.

24. As a **pipeline architect**, I want this stage to follow the same publish-only upstream / consumer-creates-job pattern as fighter profile scraping, so that pipeline conventions stay consistent.

25. As a **pipeline architect**, I want ARCHITECTURE documentation updated to reflect the chosen entry-point and row-count semantics, so that design docs match implementation.

## Implementation Decisions

### Architectural pattern

- **Entry point:** Pub/Sub only (Option B). Upstream publishes messages; the consumer creates and manages job rows. This matches the fighter profile scraper pattern.
- **Upstream contract:** JSON payload with integer `fight_id` and non-empty string `fight_url`. Topic: `fight-stats-jobs`. Subscription: `fight-stats-jobs-sub`.
- **Upstream boundary:** The Fight Results Watcher publishes only; it does not create `FightStatsScrapeJob` rows. Job creation is owned by the fight-stats consumer.
- **Worker type:** Scale-to-zero long-running Pub/Sub subscriber with idle shutdown after 60 seconds.

### Modules (deep modules with simple interfaces)

| Module | Responsibility | Interface (conceptual) |
|--------|----------------|------------------------|
| **Worker entry** | Django bootstrap, signal handling, delegate to subscriber | `main()` → starts subscriber loop |
| **Consumer** | Payload parse, job lifecycle, ack/nack, idle shutdown | `callback(message)`, `run_subscriber()`, `parse_message_payload(bytes)` |
| **Service** | Playwright fetch, invoke parser, ORM upsert, downstream publish | `process_fight_stats(fight_id, fight_url)` |
| **Parser** | Pure HTML → structured dataclasses | `parse_fight_stats_page(soup)` → metadata + two fighter stat bundles; helpers for landed/attempted and control-time parsing |
| **Config** | Env-driven constants | Timeouts, retry limits, topic/subscription IDs, page-ready selector |

The **parser** is the primary deep module: it encapsulates all UFC Stats fight-detail DOM knowledge behind a stable dataclass output that rarely changes when persistence or messaging evolves.

The **consumer** is a second deep module: it encapsulates dedup rules, retry semantics, and Pub/Sub ack/nack policy behind a thin callback interface.

### Job model and dedup

- New pipeline job model: `FightStatsScrapeJob`, extending the shared base job model with `fight_id`, `fight_url`, standard status/retry/timestamp fields, and an index on `(fight_id, status)`.
- Schema change requires explicit approval before migration.
- Dedup rules (aligned with fighter profile, not the stricter ARCHITECTURE watcher wording):
  - Skip (ack) if a RUNNING job exists for the same `fight_id`.
  - Reuse and promote an existing RETRYING job to RUNNING, refreshing URL and clearing error message.
  - Allow a new RUNNING job when prior jobs are COMPLETED or FAILED (supports intentional re-scrape).

### Parsing and data mapping

- Port parsing logic from the legacy batch scraper library into the pure parser module, replacing pandas DataFrames with dataclasses.
- Scrape fight detail pages with Playwright in the service layer; wait for a CSS selector that indicates stats tables are rendered.
- Produce fight metadata (method, round, time, round format, fighter names, W/L/D results) and two per-fighter stat bundles.
- Each fighter bundle includes summary totals (for FightStats) and a list of per-round stat objects (for RoundStats).
- Parse compound stat strings (e.g. landed/attempted pairs, control time as mm:ss) in pure helper functions.
- Two FightStats rows per fight (one per fighter), not one — consistent with the fantasy schema and bulk-load conventions.
- Resolve fighters from the existing fight record; do not create new fighter rows in this stage.

### Persistence

- Use direct Django ORM writes to fantasy tables (FightStats, RoundStats, Fights), following the precedent set by fights-in-event scraping. No dedicated API endpoint exists for fight stats ingestion.
- Upsert by natural keys: `(fight_id, fighter_id)` for FightStats; `(fight_stats_id, round_number)` for RoundStats.
- Wrap FightStats, RoundStats, Fights metadata updates, and job COMPLETED transition in a single database transaction so partial failure never marks the job complete.
- Update Fights result fields from the detail page when event-page summaries are missing or incomplete; set per-fighter `result` on FightStats rows.

### Downstream handoff

- After successful transaction commit, publish to `career-stats-jobs` with payload `{"fight_id": <int>}`.
- Publish after commit (not inside the transaction) to avoid career-stats processing on rolled-back writes.
- Career Stats Worker is out of scope; minimal payload is sufficient because downstream can query by fight_id.

### Retry and messaging lifecycle

- Max retry count: 3 (consistent with CODE_GUIDELINES and fighter profile worker).
- Invalid payload → log, ack (drop).
- Success → COMPLETED + completed_at, ack.
- Failure under max retries → RETRYING, nack.
- Failure at max retries → FAILED, ack.
- All ack/nack calls occur only inside the Pub/Sub callback.

### Infrastructure

- Register a new Docker Compose worker service using the same backend image as fighter-profile-worker.
- Extend Pub/Sub emulator init to create `fight-stats-jobs` topic and `fight-stats-jobs-sub` subscription.
- Playwright with Chromium required in the worker image (already installed for fighter profile).

### Documentation updates

- Add a feature-level developer doc for the fight-stats stage.
- Update pipeline ARCHITECTURE sections 6–7: watcher publishes only; consumer creates jobs; two FightStats rows per fight.

## Testing Decisions

### What makes a good test

- Test **external behavior** and **contracts**, not internal implementation details.
- Parser tests: given fixture HTML, assert structured output (fighter names, stat counts, parsed integers, round count). No network, no database.
- Consumer tests: given mock Pub/Sub messages and mocked service, assert job row state transitions, skip-when-RUNNING, RETRYING reuse, ack on invalid payload, nack vs ack on failure/retry count.
- Service tests (optional, lower priority): integration-style tests with mocked Playwright and real ORM test DB can verify upsert idempotency; defer if parser + consumer coverage is sufficient initially.

### Modules to test

| Module | Priority | Rationale |
|--------|----------|-----------|
| Parser | **Required** | Deep module; highest value; no I/O; easy fixtures |
| Consumer | **Required** | Job dedup, ack/nack, and retry rules are easy to regress |
| Service | Optional (phase 2) | Heavier setup (Playwright mock + DB); parser + consumer cover most logic |

### Prior art

- Fighter profile consumer tests: callback lifecycle, job creation, skip-on-RUNNING.
- Fights-in-event parser tests: saved HTML fixtures, pure parse assertions.
- Legacy scraper library: reference HTML parsing behavior to validate ported parser output against known fights.

## Out of Scope

- **Fight Results Watcher** — upstream publisher that detects completed fights and publishes to `fight-stats-jobs`.
- **Career Stats Worker** — downstream consumer of `career-stats-jobs`.
- **ScoreFight Job** — final scoring stage.
- **New REST API endpoints** for fight stats ingestion (ORM writes are sufficient for this phase).
- **Historical backfill** of all past fights (future bulk entry point may be added separately).
- **Referee and fight-details text fields** — optional metadata; defer unless needed for scoring.
- **Opponent stat mirror fields** on FightStats (`sig_str_landed_opp`, etc.) — defer unless required by scoring logic in this phase.

## Further Notes

### Grill session decisions (locked)

- Entry point: Pub/Sub only; consumer creates job rows (Option B, same as fighter profile).
- Dedup: skip RUNNING, reuse RETRYING, allow new job after COMPLETED for re-scrape idempotency.

### Legacy reference

The existing batch scraper library under scripts contains working parse logic for UFC Stats fight detail pages (fight results header, alternating fighter stat columns, totals vs significant-strikes sections). The new parser should preserve that behavioral knowledge while conforming to pipeline module boundaries (no pandas, no side effects).

### ARCHITECTURE doc corrections needed at implementation time

- Section 6 (Fight Results Watcher): should state it **publishes** to Pub/Sub only, not creates job rows.
- Section 7 (Fight Stats Scraper): should state the consumer **creates** `FightStatsScrapeJob` rows; output is **two** FightStats rows per fight.

### Local development before upstream exists

Operators can manually publish test messages to `fight-stats-jobs` with a known `fight_id` and `fight_url` from the database to exercise the worker end-to-end without the Fight Results Watcher.

### Implementation order (suggested)

1. Schema approval and job model migration.
2. Parser + parser tests.
3. Service (fetch, parse, transactional upsert).
4. Consumer + worker + consumer tests.
5. Downstream publish to career-stats-jobs.
6. Docker Compose and Pub/Sub init wiring.
7. Feature documentation and ARCHITECTURE updates.
