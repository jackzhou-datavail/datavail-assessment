# Compute Policies and Standard Sizing

**Category:** Platform Onboarding

Every compute resource users can create is governed by a compute
policy that fixes autoscaling bounds, auto-termination, allowed
instance types, and cost ceilings — with a small set of standard
"T-shirt" sizes rather than a free-form configuration form.

## Why it matters

Databricks states it plainly: **"cluster policies are recommended for
all organizations,"** and the corresponding anti-pattern is **"do not
manually create clusters without cluster policies in production."**
Policies let admins "limit a user or group's compute creation
permissions based on a set of policy rules" — capping per-cluster cost
by restricting attributes, limiting how many clusters a user can
create, and enforcing cluster-scoped library installations.

The second, less obvious benefit is onboarding speed. A policy
"simplifies the user interface" by hiding options users shouldn't have
to reason about, which means a new analyst can create working compute
on day one without first learning instance families. Without policies,
the choice is between giving everyone the unrestricted policy (and the
bill that follows) and gatekeeping every cluster request through an
admin.

## What good looks like

- Cluster creation rights are granted through policies, not through
  the unrestricted policy. Policy families provide the starting
  templates for common cases.
- Policies enforce the cost controls that would otherwise rely on
  memory: **autoscaling bounds, auto-termination on idle, and a
  restricted set of instance types**. Databricks lists all three as
  cost-optimization practices delivered *via* policies.
- Standard sizes are defined once and reused — a small/medium/large
  (T-shirt) set, roughly: small (2–8 nodes) for development and
  testing, medium (8–32) for production ETL and analytics, large (32+)
  for batch processing and ML training.
- Policies are defined in IaC alongside the rest of the workspace, so
  every environment gets the same ones.
- GPU instance types are available only under a policy scoped to
  workloads that actually use GPU-accelerated libraries.
- Runtimes are kept current — newer DBRs "often result in cost savings
  due to more efficient use of compute resources," and the policy is
  where a minimum version gets enforced.

## How to detect

`system.compute.clusters` records each classic cluster along with its
`policy_id`; clusters with a null or unrestricted policy id are the
finding. Pair that with `min_autoscale_workers`/`max_autoscale_workers`
and `auto_termination_minutes` to catch policy-covered clusters whose
policy doesn't actually constrain anything. `system.billing.usage`
joined to cluster ids ranks the ungoverned clusters by what they cost,
which is usually the version of this finding that gets acted on.

## References

- [Create and manage compute policies](https://docs.databricks.com/aws/en/admin/clusters/policies)
- [Phase 8: Design compute strategy](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/compute)
- [Best practices for cost optimization](https://docs.databricks.com/aws/en/lakehouse-architecture/cost-optimization/best-practices)
