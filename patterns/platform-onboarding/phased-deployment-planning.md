# Phased Deployment Planning Before Provisioning

**Category:** Platform Onboarding

Account, workspace, Unity Catalog, network, storage, IaC, compute,
observability, and DR decisions are made — and written down — as an
explicit sequence before the first production workspace is created,
rather than being discovered one incident at a time.

## Why it matters

Databricks publishes its onboarding path as ten ordered phases
(Account → Workspace strategy → Unity Catalog → Network → Storage →
Delta Lake → Infrastructure as Code → Compute → Observability → HA/DR)
precisely because the early decisions constrain the later ones. Identity
federation is an account-level decision that every workspace inherits;
the metastore is regional and effectively permanent; network topology
determines whether serverless is even available to you. A team that
starts by clicking "Create workspace" has already made several of these
choices implicitly, and the ones that turn out wrong are the expensive
kind to reverse — reversing them means rebuilding workspaces, migrating
catalogs, or re-platforming pipelines that are already carrying
production load.

The phases are also the natural unit of *documentation*. Each phase in
the Databricks guide ends with a deliverables checklist ("admin role
strategy designed", "identity federation strategy defined", "workspace
split strategy and naming conventions documented"). That checklist is
what a new platform engineer reads in month six to understand why the
environment looks the way it does.

## What good looks like

- Each phase produces a written artifact — a decision record naming the
  choice, the alternatives considered, and the constraint that drove it
  — stored in version control alongside the IaC that implements it.
- Phase 1 (account/identity) and Phase 3 (Unity Catalog) are settled
  before any workspace carries real data, since both are account-scoped
  and hard to retrofit. See
  [`account-first-identity-federation.md`](account-first-identity-federation.md).
- Naming conventions for workspaces, catalogs, schemas, groups, and
  compute policies are defined once, in Phase 2, and then enforced by
  IaC rather than by review comments.
- The phases are revisited on a cadence, not treated as a one-time
  onboarding ritual — workspace count, compute policy coverage, and
  cost attribution all drift as the platform grows.
- An administrative workspace per region is created for managing Unity
  Catalog resources, separate from the workspaces that run workloads.

## How to detect

This is a documentation and process signal rather than a system-table
one — no query tells you whether decisions were recorded. The
observable *proxy* for "no plan was written" is the set of symptoms the
other patterns in this category detect: workspaces that don't follow a
naming convention, compute created outside any policy, resources that
exist in the workspace but not in any repo. If an assessment finds
several of those at once, the underlying finding is usually that Phase 1
and Phase 2 were skipped.

## References

- [Databricks production planning](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/)
- [Phase 2: Design workspace strategy](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/workspace-strategy)
- [Best practices for operational excellence](https://docs.databricks.com/aws/en/lakehouse-architecture/operational-excellence/best-practices)
