# Unbounded Task Execution

> ⚠️ **ANTI-PATTERN**

**Category:** Orchestration & Reliability

Tasks run with no timeout and no retry policy — the platform default —
so a transient error kills the run permanently and a hung task runs
until a human kills it.

## Why it happens

Both settings are optional and blank by default, and a blank field
prompts nobody. Leaving the timeout empty also feels like the cautious
choice: putting a number there risks killing a legitimately slow run,
and nobody knows what the right number is on day one, so it stays
empty forever.

Retries are skipped for the opposite reason — they feel like masking a
problem. That instinct is right for deterministic bugs and wrong for
the far more common case: **"for most configurations, the default
setting does not retry any tasks on task failure,"** while in practice
"errors are often transient and resolved through restart." The default
therefore converts routine infrastructure noise into pages.

## Impact

- Transient failures page a human at 3am for something a single
  automatic retry would have fixed. This is the largest avoidable
  source of alert fatigue in most workspaces.
- **A hung task produces no event at all.** It is not failed, so
  nothing alerts; it is not finished, so nothing downstream proceeds.
  The pipeline is stopped and every indicator says "running."
- A runaway task holds compute for as long as it runs. On a classic
  cluster that is billed continuously; on serverless it is still paid
  for by the second.
- Downstream dependents wait indefinitely, so one unbounded task stalls
  an entire graph and the impact looks like a platform problem.
- Without timeouts there is no enforced SLA — "this job must finish by
  6am" is an intention rather than a property of the system.
- Recovery is manual and therefore slow and inconsistent: someone must
  notice, decide the task is stuck rather than slow, and cancel it.

## How to fix

1. Set an explicit timeout on every task, derived from observed p95
   runtime with headroom. A wrong-but-present timeout beats no timeout,
   and it can be tuned once you have data.
2. Add retries for tasks touching external systems or shared storage,
   remembering that **"if you configure both Timeout and Retries, the
   timeout applies to each retry"** — so size the pair against the
   job's SLA, not independently.
3. Leave serverless jobs to "auto-optimize retries by default" unless
   you have a specific reason to override, and treat continuous jobs
   separately since they already use "an exponential backoff retry
   policy."
4. Make tasks idempotent before enabling retries; retrying a task that
   half-wrote its output makes the problem worse. See
   [`../data-ingestion/idempotent-ingestion-with-checkpoints.md`](../data-ingestion/idempotent-ingestion-with-checkpoints.md).
5. Do not paper over deterministic failures with retries — a task that
   fails the same way three times has a bug, and the retries only
   delay the alert.
6. Pair timeouts with duration warning thresholds so "slower than
   expected" is caught before "killed at the limit." See
   [`failure-notifications-and-duration-thresholds.md`](failure-notifications-and-duration-thresholds.md).

## How to detect

Retry and timeout values are job configuration, read via the Jobs API
or the bundle YAML rather than SQL. System tables show the symptoms:
in `system.lakeflow.job_task_run_timeline`, `result_state` of
`TIMED_OUT` and task runs with a start but no end are the hung cases,
while consecutive failed runs sharing a `termination_code` with no
intervening retry attempt indicate a missing retry policy. Duration
outliers — runs far above the task's own median — are the third
signal, and the one that usually identifies the task worth fixing
first.

## References

- [Configure and edit tasks in Lakeflow Jobs](https://docs.databricks.com/aws/en/jobs/configure-task)
- [Run jobs continuously](https://docs.databricks.com/aws/en/jobs/continuous)
- [Jobs system tables reference](https://docs.databricks.com/aws/en/admin/system-tables/jobs)
