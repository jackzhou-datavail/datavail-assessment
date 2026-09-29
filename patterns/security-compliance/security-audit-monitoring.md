# Security Audit Log Monitoring and Alerting

**Category:** Security & Compliance

Security-relevant audit events — logins, token creation, admin grants,
IP access list and workspace setting changes, secret access — are
queried from `system.access.audit` on a schedule and alerted on, rather
than only being retained for an investigation that may never be
triggered.

## Why it matters

Audit logging is on by default for the system table; what's usually
missing is anyone *reading* it. A log nobody queries detects nothing: a
new personal access token issued to a departed contractor, a user
quietly added to the admins group, or an IP access list removed on a
Friday evening all land in `system.access.audit` and sit there.

This pattern is the security counterpart to
[`lineage-and-audit-via-system-tables.md`](../unity-catalog-governance/lineage-and-audit-via-system-tables.md),
which covers audit for data access and lineage. Here the focus is the
platform's control surface — identity, credentials, and configuration.

## What good looks like

- **A small, named set of alerting queries** over `system.access.audit`,
  scheduled as Databricks SQL alerts and routed to the security team:
  - Authentication: `service_name = 'accounts'`, `action_name` in
    `login`, `loginMfa`, `deniedIpLogin`, with failure responses grouped
    by `user_identity` and `source_ip_address`.
  - Credentials: `generateDbToken`, `updateDbToken` — new personal
    access tokens, especially for admins or long lifetimes.
  - Privilege changes: `addPrincipalToGroup`, `removePrincipalFromGroup`,
    `grantAdminPermission`, `revokeAdminPermission`.
  - Perimeter: `createIpAccessList`, `updateIpAccessList`,
    `deleteIpAccessList`; `workspace` service `workspaceConfEdit` and
    `updateWorkspaceSetting`.
  - Secrets: `service_name = 'secrets'` reads from unexpected identities.
  - Account: `accountsManager` workspace and storage configuration changes.
- **Retention decided deliberately.** System table retention is
  bounded, so anything needed beyond it for compliance is copied to a
  long-retention table or delivered via audit log delivery to the
  organization's own storage / SIEM.
- **SIEM integration** where the organization has one, with Databricks
  as a source — not a separate console nobody watches.
- Where the compliance security profile is on, enhanced security
  monitoring logs are included — see
  [`compliance-security-profile.md`](compliance-security-profile.md).

## How to detect

`system.access.audit` itself is the data; the check is whether it is
*used*. Look in `system.query.history` for scheduled statements whose
`statement_text` references `system.access.audit` (and in
`system.alert` / the Alerts API for alert definitions over it). No
scheduled query and no alert on the audit table is the finding. Account
audit-log delivery configuration is checked through the Account API
(log delivery configurations).

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **Security and Identity › Audit logging** — *primary.* Is `system.access.audit` enabled, retained long enough, and actively queried / alerted on for security events and data access?

## References

- [Audit log system table reference](https://docs.databricks.com/aws/en/admin/system-tables/audit-logs)
- [Audit log reference (service and action names)](https://docs.databricks.com/aws/en/admin/account-settings/audit-logs)
- [Configure audit log delivery](https://docs.databricks.com/aws/en/admin/account-settings/audit-log-delivery)
