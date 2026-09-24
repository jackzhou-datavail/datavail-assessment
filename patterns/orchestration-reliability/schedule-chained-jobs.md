# Schedule-Chained Jobs

> ⚠️ **ANTI-PATTERN**

**Category:** Orchestration & Reliability

Pipeline stages run as separate single-task jobs whose cron schedules
are offset — ingest at 01:00, transform at 02:00, aggregate at 03:00 —
so ordering depends on each stage finishing inside its allotted hour.

## Why it happens

It is the obvious way to build the second stage. The first job exists
and works; the new step needs to run after it; a cron expression an
hour later is one field to fill in and requires no understanding of
task graphs. It also feels safer than coupling them — if the
transformation is a separate job, a bug in it cannot break ingestion.

The offsets are usually generous at first, which is exactly why the
pattern survives. An hour of slack for a twelve-minute job looks like
plenty of margin, so nothing prompts a rethink until the data volume
has quadrupled and the slack is gone.

## Impact

- **Silent staleness.** When the upstream job runs long, the
  downstream one starts anyway and processes yesterday's data. It
  succeeds. The dashboard is wrong and every status indicator is green
  — the worst possible combination.
- Failure does not propagate. Upstream fails, downstream still runs,
  and the alert points at the stage that failed rather than the output
  that is now wrong.
- No repair path. A job with declared structure can be repaired from
  the failed task onward; a chain of separate jobs must be re-run by
  hand, in the right order, by someone who knows what that order is.
- The schedule becomes undocumented architecture. The dependency graph
  exists only in the offsets, so nobody can see it, review it, or
  safely change a start time.
- Slack is wasted time. An hour of padding between every stage turns a
  40-minute pipeline into a 3-hour one, purely as insurance.
- Adding a stage means re-planning every downstream offset.

## How to fix

1. Collapse the chain into one job with tasks wired by explicit
   dependencies, so the platform enforces the order. See
   [`task-dependencies-over-schedule-chaining.md`](task-dependencies-over-schedule-chaining.md).
2. Where stages genuinely belong to different jobs — different owners,
   different SLAs — connect them with the **Run Job** task rather than
   with clock offsets.
3. Use conditional tasks for the branching that the separate-jobs
   design was really trying to express (skip cleanup on failure, run
   backfill only when a flag is set).
4. Once ordering is enforced, remove the padding; the pipeline's
   runtime becomes its actual critical path.
5. Set a duration warning threshold on the consolidated job, since
   lateness is now a single measurable property. See
   [`failure-notifications-and-duration-thresholds.md`](failure-notifications-and-duration-thresholds.md).
6. Define the job in a bundle so the dependency graph is reviewable.

## How to detect

`system.lakeflow.job_tasks.depends_on_keys` is the direct measure: jobs
whose tasks declare no dependencies, combined with
`system.lakeflow.jobs.triggers` showing cron schedules, identify
candidates. Confirm with lineage — where one job's write targets in
`system.access.table_lineage` are another job's read sources, and the
two fire on staggered schedules with no declared dependency between
them, that is a chain. `job_run_timeline` start and end times then show
how much real slack is left, which is the argument for fixing it.

## References

- [Control the flow of tasks within Lakeflow Jobs](https://docs.databricks.com/aws/en/jobs/control-flow)
- [Run Job task for jobs](https://docs.databricks.com/aws/en/jobs/tasks/run-job)
- [Jobs system tables reference](https://docs.databricks.com/aws/en/admin/system-tables/jobs)
