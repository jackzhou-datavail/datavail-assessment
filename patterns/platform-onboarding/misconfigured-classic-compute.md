# Misconfigured Classic Compute

> ⚠️ **ANTI-PATTERN**

**Category:** Platform Onboarding

Classic clusters run with auto-termination disabled or set very high,
on out-of-support runtimes, with fixed sizes, all on-demand instances,
and hand-tuned Spark configuration — each setting individually
defensible when it was chosen, collectively expensive and fragile.

## Why it happens

Cluster configuration is copied. The first working cluster becomes the
template, including the `spark.sql.shuffle.partitions` someone tuned
for a problem that no longer exists and the auto-termination someone
disabled because a long training run kept being killed. Runtime
versions are pinned because upgrading is a risk nobody is rewarded for
taking, and spot instances are avoided after one bad preemption. With
no compute policy constraining the form
([`compute-policies-and-standard-sizing.md`](compute-policies-and-standard-sizing.md)),
nothing pushes back.

## Impact

- **Idle spend.** A cluster with no auto-termination bills from the
  moment it's forgotten until someone notices.
- **Missing platform improvements.** Databricks recommends "the latest
  long-term support (LTS) Databricks Runtime version"; old runtimes miss
  performance work, security fixes, and features (Unity Catalog modes,
  Photon improvements) — and eventually leave support.
- **Overridden optimizations.** Hardcoded Spark settings "override the
  built-in optimizations that Databricks provides," so adaptive query
  execution and auto-tuning can't do their job.
- **Portability debt.** Init scripts, DBFS mounts, compute-scoped
  libraries, and local storage paths — all discouraged — make the
  cluster impossible to move to serverless or standard access mode.
- **Paying on-demand rates** for fault-tolerant batch work that could
  use spot capacity.

## How to fix

1. Enforce auto-termination and autoscaling through compute policies;
   make fixed-size clusters an exception with a reason.
2. Set a minimum runtime in policy and upgrade to the current LTS on a
   cadence; treat end-of-support runtimes as findings.
3. Remove hardcoded Spark configs and re-test; add back only what a
   benchmark justifies.
4. Use spot (with on-demand driver) for workloads "that have lax latency
   requirements"; use instance pools where start time matters.
5. Move to standard access mode and UC volumes/libraries instead of
   init scripts and mounts — then evaluate whether the workload belongs
   on serverless at all.

## How to detect

`system.compute.clusters` (latest row per `cluster_id`, `deleted_time`
null): `auto_termination_minutes` null/0 or very high on
`cluster_source` = UI/API interactive clusters; `dbr_version` older than
the current LTS or out of support; `min_autoscale_workers` null with a
fixed `num_workers`; `aws_attributes` / `azure_attributes` availability
fully on-demand; non-empty `init_scripts`; `data_security_mode` still on
legacy/no-isolation modes. Join `system.billing.usage` to rank by cost
and `system.compute.node_timeline` to find idle-but-running time.

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **FinOps › Compute configuration (Classic)** — *primary.* Do classic clusters have auto-termination, autoscaling, a current LTS runtime, spot where appropriate, and no hard-coded Spark config or legacy access modes?
- **Governance and Unity Catalog › Policies for compute** — *supporting;* primary pattern is [`compute-policies-and-standard-sizing.md`](compute-policies-and-standard-sizing.md).

## References

- [Classic compute configuration best practices](https://docs.databricks.com/aws/en/compute/cluster-config-best-practices)
- [Compute system tables reference](https://docs.databricks.com/aws/en/admin/system-tables/compute)
- [Phase 8: Design compute configuration](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/compute)
