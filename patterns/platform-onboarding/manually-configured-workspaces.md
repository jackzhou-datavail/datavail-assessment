# Manually Configured "Snowflake" Workspaces

> ⚠️ **ANTI-PATTERN**

**Category:** Platform Onboarding

Workspaces, clusters, jobs, and grants are created by clicking through
the UI, so each environment is a unique artifact that cannot be
recreated, compared, or reviewed — and production differs from staging
in ways nobody can enumerate.

## Why it happens

The UI is how everyone learns Databricks, and it works. The first
workspace gets configured by hand because there's nothing to automate
yet; the second gets configured by hand because it's faster than
writing Terraform for a one-off; by the third, the manual approach is
the established process. IaC then looks like a migration project rather
than a starting point, and it keeps getting deferred.

Partial adoption is the more common version: infrastructure is in
Terraform, but someone fixes a production issue in the UI and never
backports it. Databricks names this directly as an anti-pattern —
"mixing automation with manual configuration" — because a half-managed
resource is worse than an unmanaged one, since the next `terraform
apply` may silently revert the fix or fail on drift.

## Impact

- Environments cannot be recreated. Disaster recovery, region
  expansion, and "spin up a clean test environment" all become
  multi-week efforts.
- No review, no history, no diff. A permission change or a Spark config
  change leaves no record of who made it or why.
- Drift between dev, staging, and production means testing in staging
  stops predicting production behavior — the specific failure mode CI/CD
  was meant to eliminate.
- Every workspace becomes a "snowflake workspace," which Databricks
  lists among the anti-patterns to avoid alongside "do not manually
  create workspaces in production (use IaC for repeatability)."
- Local Terraform state (the other named anti-pattern) turns a laptop
  into a single point of failure for the whole platform.

## How to fix

1. Split by lifecycle and adopt both tools: Terraform for workspaces,
   networks, storage, and Unity Catalog; Declarative Automation Bundles
   for jobs, pipelines, notebooks, and models. See
   [`infrastructure-as-code-terraform-and-bundles.md`](infrastructure-as-code-terraform-and-bundles.md).
2. Move Terraform state to a remote backend with locking before
   anything else — it's the cheapest fix with the largest blast-radius
   reduction.
3. Import existing resources rather than recreating them, starting with
   the highest-drift surface: compute policies, workspace admin
   settings, and Unity Catalog grants.
4. Close the UI path for production: restrict cluster creation to
   policies, restrict workspace creation to account admins, and make
   the bundle the only way jobs get deployed.
5. Build reusable modules and custom bundle templates so the automated
   path is genuinely faster than the manual one — otherwise people
   route around it.

## How to detect

The reconciliation check is the real one: compare `system.lakeflow.jobs`
and `system.lakeflow.pipelines` against what the repos declare, and
compare workspace inventory against Terraform state. Two cheap
system-table proxies: jobs whose `creator_id` is an individual user
rather than a deployment service principal, and job/pipeline names
lacking the `[<target>] <name>` prefix that bundle deployment applies.
`data_collection/collect_data.py` already loads those tables with
creator and `run_as` fields.

## References

- [Phase 7: Design IaC strategy](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/iac)
- [Best practices for operational excellence](https://docs.databricks.com/aws/en/lakehouse-architecture/operational-excellence/best-practices)
- [Phase 2: Design workspace strategy](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/workspace-strategy)
