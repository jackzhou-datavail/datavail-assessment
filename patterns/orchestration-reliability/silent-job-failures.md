# Silent Job Failures

> ⚠️ **ANTI-PATTERN**

**Category:** Orchestration & Reliability

Production jobs fail with nobody told. No failure notification is
configured, or it goes to one person's inbox, so a broken pipeline is
discovered days later by whoever notices the numbers stopped moving.

## Why it happens

Notifications are optional and a job runs fine without them. During
development the author watches runs directly, so alerting adds nothing;
by the time the job is production, nobody remembers that the watching
was manual. The job is quietly promoted from "thing I am observing" to
"thing the business depends on" without the configuration catching up.

Where alerts do exist they often point at an individual — the creator's
address, filled in by default. That works until the person is on
holiday, changes teams, or filters the messages because the job alerts
weekly for a known-noisy reason. Alert fatigue then does the rest: a
job that cries wolf every Tuesday trains everyone to ignore it, which
is functionally the same as having no alert.

## Impact

- **Detection latency measured in days.** The realistic discovery path
  is a downstream consumer asking why a figure looks wrong, by which
  point the wrong figure has been used.
- Bad or stale data propagates. Every consumer downstream of the failed
  job keeps serving whatever it last had, with no indication the data
  is frozen.
- Backfills grow expensive with delay — a day of missed ingestion is
  routine, three weeks is a project.
- Trust erodes faster than it can be rebuilt. Stakeholders who have
  been burned by a silent failure start maintaining their own shadow
  numbers, which is a permanent tax.
- Failures attributed to a departed employee's alerts are invisible
  twice: the job fails, and the notification bounces.
- Without alerting, nobody knows the *rate* of failure, so there is no
  case for investing in the fix.

## How to fix

1. Add failure notifications to every production job, routed to a group
   alias or on-call webhook — never to an individual. See
   [`failure-notifications-and-duration-thresholds.md`](failure-notifications-and-duration-thresholds.md).
2. Add a duration warning threshold so "late" alerts too; a job that
   never finishes never fails.
3. Add retry policies so the transient failures that generate most of
   the noise resolve themselves and stop desensitising the team. See
   [`retries-and-timeouts-on-every-task.md`](retries-and-timeouts-on-every-task.md).
4. Fix or retire the chronically noisy jobs. An alert that fires
   routinely and is routinely ignored is worse than none, because it
   trains the response.
5. Review failure rates from system tables on a cadence, so jobs
   failing without anyone noticing are caught by the review even when
   the alerting is missing.
6. Deploy notification settings in the bundle, so a new environment is
   never silently un-alerted.

## How to detect

Whether notifications are configured is a job setting, read through the
Jobs API or the bundle YAML. The measurable consequence lives in
`system.lakeflow.job_run_timeline`, which carries `result_state` and
`termination_code`: compute the success rate per job over the window,
then look for the telling shape — **repeated failures over consecutive
days with no change in outcome**. A job failing the same way for a week
is definitionally one nobody is being told about. Rank those by whether
anything downstream reads their output, via
`system.access.table_lineage`.

## References

- [Configure and edit Lakeflow Jobs](https://docs.databricks.com/aws/en/jobs/configure-job)
- [Jobs system tables reference](https://docs.databricks.com/aws/en/admin/system-tables/jobs)
- [Observability from system tables](../platform-onboarding/observability-from-system-tables.md)
