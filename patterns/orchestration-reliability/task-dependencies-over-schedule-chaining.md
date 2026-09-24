# Task Dependencies Over Schedule Chaining

**Category:** Orchestration & Reliability

Execution order is expressed as declared dependencies between tasks
inside a job, so the platform knows what must finish before what — not
as separate jobs whose schedules are offset far enough apart that the
first one is "probably done."

## Why it matters

Lakeflow Jobs lets you "control the execution order of tasks by
specifying dependencies between them," running tasks "in sequence or
parallel," and building "branching flows that include conditional
tasks, error correction, or cleanup." A declared dependency is a fact
the scheduler enforces. A 30-minute schedule offset is a guess that
holds until the upstream job gets slower, and then fails silently by
processing yesterday's data.

The difference shows up most sharply on failure. When task B depends on
task A and A fails, B does not run — and the job reports one failure
with a clear cause. When B is a separate job scheduled later, B runs
happily on stale input and succeeds, so the alert you get is for A
while the damage is in B's output.

Dependencies also unlock repair. A job with declared structure can be
repaired from the failed task onward; a chain of separate jobs has to
be re-run by hand, in order, by someone who knows the order.

## What good looks like

- One job per logical unit of work, containing the tasks that must
  succeed together, wired with explicit dependencies.
- Parallel branches where steps are genuinely independent, so the
  critical path is the real critical path and not an artifact of how
  someone sequenced it.
- Conditional tasks (run-if) for branching, error correction, and
  cleanup, rather than a downstream job that inspects a table to guess
  whether it should proceed.
- Cross-job dependencies expressed with the **Run Job** task, so a job
  can depend on another job without falling back to schedule offsets.
- Tasks named for what they do, since task keys are what
  `depends_on_keys` references and what an operator reads at 2am.
- The whole graph defined in a bundle, so the dependency structure is
  reviewable in a pull request.

## How to detect

`system.lakeflow.job_tasks` carries `job_id`, `task_key`, and
**`depends_on_keys`** — so dependency structure is directly
measurable. The primary signal is multi-task jobs where no task
declares a dependency: work that is grouped but not ordered. The
complementary signal comes from `system.lakeflow.jobs.triggers`
combined with `job_run_timeline` start times: distinct single-task jobs
firing on staggered cron schedules, where one job's targets are another
job's sources in `system.access.table_lineage`, is schedule chaining in
its observable form.

## References

- [Control the flow of tasks within Lakeflow Jobs](https://docs.databricks.com/aws/en/jobs/control-flow)
- [Run Job task for jobs](https://docs.databricks.com/aws/en/jobs/tasks/run-job)
- [Jobs system tables reference](https://docs.databricks.com/aws/en/admin/system-tables/jobs)
