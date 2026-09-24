# Environment-Based Workspace Strategy

**Category:** Platform Onboarding

Workspaces are split along SDLC environments (at minimum Dev and Prod)
and hard isolation boundaries — regulation, region, business unit —
while *everything else* is isolated with Unity Catalog catalogs and
schemas inside those workspaces.

## Why it matters

The workspace is the unit of platform configuration and network
topology, not the unit of team organization. Databricks' explicit
guidance is to "split SDLC environments into separate workspaces (at
least Dev and Prod, but possibly more depending on requirements)" and,
just as explicitly, "do not create separate workspaces for individual
teams or small projects (use Unity Catalog catalogs and schemas for
isolation instead)."

The cost of getting this wrong runs in both directions. Too few
workspaces and a developer's experiment shares configuration and
compute policy with production. Too many and you inherit administrative
overhead that scales linearly with workspace count — plus a real
functional loss: "there is no notebook sharing (collaboration) across
workspaces." See [`workspace-sprawl.md`](workspace-sprawl.md) for the
failure mode on that side.

## What good looks like

- A small team (say up to five data engineers) starts with **two**
  workspaces — development and production — in a single cloud account,
  and adds staging when the release process needs it.
- Separation is driven by a real boundary: strict SDLC isolation
  (separate VNets per environment), data residency across regions,
  regulated business units, differing platform-feature access, or cloud
  account resource limits — not by org chart.
- Within a workspace, isolation is Unity Catalog's job: a catalog per
  environment inside one metastore, production catalogs bound in
  `ISOLATED` mode so they can't be read from the wrong workspace.
- Developers get personal schemas (`dev_${user_name}`) so nobody
  overwrites a shared dev table.
- **Start with serverless workspaces**; switch to classic only when a
  specific network or compliance requirement demands it.
- One administrative workspace per region manages Unity Catalog
  resources.
- The split strategy and naming conventions are documented, and
  workspaces are created by IaC — see
  [`infrastructure-as-code-terraform-and-bundles.md`](infrastructure-as-code-terraform-and-bundles.md).

## How to detect

Workspace inventory comes from the Account API / account console, not
system tables — count workspaces, check names against the convention,
and compare the count to the number of genuine isolation boundaries the
organization actually has. Inside a workspace,
`system.information_schema.catalogs` and `.schemas` show whether
environment separation is expressed as catalogs (good) or as
same-catalog naming prefixes (weaker). Cross-check against
`system.access.workspaces_latest` for the account-level list.

## References

- [Phase 2: Design workspace strategy](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/workspace-strategy)
- [Developer best practices on Databricks](https://docs.databricks.com/aws/en/developers/best-practices)
- [Best practices for operational excellence](https://docs.databricks.com/aws/en/lakehouse-architecture/operational-excellence/best-practices)
