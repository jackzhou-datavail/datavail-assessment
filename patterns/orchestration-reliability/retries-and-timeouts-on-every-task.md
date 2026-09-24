# Retries and Timeouts on Every Task

**Category:** Orchestration & Reliability

Each task declares how many times it may retry and how long it is
allowed to run, so transient failures self-heal and a hung task fails
loudly instead of running until someone notices.

## Why it matters

The default is the part people miss: **"for most configurations, the
default setting does not retry any tasks on task failure."** A job
created in the UI or a bundle without an explicit retry policy will
fail permanently on the first transient error — a momentary storage
throttle, a brief metastore blip — and page someone for a problem that
would have resolved itself on the next attempt. Databricks' own framing
is that "errors are often transient and resolved through restart."

Timeouts are the opposite failure. Without one, a task that hangs — a
query waiting on a lock, a stream that stops advancing — runs until it
is killed manually. There is no alert for "still running," only an
absence of completion, which is exactly the signal humans are worst at
noticing. With a timeout, the task moves to `Timed Out` and becomes a
failure that alerting can act on.

The interaction between the two is worth knowing precisely: **"if you
configure both Timeout and Retries, the timeout applies to each
retry."** So three retries against a 30-minute timeout is a worst case
of two hours, not thirty minutes — size them together, not separately.

## What good looks like

- An explicit retry count on every task that touches an external
  system or shared storage, with the retry interval measured "between
  the start of the failed run and the subsequent retry run."
- A timeout on every task, set from observed duration with headroom —
  not left blank because nobody knew what to put.
- Retries and timeout sized as a pair against the job's SLA, since the
  timeout applies per attempt.
- **Serverless jobs** left to "auto-optimize retries by default" unless
  there is a specific reason to override.
- **Continuous jobs** understood to use "an exponential backoff retry
  policy" already, so they need a different treatment from scheduled
  ones.
- Retries used for transient faults only. A task that fails
  deterministically will fail three more times and delay the alert;
  that is a bug to fix, not a retry to add.
- Non-idempotent tasks made safe before retries are enabled — a retry
  on a task that half-wrote its output makes things worse. See
  [`../data-ingestion/idempotent-ingestion-with-checkpoints.md`](../data-ingestion/idempotent-ingestion-with-checkpoints.md).

## How to detect

Retry counts and timeout values are job *settings*, and the
`system.lakeflow` tables record run history rather than configuration —
so this is read through the Jobs API (or the bundle YAML in the repo),
not SQL. What system tables do show is the consequence:
`system.lakeflow.job_task_run_timeline` carries `result_state` and
`termination_code`, so repeated failures with the same termination code
and no intervening retry attempt indicate a missing retry policy, and
`TIMED_OUT` states (or task runs with no end time) indicate the timeout
situation from either direction.

## References

- [Configure and edit tasks in Lakeflow Jobs](https://docs.databricks.com/aws/en/jobs/configure-task)
- [Run jobs continuously](https://docs.databricks.com/aws/en/jobs/continuous)
- [Jobs system tables reference](https://docs.databricks.com/aws/en/admin/system-tables/jobs)
