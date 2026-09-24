# Monolithic Single-Task Jobs

> ⚠️ **ANTI-PATTERN**

**Category:** Orchestration & Reliability

A job is one task running one long notebook that ingests, transforms,
aggregates, and publishes — so any failure fails everything, and
recovery means re-running the whole thing from the start.

## Why it happens

The notebook came first. It was written top to bottom during
development, it worked, and scheduling it was a single click. Splitting
it into tasks means deciding where the seams are, parameterising the
hand-offs, and testing each piece — real work with no visible benefit
on the day the job already runs fine.

It is also self-reinforcing. Because the notebook shares state between
its sections (a DataFrame defined in cell 4 used in cell 20), splitting
it later requires materialising intermediate results, which feels like
added complexity rather than removed risk.

## Impact

- **No granular recovery.** A failure in the last step re-runs the
  first, so a two-minute bug costs a ninety-minute rerun — and if the
  early steps are expensive, the cost is real money each time.
- Repair runs cannot help. The repair feature restarts from the failed
  task; with one task, that is the whole job.
- No parallelism. Independent work runs sequentially because there is
  no structure expressing that it is independent, so the job takes as
  long as the sum of its parts.
- Failure diagnosis is archaeology — the run failed, and the cause is
  somewhere in an hour of logs rather than attributed to a named task.
- Retries become dangerous rather than helpful: retrying a monolith
  re-executes work that already succeeded, which for non-idempotent
  steps means duplicated writes.
- One compute configuration for everything, so a small step and a
  heavy step share a cluster sized for the heavy one.
- The job is the notebook, which drags the whole
  [`../platform-onboarding/notebooks-as-production-code.md`](../platform-onboarding/notebooks-as-production-code.md)
  problem along with it.

## How to fix

1. Split at the natural boundaries — ingest, transform, aggregate,
   publish — with each step writing a durable table rather than passing
   in-memory state.
2. Wire the steps with explicit dependencies so ordering is enforced
   and repair can restart mid-graph. See
   [`task-dependencies-over-schedule-chaining.md`](task-dependencies-over-schedule-chaining.md).
3. Run genuinely independent branches in parallel and let the critical
   path shorten on its own.
4. Give each task its own retry policy and timeout, sized to what that
   step actually does. See
   [`retries-and-timeouts-on-every-task.md`](retries-and-timeouts-on-every-task.md).
5. Move the logic out of the notebook into importable modules, so each
   task is a thin entry point that can also be unit tested.
6. Where the split is genuinely hard because steps share expensive
   state, materialise that state deliberately — the intermediate table
   is usually worth having anyway.

## How to detect

`system.lakeflow.job_tasks` gives task counts per `job_id` directly:
jobs with exactly one task are the candidate set. The ones that matter
are the long-running members of that set, so join to
`system.lakeflow.job_task_run_timeline` for duration and rank by it —
a single-task job running two minutes is fine, one running two hours is
the finding. Failure rate from `result_state` sharpens it further,
since a long monolith that fails often is where rerun cost
concentrates.

## References

- [Control the flow of tasks within Lakeflow Jobs](https://docs.databricks.com/aws/en/jobs/control-flow)
- [Configure and edit tasks in Lakeflow Jobs](https://docs.databricks.com/aws/en/jobs/configure-task)
- [Jobs system tables reference](https://docs.databricks.com/aws/en/admin/system-tables/jobs)
