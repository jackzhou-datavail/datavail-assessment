# Disaster Recovery Strategy with Tested RPO/RTO

**Category:** Platform Onboarding

Each workload has an agreed recovery point and recovery time objective,
a DR pattern chosen to meet it, and a recovery procedure that has
actually been exercised — covering data, metadata, code, configuration,
and identity, not only the data files.

## Why it matters

"The cloud provider replicates storage" is the most common DR answer
and the least complete one. Recovering a Databricks platform in another
region needs the tables *and* the Unity Catalog metadata and grants, the
jobs and pipelines, the workspace configuration, the compute policies,
the secrets, and the identities that run it all. A plan that restores
only the data leaves a region full of files that nothing can query.

Databricks' deployment guidance frames objectives by criticality:
critical workloads at "RTO < 1 hour, RPO < 15 minutes (active-active or
active-passive with continuous replication)," standard workloads at
"RTO < 24 hours, RPO < 24 hours (backup and restore)." Most accounts
need both tiers; paying for active-active everywhere is as much a
finding as having nothing.

## What good looks like

- RPO/RTO documented per workload tier and agreed with the business.
- A pattern per tier: **backup and restore** for standard, **active-
  passive** with periodic replication for important, **active-active**
  only where the cost is justified.
- Every layer covered:
  - **Data** — Delta tables replicated with Deep Clone (incremental on
    rerun) or managed replication; raw sources geo-redundant.
  - **Metadata & grants** — Unity Catalog objects and ACLs defined in
    Terraform so they can be recreated.
  - **Code & jobs** — in Git and deployed by CI/CD / bundles to both
    regions ([`infrastructure-as-code-terraform-and-bundles.md`](infrastructure-as-code-terraform-and-bundles.md)).
  - **Identity** — SCIM at account level so users and groups exist in
    both regions.
- Where available, **managed disaster recovery** (account-team gated):
  Databricks "manages the replication pipeline, the state of the
  replicated catalogs in the secondary, and the failover process." Note
  its exclusions — materialized views, streaming tables, ML models,
  published dashboards, and shares aren't replicated.
- DR tested: runbook reviews monthly, full failover exercises
  periodically, and actual RTO/RPO measured during tests.

## How to detect

Mostly a design conversation, with some evidence available: jobs whose
names or code perform `DEEP CLONE` into a secondary catalog/region
(`system.lakeflow.jobs`, `system.query.history` `statement_text`), a
second-region workspace in the Account API, and IaC coverage of UC
objects. Where managed DR is enabled, `system.replication.states`
records replication status and historical RPO. The finding is a
production workload tier with no stated RPO/RTO, or objectives stated
but never tested.

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **Platform management › Disaster recovery** — *primary.* Are RPO/RTO defined per workload tier, is there a DR pattern covering data, metadata, code and identity, and has it been tested?

## References

- [Phase 10: Design high availability and disaster recovery](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/ha-dr)
- [Disaster recovery](https://docs.databricks.com/aws/en/admin/disaster-recovery)
- [Managed disaster recovery](https://docs.databricks.com/aws/en/admin/managed-disaster-recovery)
- [Best practices for reliability](https://docs.databricks.com/aws/en/lakehouse-architecture/reliability/best-practices)
