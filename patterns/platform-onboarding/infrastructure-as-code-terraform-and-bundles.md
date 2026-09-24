# Infrastructure as Code: Terraform for Platform, Bundles for Workloads

**Category:** Platform Onboarding

Account- and workspace-level infrastructure is managed with Terraform;
data and AI workloads are managed with Declarative Automation Bundles
(formerly Databricks Asset Bundles). Neither is created by hand in the
UI in production.

## Why it matters

Databricks draws the line between the two tools explicitly:

- *"Use Terraform for infrastructure resources (for example, workspaces,
  networks, Unity Catalog, storage)"*
- *"Use Declarative Automation Bundles for data and AI workloads (for
  example, jobs, pipelines, notebooks, models)"*

The reason to split them is lifecycle. Workspaces and networks change
rarely, are owned by a platform team, and need state management and
plan review. Jobs and pipelines change every sprint, are owned by the
teams that write them, and need to ride the same PR as the code they
run. Forcing workload deployment through Terraform makes every pipeline
change a platform-team ticket; forcing network configuration through
bundles puts cloud infrastructure in a data engineer's YAML.

The companion anti-patterns are equally explicit: *"do not manually
create workspaces in production (use IaC for repeatability)"* and
*"do not store Terraform state locally (use remote backends)."*

## What good looks like

- Remote Terraform state with locking enabled; reusable modules rather
  than copy-pasted workspace definitions.
- One administrative workspace per region, created by Terraform, for
  managing Unity Catalog resources.
- **Small, focused bundles** — one per team, covering all of that
  team's environments (dev/staging/prod) under a single lifecycle, so a
  rollback is targeted rather than account-wide.
- Bundles deploy to team-owned workspace locations, not
  `/Workspace/Shared`, so least-privilege access is enforced by where
  the code lands.
- Shared libraries are pulled into multiple bundles via `sync.paths`
  rather than duplicated.
- Custom bundle templates encode governance, permissions, and
  infrastructure defaults, so a new project starts compliant instead of
  being reviewed into compliance later.
- Inter-bundle dependencies are wired explicitly in CI/CD — upstream
  deploys finish before downstream tasks start.
- `databricks bundle validate` runs in CI as one of three testing
  layers, alongside unit tests (pytest) and staging integration tests.

## How to detect

There is no system table for "was this resource created by IaC," so the
practical check is a reconciliation: list jobs and pipelines from
`system.lakeflow.jobs` / `system.lakeflow.pipelines` and compare against
what the repos actually declare. Two signals narrow it down without a
full diff — jobs whose `creator_id` is an individual user rather than a
deployment service principal, and job/pipeline names that don't carry
the `[<target>] <bundle>` prefix that bundle deployment applies.
`data_collection/collect_data.py` already loads both tables with their
creator/owner fields, so the raw material for this check is present.

## References

- [Phase 7: Design IaC strategy](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/iac)
- [Declarative Automation Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/)
- [Developer best practices on Databricks](https://docs.databricks.com/aws/en/developers/best-practices)
