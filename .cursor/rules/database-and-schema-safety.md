# Database and Schema Safety Rules

## Purpose

These rules define how Cursor must handle database schema changes and database write logic.

The goal is to protect the database from unsafe changes, avoid accidental migrations, keep writes consistent, and prevent inefficient database operations.

All Cursor-generated database or schema-related code must follow these rules unless explicitly told otherwise.

---

# 1. Schema and Migration Approval Rules

Before creating new database tables, changing existing schemas, or applying migrations, Cursor must ask for approval first.

Cursor must ask before:

- creating new models
- adding model fields
- removing model fields
- renaming model fields
- creating migrations
- running migrations
- changing relationships between tables

Before implementation, Cursor must provide the proposed schema and wait for approval.

Example approval request:

```txt
I need to create the following table for this phase. Please approve the schema before I create or run migrations.
```

Cursor must not create or run migrations until approval is given.

---

# 2. Proposed Schema Format

When asking for schema approval, Cursor must clearly show:

- table/model name
- fields
- field types
- nullable fields
- default values
- indexes or unique constraints, if needed
- relationships to other tables, if any
- why the schema is needed

Example:

```txt
Proposed model: FighterProfileScrapeJobLog

Fields:
- id: primary key
- raw_ufc_fighter_id: string, required
- profile_url: string, required
- status: string, required
- retry_count: integer, default 0
- error_message: text, nullable
- created_at: datetime
- updated_at: datetime

Reason:
This table tracks fighter profile scraping jobs separately from the main fantasy fighter table.
```

---

# 3. Database Write Rules

When writing multiple records to the database, prefer bulk inserts.

Use bulk inserts for things like:

- fight jobs
- fighter profile jobs
- round stats
- scraped row batches
- job log entries
- any repeated database inserts from a list

Avoid inserting one row at a time inside a loop unless there is a clear reason.

If one-row-at-a-time inserts are used, Cursor must explain why.

---

# 4. Transaction Rules

When writing to the database, use `transaction.atomic` when multiple related operations must succeed together.

Use transactions especially when:

- multiple related records must be created together
- a job status depends on a successful database write
- raw scrape data and job logs are updated together
- fight stats and round stats are created together
- multiple tables must stay consistent

Example:

```python
from django.db import transaction

with transaction.atomic():
    ...
```

Do not mark work as completed until all related database writes inside the transaction have succeeded.

---

# 5. Completion Safety Rule

If a status update depends on a database write, the status should only be marked as complete after the write succeeds.

Cursor must not mark a record, job, or process as completed before its required database writes are finished.

Bad:

```txt
mark COMPLETED
then write records
```

Good:

```txt
write records successfully
then mark COMPLETED
```

---

# 6. Existing Database Logic Reuse Rule

Before creating new database queries, serializers, endpoints, services, helper methods, or model managers, Cursor must inspect the existing codebase first.

Cursor must check for existing:

- model methods
- model managers
- query helpers
- repository methods
- service methods
- serializers
- API views or endpoints

If existing code already supports the needed operation, reuse it instead of creating duplicate database logic.

Do not create duplicate query logic, duplicate service logic, or duplicate endpoints.

---

# 7. Cursor Behavior for Database Work

Before making database-related changes, Cursor must:

- inspect the existing code first
- identify existing database access patterns
- explain what database files it plans to change
- explain why each change is needed
- ask before schema or migration changes
- avoid large database rewrites
- avoid silently changing relationships