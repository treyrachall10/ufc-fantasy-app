# UFC Data Pipeline Architecture

## Purpose

This pipeline scrapes UFC event, fight, fighter, result, and stat data in stages. Each stage should do one specific job and pass work downstream using database-backed job records.

The system should be designed so each worker can be run independently, retried safely, and scaled separately later.

## Current Pipeline Flow

Event Watcher
→ Event Scraper
→ Fights In Event Scraper
→ Fighter Profile Scraper
→ DB Event Watcher
→ Fight Results Watcher
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
- Duplicate jobs should not be created if a pending, running, or completed job already exists.
- Bulk inserts should be used when creating many records.
- Related database writes should use transactions when partial writes would corrupt the pipeline.
- Each stage should update its job status.
- Each stage should log start, success, skip, and failure states.

## 1. Event Watcher

### Role

Scheduled job.

### Responsibility

The Event Watcher checks whether new UFC events exist on the UFC website compared to the newest event stored in the database.

### Flow

1. Get the most recent event from the database.
2. Check the UFC website for available events.
3. Compare website events against the latest stored event.
4. If new events exist, create EventScrapeJob records.
5. Do not scrape full event details directly.

### Output

Creates EventScrapeJob records.

## 2. Event Scraper

### Role

One-and-done job worker.

### Responsibility

The Event Scraper processes one EventScrapeJob and creates the event record.

### Flow

1. Receive an EventScrapeJob.
2. Scrape the UFC event page.
3. Add or update the Event record.
4. Save the event URL and event ID.
5. Create/publish a FightsInEventScrapeJob.

### Output

Creates a FightsInEventScrapeJob containing:

- event_id
- event_url

## 3. Fights In Event Scraper

### Role

Scale-to-zero worker.

### Responsibility

The Fights In Event Scraper processes one event and discovers all fights attached to that event.

### Flow

1. Receive event_id and event_url.
2. Scrape all fights from that event page.
3. For each fight, get or create both fighters.
4. Create fight records or FightCreationJob records.
5. Bulk insert fight jobs.
6. If a new fighter is created, create a FighterProfileScrapeJob.

### Output

Creates:

- Fight records or FightCreationJob records
- FighterProfileScrapeJob records for newly discovered fighters

### Boundary

This worker must not scrape detailed fight stats or fight results.

## 4. Fighter Profile Scraper

### Role

Scale-to-zero worker.

### Responsibility

The Fighter Profile Scraper scrapes individual fighter profile pages.

### Flow

1. Receive a FighterProfileScrapeJob.
2. Scrape the fighter profile URL.
3. Update fighter metadata and profile stats.
4. Mark the job completed or failed.

### Required Modes

This worker should support:

- processing one fighter profile job
- bulk processing fighters missing profile data

## 5. DB Event Watcher

### Role

Scheduled job.

### Responsibility

The DB Event Watcher checks whether the newest event in the database is happening today or recently enough to begin watching for fight results.

### Flow

1. Query the newest event in the database.
2. Check whether the event date is today or yesterday.
3. If yes, trigger/start the Fight Results Watcher.
4. If no, do nothing.

### Boundary

This job should only check the database. It should not scrape UFC.com.

## 6. Fight Results Watcher

### Role

Temporary polling worker.

### Responsibility

The Fight Results Watcher watches an active event for fight result availability.

### Flow

1. Query fights for the active event.
2. Use the saved event URL or fight URLs.
3. Poll for the fight results badge.
4. If no result badge exists, sleep for 5 minutes.
5. If a result badge exists, check whether a FightStatsScrapeJob already exists.
6. If a pending, running, or completed job exists, skip.
7. If no job exists, create a FightStatsScrapeJob.

### Output

Creates FightStatsScrapeJob records.

### Boundary

This watcher should not scrape full fight stats directly.

## 7. Fight Stats Scraper

### Role

Scale-to-zero worker.

### Responsibility

The Fight Stats Scraper scrapes raw fight performance data for a completed fight.

### Flow

1. Receive a FightStatsScrapeJob.
2. Scrape raw fight performance data.
3. Create fighter fight metadata.
4. Create one FightStats row.
5. Bulk create RoundStats rows.
6. Update the FightStatsScrapeJob status.
7. Create/publish a CareerStatsJob.

### Output

Creates:

- Fighter fight metadata
- FightStats row
- RoundStats rows
- CareerStatsJob

### Transaction Rule

FightStats, RoundStats, and job status updates should be handled safely so the job is not marked completed if dependent writes fail.

## 8. Career Stats Worker

### Role

Scale-to-zero worker.

### Responsibility

The Career Stats Worker recalculates cumulative fighter stats after a completed fight.

### Flow

1. Receive fight_id, fighter_ids, round_stat_ids, and/or fight_stat_id.
2. Query completed FightStats rows for the fighters.
3. Query fighter history if needed.
4. Calculate cumulative totals.
5. Calculate win/loss totals if needed.
6. Update or create career stat records.
7. Create/publish a ScoreFightJob.

### Boundary

Only completed fight stats should be used for career stat calculations.

## 9. ScoreFight Job

### Role

Final scoring worker.

### Responsibility

The ScoreFight Job scores individual rounds and the full fight after stats and career data are finalized.

### Flow

1. Query finalized FightStats.
2. Query finalized RoundStats.
3. Score each round.
4. Score the overall fight.
5. Store final score results.

### Language Decision

Do not use Go yet. Keep the scoring job in the same language/framework as the rest of the pipeline until the full pipeline works end-to-end.

Go can be considered later if scoring becomes performance-heavy or if this becomes a separate service.

## End-to-End Success Criteria

The full pipeline is successful when:

1. New events are discovered.
2. Events are scraped and stored.
3. Fights are discovered and stored.
4. Fighter profile jobs are created for new fighters.
5. Fighter profiles are scraped.
6. Active events are detected.
7. Fight result availability is watched.
8. Fight stats and round stats are stored.
9. Career stats are updated.
10. Final fight scores are calculated and stored.