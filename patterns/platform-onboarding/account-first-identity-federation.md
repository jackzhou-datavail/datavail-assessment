# Account-First Identity Federation

**Category:** Platform Onboarding

Users, service principals, and groups are provisioned once at the
Databricks *account* level from the corporate identity provider, then
assigned to workspaces — rather than being created workspace by
workspace.

## Why it matters

Identity federation means "users, service principals, and groups" are
managed centrally at the account level and then granted access to
specific workspaces. The alternative — provisioning into each workspace
— multiplies by the number of workspaces: every new hire needs N
additions, every departure needs N removals, and the N copies drift
apart silently. Databricks' guidance is to "synchronize all of the users
and groups in your identity provider to the account console rather than
to individual workspaces, so you only need to configure one SCIM
provisioning application."

Getting this right in Phase 1 matters more than most onboarding
decisions because everything downstream inherits it: Unity Catalog
grants are written against groups, workspace assignment is written
against groups, and compute policy access is written against groups. If
the group layer doesn't exist yet, teams write grants against individual
users instead, and that becomes the permission graph you live with —
see [`../unity-catalog-governance/individual-user-grants.md`](../unity-catalog-governance/individual-user-grants.md).

## What good looks like

- **Automatic identity management** is the recommended provisioning
  mechanism for supported identity providers — it synchronizes users,
  service principals, groups, and nested groups directly. SCIM remains
  the fallback for providers it doesn't cover.
- SSO at the account level with MFA: OIDC for new deployments, SAML 2.0
  where an enterprise/legacy IdP requires it. Databricks' security
  guidance is to "use SSO with multifactor authentication to centralize
  authentication and reduce password risks."
- **Account admin roles go to 2–3 trusted individuals only.** The
  broader principle is "a limited number of account admins per account
  and workspace admins in each workspace" — admin rights are delegated
  down to workspace admins and feature-specific roles (metastore admin,
  marketplace admin) rather than concentrated or handed out broadly.
- The admin model matches the organization: centralized for small
  teams, federated for large ones, segregated-duties for regulated
  industries.
- Access is granted to groups, never to individuals: "assign access to
  workspaces and access-control policies in Unity Catalog to groups,
  instead of to users individually."
- Service principals — not human accounts — run automation. See
  [`service-principals-for-automation.md`](service-principals-for-automation.md).

## How to detect

System tables don't expose the account's identity configuration
directly, so this is checked through the account console / Account API
rather than SQL: whether a SCIM or automatic-identity-management
connection exists, how many principals hold the account admin role, and
whether SSO is enforced. The indirect signal that shows up in data is
ownership: `system.lakeflow.jobs` / `pipelines` `run_as` and
`system.information_schema.tables.table_owner` values that are
individual user emails rather than group or service-principal
identities. `data_collection/collect_data.py` already reads those fields
for its `has_owner_tag` signal, though it treats any non-null owner as
positive and does not distinguish a person from a group.

## References

- [Phase 1: Design account and identity strategy](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/account-setup)
- [Identity best practices](https://docs.databricks.com/aws/en/admin/users-groups/best-practices)
- [Best practices for security, compliance, and privacy](https://docs.databricks.com/aws/en/lakehouse-architecture/security-compliance-and-privacy/best-practices)
