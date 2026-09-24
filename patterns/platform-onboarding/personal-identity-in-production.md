# Personal Identities and Hardcoded Credentials in Production

> ⚠️ **ANTI-PATTERN**

**Category:** Platform Onboarding

Production jobs and pipelines run as a named individual's account, and
the credentials they need — API keys, database passwords, tokens — are
pasted into notebook cells or job parameters instead of stored in
secret scopes.

## Why it happens

Whoever builds a pipeline is its creator, and `run_as` defaults to
them. Nothing fails, so nothing prompts a change. Creating a service
principal, granting it the right Unity Catalog privileges, and wiring
up OAuth is real work with no visible payoff on the day it's done —
the payoff arrives months later, when that person leaves.

Hardcoded credentials have the same shape. A connection string typed
into a cell works immediately; a secret scope requires setup and a
mental model of who can read it. And once one credential is in a
notebook, the notebook is in Git, and the credential is in Git history.

## Impact

- **Offboarding breaks production.** When the person's account is
  disabled, every pipeline running as them fails, usually without a
  clear error pointing at the cause.
- Over-broad permissions: production write and delete rights end up
  attached to an interactive human account, which is exactly what
  running as a service principal is meant to prevent — Databricks'
  stated reason is keeping interactive users from accidentally
  overwriting production data.
- Audit logs become unreadable: `system.access.audit` shows a person's
  identity for actions a scheduled system performed, so you cannot
  distinguish automation from human activity.
- Credentials in notebooks are visible to anyone who can read the
  notebook, survive in Git history after removal, and cannot be rotated
  centrally. Databricks warns explicitly against entering "sensitive
  information such as credentials, API keys, and tokens" into notebooks
  or "storing them in plain text."
- Long-lived personal access tokens used for automation are both hard
  to rotate and hard to attribute.

## How to fix

1. Create a service principal per workload, grant it exactly the Unity
   Catalog privileges that workload needs, and set `run_as` to it.
   Keep deployment and runtime principals separate. See
   [`service-principals-for-automation.md`](service-principals-for-automation.md).
2. Authenticate with OAuth (M2M), not personal access tokens; use OIDC
   federation where no stored secret is acceptable.
3. Move every credential into a Databricks secret scope and reference
   it from notebooks and jobs. Scope secret scopes by functional role or
   application, not per user — and remember that "workspace admins,
   secret creators, and users who have been granted permission can
   access and read Databricks secrets," so scope membership is itself a
   privilege to manage.
4. Rotate anything that was ever hardcoded; removing it from the
   notebook does not remove it from Git history.
5. Enforce token management at the workspace level (maximum lifetimes,
   restricted creation) so the old path closes behind you.

## How to detect

`system.lakeflow.jobs.run_as` and `system.lakeflow.pipelines.run_as`
show an email address for a human-owned workload and an application id
for a service-principal-owned one — counting production workloads in
the first category is the primary check.
`data_collection/collect_data.py` reads both tables and derives
`has_owner_tag`, but scores any non-null owner as good; separating
"human" from "service principal" is the sharper metric for production.
Hardcoded credentials are not visible in system tables at all — that
check is a secret-scanning pass over the repo and over notebook
sources exported via the Workspace API.

## References

- [Identity best practices](https://docs.databricks.com/aws/en/admin/users-groups/best-practices)
- [Secret management](https://docs.databricks.com/aws/en/security/secrets/)
- [Best practices for security, compliance, and privacy](https://docs.databricks.com/aws/en/lakehouse-architecture/security-compliance-and-privacy/best-practices)
