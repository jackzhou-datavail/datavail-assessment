# Group-Based Permissions on Workspace Resources

**Category:** Platform Onboarding

Jobs, compute, SQL warehouses, pipelines, dashboards, serving endpoints,
and notebook folders carry access-control lists granted to groups and
service principals, at the lowest level that does the job — rather than
relying on the creator-gets-everything defaults that every workspace
starts with.

## Why it matters

Unity Catalog governs *data*; it does not govern who can edit a
production job, restart a shared cluster, or change a serving endpoint.
Those are workspace object ACLs, and their defaults are generous:
"users automatically have the CAN MANAGE permission for objects that
they create," job creators become `IS OWNER`, and objects in a folder
inherit the folder's permissions. Left alone, the permission model of a
workspace is simply "whoever built it," which breaks the moment that
person moves on and makes it impossible to answer who can change what
in production.

The levels are fine-grained enough to do this properly:

- **Jobs:** `CAN VIEW`, `CAN MANAGE RUN`, `IS OWNER`, `CAN MANAGE`
- **Compute:** `CAN ATTACH TO`, `CAN RESTART`, `CAN MANAGE`
- **SQL warehouses:** `CAN VIEW`, `CAN MONITOR`, `CAN USE`, `IS OWNER`, `CAN MANAGE`
- **Notebooks / folders:** `CAN VIEW`, `CAN RUN`, `CAN EDIT`, `CAN MANAGE`
- **Pipelines:** `CAN VIEW`, `CAN RUN`, `CAN MANAGE`, `IS OWNER`
- **Serving endpoints:** `CAN VIEW`, `CAN QUERY`, `CAN MANAGE`
- **Dashboards:** view/read, `CAN RUN`, `CAN EDIT`, `CAN MANAGE`

## What good looks like

- Permissions granted to IdP-synced **groups** (see
  [`account-first-identity-federation.md`](account-first-identity-federation.md)),
  never to individual users, and set by IaC / bundles alongside the
  resource so they can't drift.
- Production jobs and pipelines owned by, and running as, a **service
  principal** ([`service-principals-for-automation.md`](service-principals-for-automation.md));
  on-call groups hold `CAN MANAGE RUN`, developers `CAN VIEW`.
- Warehouses: consumers get `CAN USE`, platform team `CAN MANAGE`;
  `CAN MONITOR` for those who need query visibility without control.
- Shared compute: `CAN ATTACH TO` for users, `CAN MANAGE` for admins —
  and no legacy no-isolation shared clusters, where attach rights expose
  credentials.
- Production code lives in team-owned folders, not `/Workspace/Shared`,
  so folder inheritance enforces least privilege.
- Workspace admins kept to a small group — admins have `CAN MANAGE` on
  everything.

## How to detect

ACLs aren't in system tables; read them with the Permissions API
(`databricks permissions get jobs <id>`, `clusters`, `warehouses`,
`pipelines`, `serving-endpoints`, `directories`). Enumerate production
jobs and pipelines from `system.lakeflow.jobs` / `pipelines`, then flag:
ACL entries for individual `user_name` rather than `group_name` /
`service_principal_name`; `IS OWNER` held by a human on scheduled
production jobs; `CAN MANAGE` granted to `users`; and warehouses where
all users hold `CAN MANAGE`. Permission changes appear in
`system.access.audit` for change history. The Security Analysis Tool
covers part of this across workspaces
([`../security-compliance/security-analysis-tool-baseline.md`](../security-compliance/security-analysis-tool-baseline.md)).

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **Governance and Unity Catalog › Identity/group management on resources** — *primary.* Are permissions on data (UC grants) and on workspace resources (jobs, compute, warehouses, pipelines, endpoints, folders) given to IdP-synced groups and service principals rather than individual users?

## References

- [Access control lists](https://docs.databricks.com/aws/en/security/auth/access-control/)
- [Manage identities, permissions, and privileges for Lakeflow Jobs](https://docs.databricks.com/aws/en/jobs/privileges)
- [permissions command group](https://docs.databricks.com/aws/en/dev-tools/cli/reference/permissions-commands)
