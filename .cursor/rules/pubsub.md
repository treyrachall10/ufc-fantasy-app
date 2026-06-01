# Pub/Sub Rules

## Purpose

These rules apply whenever working with Pub/Sub-style message processing.

Use these rules for:

- topics
- subscriptions
- publishers
- consumers
- callbacks
- ack/nack behavior
- retry behavior
- job status updates
- message-driven workers

The goal is to keep message processing simple, reliable, retry-safe, and easy to debug.

---

## 1. Message Payload Rules

Pub/Sub messages should use small JSON payloads.

Only send the values needed to identify and process the job.

Good examples:

{
  "job_id": 123
}

{
  "record_id": 456,
  "source_url": "https://example.com/item"
}

Do not send:

- full HTML pages
- full parsed objects
- full database models
- large JSON blobs
- data that the consumer should load itself

The message should identify the work.

The consumer or service should do the actual processing.

---

## 2. Payload Parsing Rules

Payload parsing should be done in a separate function.

The parsing function should:

- decode the raw message bytes
- load the JSON
- extract required fields
- validate required values
- return simple values needed by the callback

Example:

def parse_message_payload(raw: bytes) -> tuple[int, str]:
    raw_text = raw.decode("utf-8")
    data = json.loads(raw_text)

    record_id = int(data["record_id"])
    source_url = str(data["source_url"]).strip()

    if not source_url:
        raise ValueError("source_url is empty")

    return record_id, source_url

---

## 3. Invalid Payload Rules

Invalid payloads should be acknowledged and dropped.

Invalid payloads include:

- invalid JSON
- missing required keys
- wrong value types
- empty required values

Do not nack invalid payloads if retrying will not fix the message.

Example:

try:
    record_id, source_url = parse_message_payload(message.data)
except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
    logger.exception("Invalid Pub/Sub payload; acknowledging to drop message: %s", exc)
    message.ack()
    return

---

## 4. Ack/Nack Rules

All ack() and nack() calls must happen inside the subscriber callback.

Ack when:

- processing succeeds
- the message is invalid and should be dropped
- the job is skipped intentionally
- max retries were reached and the job was marked failed

Nack when:

- processing fails
- retry attempts remain
- the message should be retried

Never ack before processing is complete.

Never ack before job status is saved.

Never ack before required writes or updates succeed.

Never nack after max retries are reached.

---

## 5. Job Lookup Rules

If the system uses job tracking, load or create the correct job row before processing.

Do not create duplicate active jobs for the same work item.

If a matching job is already running, skip the message and ack it.

If a matching job is retrying, reuse it and mark it running.

If no active job exists, create a new running job.

---

## 6. Job Status Rules

Job status must match the real processing state.

General success flow:

1. receive message
2. parse payload
3. load or create job
4. mark job as running
5. process job
6. mark job as completed
7. ack message

General failure flow:

1. capture the error
2. increment retry count
3. save the error message
4. if retries remain, mark job as retrying and nack
5. if retries are exhausted, mark job as failed and ack

Common statuses:

PENDING
RUNNING
COMPLETED
RETRYING
FAILED
SKIPPED

---

## 7. Retry Rules

Retry count must be limited by a config value or constant.

Do not allow infinite retries.

If retry count reaches the max retry count:

- mark the job as failed
- save the error message
- ack the message

If retries remain:

- mark the job as retrying
- save the error message
- nack the message

Example:

job.retry_count += 1
job.error_msg = str(error)

if job.retry_count >= MAX_RETRY_COUNT:
    job.status = JobStatus.FAILED
    job.save()
    message.ack()
else:
    job.status = JobStatus.RETRYING
    job.save()
    message.nack()

---

## 8. Completion Rules

A job must only be marked completed after processing succeeds.

Ack the message only after the job is marked completed.

Example:

process_job(job_id)

job.status = JobStatus.COMPLETED
job.completed_at = now()
job.save()

message.ack()

---

## 9. Transaction Rules

Use a transaction when related database updates must succeed together.

Use transactions when:

- marking a job completed
- saving multiple related rows
- job status depends on a successful write
- processing must not be partially saved

Example:

with transaction.atomic():
    job.status = JobStatus.COMPLETED
    job.completed_at = now()
    job.save()

---

## 10. Config Rules

Pub/Sub settings must come from config or constants.

Do not hardcode important Pub/Sub values inside processing logic.

Use config/constants for:

- project id
- topic id
- subscription id
- max retry count
- idle timeout
- batch size
- worker settings

Good:

PROJECT_ID
TOPIC_ID
SUBSCRIPTION_ID
MAX_RETRY_COUNT

Bad:

subscription_id = "my-hardcoded-sub"
max_retry_count = 3

---

## 10a. Docker Pub/Sub Emulator Host

When a publisher or subscriber runs **inside a Docker container**, set:

```text
PUBSUB_EMULATOR_HOST=pubsub:8085
```

Use the Compose **service name** (`pubsub`), not `localhost:8085`. Inside a container, `localhost` is that container — not the emulator.

When running on the **host** (IDE debugger, local shell), use:

```text
PUBSUB_EMULATOR_HOST=localhost:8085
```

Override in `docker-compose.yml` `environment` for containerized services; keep `localhost:8085` in `.env` for host-side runs.

---

## 11. Subscriber Rules

The subscriber should:

- validate required config before starting
- create the subscription path from config
- subscribe using the callback
- log what subscription it is listening on
- shut down cleanly when needed

Example:

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)

---

## 12. Logging Rules

Log important Pub/Sub events.

Log:

- subscriber startup
- invalid payloads
- skipped jobs
- processing failures
- retry decisions
- permanent failures
- shutdown events

Do not log full large payloads unless debugging requires a short preview.

---

## 13. Responsibility Rules

Keep responsibilities separated.

Publisher should handle:

- creating messages
- publishing to the correct topic

Consumer should handle:

- subscribing
- callback flow
- ack/nack decisions
- message parsing
- job status flow

Service or processor should handle:

- actual business logic
- scraping
- API calls
- calculations
- data updates

Config should handle:

- topic names
- subscription names
- retry limits
- environment values

Models or repositories should handle:

- job records
- database reads/writes

Do not put heavy business logic directly inside the callback.