# Compute Right-Sizing from Utilization Data

**Category:** Platform Onboarding

Cluster sizes and instance types are adjusted from measured CPU and
memory utilization — reviewed on a schedule — instead of being set once
at creation and copied forward forever.

## Why it matters

Initial sizing is a guess. It is usually a generous one, because an
undersized cluster fails visibly and an oversized one fails only on the
invoice. Without a feedback loop, the generous guess becomes the
template for the next cluster too. The data to close that loop already
exists: `system.compute.node_timeline` records per-node utilization
(`cpu_user_percent`, `cpu_system_percent`, `cpu_wait_percent`,
`mem_used_percent`, network and disk) for classic compute.

Right-sizing isn't only about shrinking. A cluster spending most of its
time in `cpu_wait_percent` is I/O-bound and may need a different
instance family, not fewer nodes; memory pinned near 100% with spill
suggests fewer, larger workers — Databricks' own advice for complex ETL
is "fewer workers to reduce the amount of data shuffled" with larger
instances.

## What good looks like

- A recurring (monthly or quarterly) review of the top-spend clusters
  and job compute against their utilization, with changes applied
  through the compute policy or bundle — not hand-edited in the UI.
- Autoscaling bounds set from observed load; `max_autoscale_workers`
  reached regularly means it's too low, never approached means it's too
  high.
- Instance family chosen for the workload profile (memory-, compute-, or
  storage-optimized; GPU only for GPU libraries).
- Single-node compute for analysis and ML experimentation that doesn't
  need a cluster.
- Serverless adopted where it removes the sizing decision entirely — see
  [`serverless-first-compute.md`](serverless-first-compute.md). The
  SQL-warehouse version of this pattern is
  [`../sql-analytics/serverless-sql-warehouses.md`](../sql-analytics/serverless-sql-warehouses.md).

## How to detect

Aggregate `system.compute.node_timeline` by `cluster_id` over 30 days
(average and p95 of `cpu_user_percent + cpu_system_percent` and
`mem_used_percent`, workers only via `is_driver = false`), join
`system.compute.clusters` for `worker_node_type`, `num_workers`,
`min_autoscale_workers` / `max_autoscale_workers`, and join
`system.billing.usage` (`usage_metadata.cluster_id`) for cost. Rank
clusters with high cost and low p95 utilization — that list is the
right-sizing backlog. Driver-only activity on a multi-node cluster
(workers idle while the driver is busy) is a strong signal of
non-distributed code on distributed compute.

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **FinOps › Compute right sizing** — *primary.* Are cluster sizes and instance types adjusted from measured utilization (`system.compute.node_timeline`)? Which high-cost clusters have low utilization?

## References

- [Compute system tables reference](https://docs.databricks.com/aws/en/admin/system-tables/compute)
- [Classic compute configuration best practices](https://docs.databricks.com/aws/en/compute/cluster-config-best-practices)
- [View compute metrics](https://docs.databricks.com/aws/en/compute/cluster-metrics)
- [Best practices for cost optimization](https://docs.databricks.com/aws/en/lakehouse-architecture/cost-optimization/best-practices)
