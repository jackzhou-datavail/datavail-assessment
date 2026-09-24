# Failure Notifications and Duration Thresholds

**Category:** Orchestration & Reliability

Every production job notifies a team — not an individual — when it
fails, and carries a duration warning threshold so a job that is merely
*late* is noticed before it becomes an incident.

## Why it matters

Notifications are "emails or webhooks to be sent when a job fails or
takes too long," configurable "at the task or job level." Without them,
the detection mechanism for a failed pipeline is a person opening the
Jobs UI, or a downstream consumer asking why a number looks wrong. Both
are slow, and the second is expensive because the bad data has already
been used.

Duration thresholds cover the failure mode that alerting usually
misses. A job that fails produces an event; a job that takes four hours
instead of twenty minutes produces nothing at all until it finally
finishes. Setting an expected completion time turns lateness into a
signal, which matters most for the pipelines feeding a morning
dashboard — being late is the failure, whether or not the run
eventually succeeds.

For streaming work, the equivalent is the streaming backlog threshold:
a stream that is technically running but falling further behind is
healthy by every binary measure and useless in practice.

## What good looks like

- Failure notifications on every production job, routed to a **group
  alias or an on-call webhook**, never to the individual who happened
  to create the job.
- Webhooks into the team's existing incident channel where one exists,
  so job alerts arrive where people already look.
- A duration warning threshold on jobs with a downstream commitment,
  set from observed p95 runtime rather than from hope.
- Streaming backlog metric thresholds configured on continuous and
  streaming workloads.
- Task-level notifications used sparingly, for the specific step whose
  failure needs different handling from the job's.
- Alerts that mean something: if a job alerts every week and nobody
  acts, that is a broken job or a wrong threshold, not background noise
  to be filtered.
- Notification configuration deployed in the bundle alongside the job,
  so a new environment gets alerting without a manual step.

## How to detect

Notification and threshold settings live in the job configuration, so
they are read through the Jobs API or the bundle YAML rather than
system tables. What system tables give you is the impact:
`system.lakeflow.job_run_timeline` carries `result_state` and
`termination_code`, so you can rank jobs by failure count and by how
long failures persisted before the next successful run. A job with
repeated failures over many days is, in practice, a job nobody is being
told about — which is the finding, arrived at from the other end.

## References

- [Configure and edit Lakeflow Jobs](https://docs.databricks.com/aws/en/jobs/configure-job)
- [Configure and edit tasks in Lakeflow Jobs](https://docs.databricks.com/aws/en/jobs/configure-task)
- [Jobs system tables reference](https://docs.databricks.com/aws/en/admin/system-tables/jobs)
