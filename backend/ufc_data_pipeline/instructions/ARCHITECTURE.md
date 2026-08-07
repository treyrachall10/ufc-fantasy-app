# UFC Data Pipeline Architecture

## Purpose

This pipeline scrapes UFC event, fight, fighter, result, and stat data in stages. Each stage should do one specific job and pass work downstream using database-backed job records.

The system should be designed so each worker can be run independently, retried safely, and scaled separately later.

## Current Pipeline Flow

Event Watcher
→ Fights In Event Scraper
→ Fighter Profile Scraper
→ Live Event Results Watcher
→ Fight Stats Scraper
→ Career Stats Worker
→ ScoreFight Job

## Core Architecture Rules

- Watchers detect when work needs to happen.
- Scrapers perform a specific scrape task.
- Workers process existing jobs.
- Job records should be stored in the database.
- Downstream work should be triggered by creating/publishing jobs.
- Workers should be idempotent.
- Duplicate in-flight jobs should be avoided; exact dedup rules are stage-specific (for example, the fighter profile worker skips only when a `RUNNING` job exists, but allows a new scrape after `COMPLETED`).
- Bulk inserts should be used when creating many records.
- Related database writes should use transactions when partial writes would corrupt the pipeline.
- Each stage should update its job status.
- Each stage should log start, success, skip, and failure states.

## 1. Event Watcher

### Role

Scheduled job (one-shot command; no internal sleep loop).

### Responsibility

The Event Watcher discovers new completed UFC events from the listing page, persists missing `Events` through the main API, and publishes fights-in-event work. Listing fields (name, date, location, URL) are sufficient to persist an Event; there is no separate Event Scraper stage and no event-detail scrape for Event persistence.

### Flow

1. Create/update an `EventSyncJob` for this run (`RUNNING`).
2. Load stored event identities through the pipeline-authenticated discovery API.
3. Scrape the completed-events listing (`http://ufcstats.com/statistics/events/completed?page=all`).
4. Compare scraped rows against stored URLs and `(name, date)` pairs (identity-set comparison; not date-only cutoff alone).
5. For each unknown event, upsert through the pipeline-authenticated event API (URL match first, then name+date).
6. After each successful upsert, publish `{"url": <event_url>, "event_id": <int>}` to `fights-in-event`.
7. Mark `EventSyncJob` `COMPLETED` on success (including no work) or fail the job/command on persistence or publish errors.
8. Exit.

### Backfill mode

`watch_events --backfill-from YYYY-MM-DD` replays every unique listing event on or after an inclusive, strictly-parsed source-date cutoff (known and unknown alike) through the same `SetEvent` upsert and unchanged `{"url", "event_id"}` contract. It reuses canonical `event_id` values, fills missing stored URLs, and never deletes events outside the range. There is no backfill Pub/Sub marker, new topic, or separate orchestrator; replay safety is provided by idempotent downstream processing (issue 031). Completion status is never forced — it stays HTML-derived in the Fights In Event Scraper.

### Boundary

- Must not write `fantasy.Events` through Django ORM.
- Must not create `EventScrapeJob` rows or publish to an event-scrape topic.
- Must not scrape individual event detail pages solely to persist Events.
- Downstream fight discovery remains the Fights In Event Scraper’s job.
- Backfill must not force fight completion or introduce a backfill-specific contract.

### Output

- Upserted `Events` rows (via API)
- Pub/Sub messages on `fights-in-event` with `event_id` and `url`
- One `EventSyncJob` row per watcher execution

### Production scheduling

Package as Cloud Scheduler → Cloud Run Job → existing backend image → `python manage.py watch_events` → exit (one-shot; empty work exits successfully). Operator checklist (command override, env vars, IAM, Chromium, timeouts, URL normalization, live listing selector verification) lives in `events/event_watcher/docs/event-watcher.md`. Deployment Terraform is out of scope until a later issue expands it.

## 2. Fights In Event Scraper

### Role

Scale-to-zero worker.

### Responsibility

The Fights In Event Scraper processes one event and discovers all fights attached to that event. It also detects whether each fight is already completed on the event page and, when it is, scrapes the result summary fields available there (winner, method, round, time, and round format when present). Fighter rows are resolved via the existing get-or-create flow (profile URL preferred, normalized name as fallback).

### Flow

1. Receive event_id and event_url.
2. Scrape all fights from that event page (bout, weight class, fight URL, and related metadata).
3. For each fight row, detect completed vs upcoming from the event-page result banner and set `fight_status` to `COMPLETED` or `UPCOMING`.
4. For completed fights, parse available result summary fields from the event page and resolve `winner` using batch fighter lookup after fighters are ensured to exist.
5. For each fight, get or create both fighters.
6. Bulk insert fight records.
7. Publish fighter profile scrape messages to Pub/Sub for new fighters and for existing fighters whose `profile_url` was backfilled (see `fights_in_event/parser.py` → `ensure_fighters_exist`).

### Output

Creates:

- Fight records (including `fight_status` and event-page result summaries when already completed)
- Pub/Sub messages on `fighter-profile-jobs` for downstream profile scraping (consumer creates `FighterProfileScrapeJob` rows when processing)

### Boundary

This worker must not scrape individual fight detail pages or deep per-round fight stats. Event-page result summaries are in scope here; detailed stats and round-level data remain downstream (Fight Stats Scraper). For live events, the Live Event Results Watcher detects completion on the event page and publishes Fight Stats work.

## 3. Fighter Profile Scraper

### Role

Scale-to-zero worker (Pub/Sub consumer + Playwright scraper).

### Responsibility

The Fighter Profile Scraper consumes Pub/Sub messages for individual fighter profile pages, scrapes metadata with Playwright, and updates fighter records via the main API service.

### Flow

1. Receive a Pub/Sub message: `{fighter_id, fighter_url}` (published by `fights_in_event`).
2. Create or resume a `FighterProfileScrapeJob` row (`RUNNING`). Skip only if another job for the same fighter is already `RUNNING`; reuse `RETRYING`; allow new runs after `COMPLETED`.
3. Load the profile page with Playwright (Chromium).
4. Parse name from `.b-content__title-highlight` (split into first/last), nickname from `.b-content__Nickname`, and tale-of-the-tape stats from `ul.b-list__box-list`.
5. `PATCH /api/fighters/<fighter_id>/SetFighterProfile`.
6. Mark the job `COMPLETED` or `FAILED` / `RETRYING`.

### Required Modes

This worker should support:

- processing one fighter profile job from Pub/Sub
- bulk processing fighters missing profile data (future / not yet implemented as a separate entry point)

### Local / Docker notes

- Pub/Sub emulator host must be `localhost:8085` on the host and `pubsub:8085` inside docker-compose.
- Chromium must be installed in the Docker image (`playwright install --with-deps chromium` in `backend/Dockerfile`).
- Worker idle shutdown is controlled by `WORKER_IDLE_SHUTDOWN_ENABLED` (Compose disables it for local development).

## 4. Live Event Results Watcher

### Role

Scheduled one-shot job (Cloud Scheduler → Cloud Run Job → existing backend image → `python manage.py watch_live_event_results` → exit). Replaces the former planned separate DB Event Watcher and permanent-polling Fight Results Watcher.

### Responsibility

Select the newest stored event through the pipeline discovery API, apply a required IANA timezone date gate (today/yesterday), load one event fight snapshot, claim an API-owned event lease, fetch the UFC Stats event page at most once when eligible, reconcile fights by normalized URL, persist cancellations/restorations/completions through pipeline APIs, publish durable Fight Stats and Fights In Event rescrape handoffs, and exit.

### Flow

1. Fail fast on missing/invalid `LIVE_EVENT_RESULTS_TIMEZONE` or missing pipeline API base URL/key.
2. Load newest event via discovery API; no event exits successfully (`no_event`).
3. Load LiveResultsSource snapshot (fights + handoff state).
4. If date-ineligible and no pending handoffs → successful `date_ineligible` (no lease, no scrape).
5. Claim event lease (active other owner → successful `active_lease_skip`).
6. If terminal (no upcoming fights, no unresolved handoffs) → complete lease and exit without scrape.
7. If date-ineligible with pending work → drain Fight Stats / due rescrape publications only (`pending_without_scrape`); no UFC Stats fetch.
8. Else fetch event page once, renew lease, compare card, apply cancel/restore/complete transitions, ensure/publish rescrape handoffs, drain Fight Stats handoffs, renew during progress, complete or fail the lease, exit.

### Output

- Fight status transitions and durable handoff/lease state via API
- Pub/Sub `fight-stats-jobs` messages `{"fight_id", "fight_url"}` (unchanged contract)
- Pub/Sub `fights-in-event` messages `{"url", "event_id"}` plus optional card-change metadata for replacement recovery

### Boundary

- Must not write fantasy/domain or watcher-state tables through Django ORM.
- Must not create Fight rows or scrape full fight-detail stats.
- Must not start containers or run a permanent poll/sleep/subscriber loop.
- Deployment Terraform / scheduler IaC is out of scope until a follow-up adds it.

### Production scheduling

Package as Cloud Scheduler (every 10 minutes) → Cloud Run Job → existing backend image → `python manage.py watch_live_event_results` → exit. Operator checklist (command override, env vars, IAM, Chromium, timeouts, leases, rescrape exhaustion) lives in `fights/live_event_results/docs/live-event-results.md`.

## 5. Fight Stats Scraper

### Role

Scale-to-zero worker.

### Responsibility

The Fight Stats Scraper consumes `fight-stats-jobs`, creates/manages `FightStatsScrapeJob` rows, scrapes the UFC Stats fight detail page, and upserts fight metadata and stats through the main API service.

### Flow

1. Receive a Pub/Sub message (`fight_id`, `fight_url`).
2. Create or resume a `FightStatsScrapeJob` (skip if `RUNNING`; reuse `RETRYING`; allow a new job after `COMPLETED` / `FAILED`).
3. Scrape the fight detail page with Playwright.
4. Parse metadata, two fighter total bundles, and per-round stats.
5. Persist via API:
   - `PATCH .../SetFightResultMetadata` (fight result fields)
   - `PATCH .../SetFightStatsTotals` (**two** `FightStats` rows, one per fighter)
   - `PATCH .../SetRoundStats` (per-round rows)
6. Mark the `FightStatsScrapeJob` `COMPLETED` after API writes succeed.
7. Publish `{"fight_id": <int>}` to `career-stats-jobs` **after** the COMPLETED commit.

### Output

Creates/updates:

- `FightStatsScrapeJob` rows (pipeline-owned)
- Fight result metadata on `Fights` (via API)
- **Two** `FightStats` rows per fight (via API)
- `RoundStats` rows (via API)
- Downstream Pub/Sub message on `career-stats-jobs`

### Transaction / consistency rule

Do not mark the job `COMPLETED` if API writes fail. Publish career-stats only after the COMPLETED status has committed so rolled-back or failed scrapes do not trigger downstream work.

### Local operation

Without the Live Event Results Watcher, operators can publish test messages with:

```bash
docker compose exec web python manage.py enqueue_fight_stats \
  --fight-id <id> \
  --fight-url '<ufcstats fight-details url>'
```

See `backend/ufc_data_pipeline/fights/fight_stats/docs/fight-stats.md`.

## 6. Career Stats Worker

### Role

Scale-to-zero Pub/Sub worker (`career-stats-worker` in Compose).

### Responsibility

After fight stats are persisted, recalculate cumulative `FighterCareerStats` for both fighters on the triggering fight (full replace, not incremental), then hand off to score-fight.

### Entry / messaging

- **Inbound:** `career-stats-jobs` / `career-stats-jobs-sub` with payload `{"fight_id": <int>}` only (published by the Fight Stats Scraper after COMPLETED, or via `enqueue_career_stats`).
- **Outbound:** `score-fight-jobs` with `{"fight_id": <int>}`, published **after** the `CareerStatsJob` row is committed as `COMPLETED`.

### Persistence

Fantasy writes go through the main API only (pipeline auth):

1. `GET /api/fights/<fight_id>/CareerStatsSource` — both fighters’ completed FightStats histories for recalc.
2. `PATCH /api/fighters/<fighter_id>/SetFighterCareerStats` — full-replace upsert per fighter (`select_for_update` on the fighter row).

The worker owns only pipeline job state (`CareerStatsJob`). It does not query fantasy tables via ORM.

### Flow

1. Receive `fight_id` from Pub/Sub.
2. Claim/create `CareerStatsJob` (skip if `RUNNING`; reuse `RETRYING`; new row after `COMPLETED`/`FAILED`).
3. Load source rows via CareerStatsSource.
4. Pure counters recalculate win/loss/draw, method buckets, additive sums, and `total_fight_time`.
5. Upsert both fighters’ career stats via SetFighterCareerStats.
6. Mark job `COMPLETED`, then publish to `score-fight-jobs`.
7. On failure: `RETRYING` + nack, or `FAILED` + ack after max retries; do **not** publish.

### Boundary

- Assume fight-stats rows already exist (no readiness poll).
- Exclude NC (`Could Not Continue` / similar + null result) from tallies.
- The Score Fight Worker (section 7) consumes `score-fight-jobs` downstream.

See `backend/ufc_data_pipeline/fighters/career_stats/docs/career-stats.md`.

## 7. Score Fight Worker

### Role

Scale-to-zero Pub/Sub worker (`score-fight-worker` in Compose). Final pipeline stage.

### Responsibility

After career stats are updated, score every round and the full fight for both fighters and atomically persist the complete `FightScore` / `RoundScore` state.

### Entry / messaging

- **Inbound:** `score-fight-jobs` / `score-fight-jobs-sub` with payload `{"fight_id": <int>}` only (published by the Career Stats Worker after COMPLETED, or via `enqueue_score_fight`).
- **Outbound:** none — this is the terminal stage.

### Persistence

Fantasy writes go through the main API only (pipeline auth), one GET and one PATCH per fight:

1. `GET /api/fights/<fight_id>/ScoringSource` — fight metadata plus both fighters' complete round stats. Returns 409 `SCORING_SOURCE_INCOMPLETE` (retryable) when inputs are missing and 422 `SCORING_SOURCE_UNSCOREABLE` (permanent, e.g. No Contest) when the outcome cannot be scored.
2. `PATCH /api/fights/<fight_id>/SetFightScoring` — atomic full replace: resolve all `RoundStats` in one query, bulk upsert `FightScore` + `RoundScore`, delete stale `RoundScore` rows.

The worker owns only pipeline job state (`ScoreFightJob`). It does not query fantasy tables via ORM.

### Flow

1. Receive `fight_id` from Pub/Sub.
2. Claim/create `ScoreFightJob` (skip if `RUNNING`; reuse `RETRYING`; new row after `COMPLETED`/`FAILED`; advisory lock guards cross-instance races).
3. Load the scoreable snapshot via ScoringSource.
4. Pure scoring module (`scoring.py`) calculates per-round category points and fight totals (win/round/time bonuses; draws score without winner bonuses).
5. Persist everything via SetFightScoring.
6. Mark job `COMPLETED` and ack.
7. On unscoreable outcome: `FAILED` + ack immediately (no retry). On other failures: `RETRYING` + nack, or `FAILED` + ack after max retries (3).

### Boundary

- Assume fight stats and round stats already exist (no readiness poll); missing inputs surface as retryable 409s.
- Scoring math lives in the pure module only; the legacy batch scripts import the same per-category functions.

### Language Decision

Implemented in Python/Django like the rest of the pipeline. Go can be considered later if scoring becomes performance-heavy or if this becomes a separate service.

See `backend/ufc_data_pipeline/fantasy/score_fight/docs/score-fight.md`.

## End-to-End Success Criteria

The full pipeline is successful when:

1. New events are discovered.
2. Events are scraped and stored.
3. Fights are discovered and stored.
4. Fighter profile jobs are created for new fighters.
5. Fighter profiles are scraped.
6. Live Event Results detects completions/cancellations/replacements for the newest eligible event.
7. Fight stats and round stats are stored.
8. Career stats are updated.
9. Final fight scores are calculated and stored.