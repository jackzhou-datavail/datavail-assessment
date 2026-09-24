# Workspace Sprawl

> ⚠️ **ANTI-PATTERN**

**Category:** Platform Onboarding

A new workspace is created for each team, project, or proof of concept,
so the account accumulates dozens or hundreds of workspaces that no one
owns, that drift apart in configuration, and that cannot share work.

## Why it happens

Creating a workspace is easy, feels safe, and solves the immediate
problem: a team wants isolation from another team's mess, and a fresh
workspace gives them that in minutes. Nothing pushes back at creation
time, and each individual decision looks reasonable. The cost only
appears in aggregate, months later, when someone tries to answer "how
many workspaces do we have, and who owns them?"

It is also what happens when Unity Catalog isn't yet the isolation
mechanism. Before catalogs and schemas are the answer to "keep our data
separate," the workspace is the only boundary anyone knows about.

## Impact

- Databricks' explicit limit: **"do not deploy more than 50–100
  workspaces without strong justification and robust automation."**
  Beyond that you "risk orphaned, unmanaged deployments."
- Collaboration breaks in a way people don't expect: **"there is no
  notebook sharing (collaboration) across workspaces."** Two teams in
  two workspaces cannot open each other's notebooks.
- Configuration drift — each workspace has its own admin settings,
  compute policies, and feature flags, so "it works in ours" becomes a
  routine support answer.
- Network and security infrastructure per workspace gets expensive at
  scale; private connectivity is not free per deployment.
- Cloud account limits bite: on AWS, Premium tier defaults to 10
  workspaces (hard limit 50) and Enterprise to 50 (hard limits 1,000
  classic / 2,000 serverless, raised in batches of 50).
- Some platform features have limited cross-workspace support, so the
  split quietly constrains what the organization can adopt later.

## How to fix

1. Stop creating workspaces per team. Databricks is direct: "do not
   create separate workspaces for individual teams or small projects
   (use Unity Catalog catalogs and schemas for isolation instead)."
2. Re-derive the split from real boundaries — SDLC environment, data
   residency region, regulated business unit, differing platform-feature
   access, cloud resource limits. See
   [`environment-based-workspace-strategy.md`](environment-based-workspace-strategy.md).
3. Consolidate workspaces that exist for no boundary reason, migrating
   their jobs and data into catalogs within a shared environment
   workspace.
4. Put workspace creation behind IaC and a naming convention, so the
   next one requires a reviewed pull request rather than a UI click —
   "avoid ad-hoc workspace creation without following naming
   conventions."
5. Where consolidation isn't feasible, automate: multiple workspaces
   "demand fully automated setup and maintenance," not manual care.

## How to detect

Workspace inventory comes from the Account API or account console —
count them, then compare against the number of genuine isolation
boundaries. `system.access.workspaces_latest` gives the account-level
list in SQL. The sharper signal is abandonment: join workspace ids in
`system.billing.usage` over the last 90 days against that list, and any
workspace with near-zero recent usage is an orphan candidate. Names
that don't match the convention are the other reliable tell.

## References

- [Phase 2: Design workspace strategy](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/workspace-strategy)
- [Best practices for operational excellence](https://docs.databricks.com/aws/en/lakehouse-architecture/operational-excellence/best-practices)
