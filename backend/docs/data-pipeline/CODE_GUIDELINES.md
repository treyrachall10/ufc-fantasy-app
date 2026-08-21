# Code Guidelines

## Purpose

These rules define how code must be written inside the UFC data pipeline. The goal is to keep the project simple, readable, safe to run, and easy to debug.

All Cursor-generated code must follow these rules unless explicitly told otherwise.

---

# 1. General Coding Rules

## Simplicity

* Implementation must be simple and readable.
* Prefer clear code over clever code.
* Do not over-engineer unless the architecture explicitly requires it.
* Do not add unnecessary abstractions.
* Do not rewrite existing working code unless the current phase requires it.

## Scope Control

* Only implement the current requested phase.
* Do not jump ahead to future phases.
* Do not add unrelated features.
* Do not change architecture decisions without asking first.

---

# 2. Function Comment Rules

Every function must have a short comment directly above it.

The comment must explain:

* what the function does
* what parameters it receives, if any
* what it returns, if anything

Example:

```python
# Receives a fight job id and returns the matching fight job if it exists.
# This function is used before processing a fight job to verify the job is valid.
def get_fight_job(job_id):
    ...
```

If the function does not receive parameters or return anything, say that clearly.

Example:

```python
# Receives no parameters and returns nothing.
# This function starts the scheduled event watcher.
def start_event_watcher():
    ...
```

---

# 3. Loop and Try/Except Comment Rules

Every loop must have a one-line comment directly above it explaining why the loop exists.

Example:

```python
# Loop through each scraped fight so each fight can be converted into a database job.
for fight in scraped_fights:
    ...
```

Every `try/except` block must have a one-line comment directly above it explaining what risky operation is being attempted.

Example:

```python
# Try to process the job so failures can be logged and retried safely.
try:
    ...
except Exception as error:
    ...
```

---

# 4. Inline Comment Rules for Chained Calls

When class functions are chained together or multiple function calls are used in one line, add a short inline comment explaining what the line is doing.

Example:

```python
result = scraper.load_page(url).parse_fights().to_job_rows()  # Loads the event page, parses fights, and converts them into job rows.
```

If the chained call becomes hard to read, break it into multiple simple lines instead.

---

# 5. Main Database and API Service Rules

The pipeline must not directly read from or write to the main fantasy database tables.

When data must be requested from the main application database, the pipeline must call the appropriate API service.

When data must be written to the main application database, the pipeline must call the appropriate API service.

The pipeline should treat the main application database as owned by the main API service.

## Rules

* Do not directly query main fantasy tables from the pipeline.
* Do not directly write to main fantasy tables from the pipeline.
* Use API service calls when the pipeline needs data from the main application.
* Use API service calls when the pipeline needs to create or update main application data.
* Keep raw scraping data and pipeline job data in the pipeline’s own tables.
* Store raw ids, source URLs, UFC ids, and job ids in pipeline tables.
* Do not create direct database relationships from pipeline job tables to fantasy application tables unless explicitly approved.

## Existing Views Rule

Before creating new queries, serializers, endpoints, services, or helper methods, always check for existing views first.

Cursor must inspect the existing codebase for:

* existing API views
* existing service methods
* existing serializers
* existing repository methods
* existing model managers
* existing query helpers

If an existing view or service already supports the needed operation, reuse it instead of creating a new one.

Do not create duplicate API endpoints or duplicate service logic.

---

# 6. Database Write Rules

## Bulk Inserts

When writing multiple records to the database, prefer bulk inserts.

Use bulk inserts for things like:

* fight jobs
* fighter profile jobs
* round stats
* scraped row batches
* job log entries

Avoid inserting one row at a time inside a loop unless there is a clear reason.

## Transactions

When writing to the database, use `transaction.atomic`.

Use transactions especially when:

* multiple related records must be created together
* a job status depends on a successful database write
* raw scrape data and job logs are updated together
* fight stats and round stats are created together

Example:

```python
from django.db import transaction

with transaction.atomic():
    ...
```

---

# 7. Job Log Rules

Every pipeline section must have its own database job log table.

Examples:

* EventWatcherJobLog
* EventScrapeJobLog
* FightsInEventScrapeJobLog
* FighterProfileScrapeJobLog
* FightResultsWatcherJobLog
* FightStatsScrapeJobLog
* CareerStatsJobLog
* ScoreFightJobLog

Each section should log:

* when the job starts
* when the job finishes
* when the job fails
* retry count
* relevant raw ids or external ids
* error message if failed

## Completion Rule

A job log should only be marked as `COMPLETED` after the item has been successfully written or updated in its respective table.

Do not mark a job as `COMPLETED` before database writes are finished.

Allowed statuses:

```txt
PENDING
RUNNING
COMPLETED
FAILED
SKIPPED
```

---

# 8. Raw ID and Fantasy Table Separation Rules

Pipeline job logs and scrape jobs should not directly depend on the main fantasy tables.

Instead, job logs should store raw identifiers and reference values such as:

* raw UFC event id
* raw UFC fight id
* raw UFC fighter id
* source URL
* scraped page URL
* internal job id
* processing status
* retry count

The pipeline should avoid directly referencing fantasy application tables unless the specific phase explicitly requires it and the access happens through the correct API service.

The scraping/data-ingestion pipeline should stay separate from fantasy scoring and fantasy user-facing data.

---

# 9. Pub/Sub Rules

The pipeline uses Pub/Sub for message passing.

## Topic and Subscription Naming

Topic and subscription names should be simple and readable.

Example:

```txt
topic = fight-jobs
subscription = fight-jobs-sub
```

Good names:

```txt
event-jobs
event-jobs-sub

fighter-profile-jobs
fighter-profile-jobs-sub

fight-stats-jobs
fight-stats-jobs-sub

career-stats-jobs
career-stats-jobs-sub

score-fight-jobs
score-fight-jobs-sub
```

Avoid overly long or unclear names.

## Ack/Nack Rule

Acknowledging or negatively acknowledging Pub/Sub messages must happen inside the callback function.

Google explicitly states that if ack/nack is done outside the callback, the action may not be respected.

Rules:

* Ack only after successful processing.
* Nack when the job should be retried.
* If max retry count is exceeded, mark the job as `FAILED` and ack the message so it does not retry forever.
* Do not ack before database writes are complete.
* Do not ack before job status is updated.

---

# 10. Retry Rules

Use `tenacity` for retrying job processing.

Each job should have a maximum of 3 processing attempts.

If the retry count exceeds the allowed number of attempts:

1. mark the job as `FAILED`
2. save the error message
3. stop retrying
4. move on to the next job

Do not allow infinite retries.

---

# 11. Scraping Rules

Use Playwright for web requests and scraping.

Reason:

* the UFC website uses JavaScript
* Playwright can load dynamic content
* Playwright helps avoid missing data that does not appear in raw HTML requests

Do not switch back to simple request-based scraping unless explicitly told to.

---

# 12. Configuration Rules

Use config files for values that may change.

Examples:

* polling time
* sleep time
* max retry count
* bulk insert size
* number of records to process
* Pub/Sub topic names
* Pub/Sub subscription names
* Playwright timeout values
* database batch sizes

Do not hardcode values like:

```python
time.sleep(300)
max_retries = 3
bulk_size = 500
```

unless they are loaded from config or constants.

---

# 13. Migration and Schema Approval Rules

Before creating new database tables, changing existing schemas, or applying migrations, ask for approval first.

Cursor must ask before:

* creating new models
* adding model fields
* removing model fields
* renaming model fields
* creating migrations
* running migrations
* changing relationships between tables

Before implementation, provide the proposed schema and wait for approval.

Example request:

```txt
I need to create the following table for this phase. Please approve the schema before I create or run migrations.
```

---

# 14. Job Processing Rules

Each job processor should follow this general flow:

1. receive message from Pub/Sub
2. parse job id or raw id
3. load job log from the database
4. mark job as `RUNNING`
5. process the job
6. write/update the target data table
7. mark job as `COMPLETED`
8. ack the Pub/Sub message

If processing fails:

1. capture the error
2. increment retry count
3. if retries remain, mark job appropriately and nack the message
4. if retries are exceeded, mark job as `FAILED` and ack the message

---

# 15. Duplicate Job Rules

Before creating a new job, check whether one already exists.

If a Pub/Sub job already exists as `PENDING`, skip it.

If it is `RUNNING` with an unexpired `lease_expires_at`, skip it (another worker is presumed to still own it).

If it is `RUNNING` with an expired or null lease, reclaim **that same row** for the current Pub/Sub message (worker-crash recovery). Do not insert a second active job.

If it is `RETRYING`, reclaim the same row.

If the previous job is `COMPLETED` or `FAILED`, the current phase may create a new job for a new message id when intentional reprocessing is allowed.

---

# 16. Logging Rules

Each job should log useful information, including:

* job id
* raw source id
* source URL
* start time
* finish time
* status
* retry count
* number of records created
* number of records skipped
* error message if failed

Logs should be clear enough to debug the pipeline without guessing what happened.

---

# 17. Testing Rules

Each phase should include or update tests when possible.

Tests should verify:

* jobs are created correctly
* duplicate jobs are not created
* job status changes correctly
* failed jobs are marked as failed
* completed jobs are only completed after database writes
* bulk inserts create the expected records
* Pub/Sub messages are acked or nacked correctly
* API service calls are used instead of direct main fantasy table access when interacting with main application data

Do not skip tests unless explicitly told to.

---

# 18. Cursor Behavior Rules

Cursor must:

* inspect the existing code before editing
* check for existing views/services before creating new ones
* create an implementation plan before changing code
* ask before schema or migration changes
* stay within the current phase
* avoid large rewrites
* explain what files it plans to change
* explain why each change is needed
* not silently change architecture decisions

---

# Worker, Consumer, Service, and Folder Structure Rules

## Worker Rule

A worker is the overall background process.

Workers are responsible for:

- starting the process
- loading configuration
- initializing dependencies
- starting the correct consumer
- keeping the process alive
- handling graceful shutdown

Workers should not contain the main business logic.

Example: fighter_profile_worker.py

# 19. If Statement Comment Guideline

For any if statement that is more complex than a simple boolean check, add a short comment directly above it explaining what the condition is checking in plain English.

Simple boolean checks do not need comments.

Example:

# Check if this fight row has a completed fight result banner.
if row.find("i", class_="b-flag__text"):
    fight_status = "COMPLETED"

Avoid comments that repeat the code exactly. The comment should explain the purpose of the condition.

# 20. Scraping Comment Guideline

For scraping logic, add a short comment that explains exactly what the selector is grabbing from the website in plain English.

The comment should describe the real page element or data being scraped, not just the HTML tag or class name.

Example:

# Get the two fighter profile links/names listed in this fight row.
fighter_links = row.find_all("a", class_="b-link b-link_style_black")

# Get the completed-fight result banner from this fight row.
result_banner = row.find("i", class_="b-flag__text")

# Get the method, round, and time result columns from this fight row.
result_columns = row.find_all("td", class_="b-fight-details__table-col")

When possible, comments should explain the data being extracted from the site, such as winner name, fighter profile URL, method, round, time, event date, or fight status.