# All-Purpose Compute for Scheduled Jobs

> ⚠️ **ANTI-PATTERN**

**Category:** Platform Onboarding

Scheduled, non-interactive workloads run on all-purpose (interactive)
clusters — often a long-lived shared cluster that never terminates —
instead of job compute, serverless, or a SQL warehouse.

## Why it happens

It is the path of least resistance during onboarding. A developer
builds a pipeline interactively on an all-purpose cluster, it works,
and scheduling it against that same cluster is one dropdown away.
Attaching to an existing running cluster also *feels* cheaper and
faster than a job cluster that has to start — the startup delay is
visible, and the DBU rate difference is not.

The shared-cluster habit compounds it: one always-on cluster that
"everyone uses" avoids per-team setup, so nobody turns it off, and it
accrues charges through nights and weekends whether or not anything is
running on it.

## Impact

- Direct and measurable cost: Databricks states that non-interactive
  workloads on job compute "cost significantly less than on all-purpose
  compute." The same work, on the wrong compute type, is billed at the
  interactive rate.
- Idle spend. An all-purpose cluster kept alive for a nightly job is
  paid for around the clock; job compute exists only for the run's
  duration, and serverless "terminate[s] idle compute resources to save
  costs."
- Resource contention and non-reproducibility — a shared interactive
  cluster carries whatever libraries and Spark configs the last user
  installed, so a job's environment is a moving target.
- Blast radius: a heavy ad-hoc query on the shared cluster can starve
  or fail the scheduled pipeline sharing it.
- SQL workloads on all-purpose compute also forgo the Photon
  acceleration that comes with SQL warehouses.

## How to fix

1. Move scheduled work to serverless compute first — it's the
   recommended default and removes the sizing question entirely. See
   [`serverless-first-compute.md`](serverless-first-compute.md).
2. Where classic compute is required, use **job compute** (a job
   cluster per run), not all-purpose.
3. Route SQL and BI workloads to SQL warehouses, sized by the
   size-for-latency / count-for-concurrency rule.
4. Enforce it rather than documenting it: compute policies can restrict
   which compute a job may attach to, and can mandate auto-termination
   and autoscaling bounds on what remains. See
   [`compute-policies-and-standard-sizing.md`](compute-policies-and-standard-sizing.md).
5. For streaming that doesn't need real-time latency, use the
   `AvailableNow` trigger instead of an always-on cluster.

## How to detect

`system.billing.usage` distinguishes the compute type by `sku_name` —
all-purpose DBUs attributable to scheduled runs are the finding, and
the query that lands is "spend on all-purpose SKUs, grouped by job."
`system.lakeflow.job_run_timeline` joined to `system.compute.clusters`
identifies which scheduled jobs attach to clusters whose
`cluster_source` is `UI` or `API` rather than `JOB`.
`system.compute.node_timeline` exposes utilization, which is how you
find the always-on cluster that is mostly idle.
`data_collection/collect_data.py` reads `system.lakeflow.*` for run
history but not `system.billing.*` or `system.compute.*`, so the cost
half of this check isn't wired up in this repo yet.

## References

- [Best practices for cost optimization](https://docs.databricks.com/aws/en/lakehouse-architecture/cost-optimization/best-practices)
- [Phase 8: Design compute strategy](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/compute)
- [Create and manage compute policies](https://docs.databricks.com/aws/en/admin/clusters/policies)
