# Pub/Sub Processing Skill

## Purpose

Use this skill when working with Pub/Sub-style message processing.

This skill applies to:

- publishers
- consumers
- subscriber callbacks
- payload parsing
- ack/nack behavior
- retry behavior
- job status updates
- worker startup
- debugging messages that are not being consumed
- debugging messages that retry too much
- debugging duplicate processing

The goal is to guide how Pub/Sub work should be approached before editing code.

---

## 1. Understand The Message Flow First

Before changing Pub/Sub code, identify the full message flow.

Expected flow:

1. publisher sends message
2. subscriber receives message
3. callback runs
4. payload is parsed
5. job is loaded or created, if job tracking exists
6. service or processor handles the actual work
7. job status is updated, if job tracking exists
8. message is acked or nacked

Do not edit Pub/Sub code until this flow is understood.

---

## 2. Inspect Existing Files First

Before creating new Pub/Sub code, inspect the existing related files.

Check for:

- publisher file
- consumer or subscriber file
- worker file
- config file
- service or processor file
- job model or repository file
- local Pub/Sub setup, if relevant

Do not create a new file if an existing file already owns that responsibility.

---

## 3. Classify The Task

Before coding, decide what type of Pub/Sub task it is.

Use this guide:

- Bad message data -> payload parsing
- Messages retry too much -> retry and ack/nack logic
- Duplicate processing -> job lookup and status checks
- Worker receives no messages -> config, topic, subscription, Docker, or startup logic
- Wrong processing result -> service or processor logic
- Callback is too large -> move business logic into a service or processor
- Message is acknowledged too early -> callback flow and status update logic
- Message is never removed -> max retry and ack logic

---

## 4. Keep The Callback Focused

The callback should control the message flow.

Good callback responsibilities:

- parse the payload
- handle invalid payloads
- load or create the job, if needed
- call the service or processor
- update job status, if needed
- ack or nack the message

Bad callback responsibilities:

- doing heavy business logic directly
- scraping directly
- parsing large HTML directly
- doing large database update logic directly
- making the callback hundreds of lines long
- mixing unrelated workflow logic into message handling

---

## 5. Use The Ack/Nack Decision Guide

Use this decision guide before changing ack/nack behavior.

Ack when:

- processing succeeds
- payload is invalid and should be dropped
- job is skipped intentionally
- max retries are reached and the job is marked failed

Nack when:

- processing fails
- retries remain
- the message should be retried

Never ack before processing finishes.

Never ack before job status is saved, if job tracking exists.

Never nack forever.

---

## 6. Preserve Small Message Payloads

Pub/Sub messages should identify the work, not carry all the work.

Good payload examples:

{
  "job_id": 123
}

{
  "record_id": 456,
  "source_url": "https://example.com/item"
}

Avoid changing the payload format unless both the publisher and consumer are updated intentionally.

---

## 7. Preserve Config Usage

Use config or constants for Pub/Sub values.

Check config before hardcoding anything.

Common config values:

- project id
- topic id
- subscription id
- max retry count
- idle timeout
- batch size
- worker settings

Do not hardcode these values inside processing logic.

---

## 7a. Docker and Pub/Sub Emulator Host

When using the **Pub/Sub emulator** with Docker Compose, `PUBSUB_EMULATOR_HOST` must match **where the process runs**, not where the emulator is published on the host.

| Process runs on | Set `PUBSUB_EMULATOR_HOST` to |
|-----------------|-------------------------------|
| Host (IDE debugger, local terminal) | `localhost:8085` |
| Another Docker container on the same Compose network | `pubsub:8085` (the **service name**, not `localhost`) |

**Why:** Inside a container, `localhost` refers to that container itself. The emulator runs in the `pubsub` service, so workers started from `web`, `fighter-profile-worker`, or an ad-hoc `docker compose exec web` shell must use the Docker network hostname `pubsub:8085`.

**Symptom:** Worker starts and appears healthy, but no messages are consumed and no job rows are written — publish succeeds from host or another container, yet the subscriber never receives callbacks.

**Fix:** Override `PUBSUB_EMULATOR_HOST` in `docker-compose.yml` for any service that publishes or subscribes from inside Docker:

```yaml
environment:
  PUBSUB_EMULATOR_HOST: pubsub:8085
```

Keep `PUBSUB_EMULATOR_HOST=localhost:8085` in `.env` for host-side development; Compose `environment` overrides take precedence inside containers.

Reference: `fighter-profile-worker` and `web` in `docker-compose.yml`.

---

## 8. Debugging Guide

If messages are not being consumed, check:

- worker or container is running
- **`PUBSUB_EMULATOR_HOST` matches host vs container** (see section 7a)
- project id is correct
- topic exists
- subscription exists
- subscription is connected to the expected topic
- publisher is publishing to the expected topic
- worker logs show subscriber startup
- callback is not crashing before useful logs appear

If messages retry forever, check:

- retry count is incrementing
- max retry count is enforced
- failed jobs are acked
- retrying jobs are nacked
- permanent failures are not being nacked

If duplicate processing happens, check:

- existing running jobs are skipped
- skipped jobs are acked
- retrying jobs are reused correctly
- the same message is not being published multiple times
- multiple subscriptions are not unintentionally processing the same topic

---

## 9. Implementation Plan Format

Before editing Pub/Sub code, use this short plan:

Pub/Sub Plan

1. Issue:
   - Briefly describe the problem.

2. Current flow:
   - Explain how the message currently moves through the system.

3. Files to inspect:
   - List the files that need inspection.

4. Files to change:
   - List only the files that need edits.

5. Risk:
   - Mention ack/nack, retry, duplicate job, config, or schema risk.

6. Schema impact:
   - State whether schema changes are needed.
   - If yes, ask before changing models or migrations.

---

## 10. Final Check

Before finishing Pub/Sub work, verify:

- payload parsing is separate
- invalid payloads are acked
- ack/nack happens inside callback
- successful processing acks only after work is complete
- failed processing increments retry count, if retries are tracked
- retryable failure nacks
- max retry failure acks
- config values are used
- callback does not contain heavy business logic
- publisher and consumer agree on payload format