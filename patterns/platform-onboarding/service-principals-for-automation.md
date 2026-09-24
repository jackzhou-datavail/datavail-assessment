# Service Principals for Automation

**Category:** Platform Onboarding

Production jobs, pipelines, deployments, and administrative automation
run as service principals authenticated with OAuth — not as a named
person's account and not with long-lived personal access tokens.

## Why it matters

Databricks recommends "creating service principals to run production
jobs or modify production data," and the security pillar repeats it:
"use service principals to run administrative tasks and production
workloads." The stated reason is blast radius — if production write and
delete permissions belong to a service principal rather than to
interactive users, an analyst cannot accidentally overwrite a
production table from a notebook.

The second reason is continuity. A pipeline whose `run_as` is a person
breaks when that person changes teams or leaves, and the failure is
usually discovered by the on-call engineer at the worst possible time.
The third is auditability: a service principal named for its workload
makes `system.access.audit` readable, where a shared human account does
not.

Databricks also recommends **separate deployment and runtime
principals** — the identity that deploys a bundle is not the identity
that runs its jobs, so a compromised CI credential cannot also read
production data.

## What good looks like

- OAuth (M2M) authentication for service principals rather than
  personal access tokens; OIDC federation where regulated industries
  require no stored secret at all.
- One service principal per workload or team boundary, named for its
  purpose, with Unity Catalog grants scoped to exactly what that
  workload touches.
- Distinct deployment and runtime principals, as above.
- Service principals created at the account level and assigned to
  workspaces, like any other identity — see
  [`account-first-identity-federation.md`](account-first-identity-federation.md).
- Credentials never appear in code: they live in Databricks secret
  scopes and are referenced from notebooks and jobs. Storing
  "credentials, API keys, and tokens" in plain text in a notebook is
  explicitly warned against.
- Token management is enforced at the workspace level (maximum
  lifetimes, restricted token creation).

## How to detect

`system.lakeflow.jobs.run_as` and `system.lakeflow.pipelines.run_as`
tell you directly whether each production workload runs under a person
or a service principal — a service principal appears as a UUID-style
application id rather than an email address.
`data_collection/collect_data.py` reads both tables and derives
`has_owner_tag` from the owner/creator fields, but it treats any
non-null owner as good; splitting "owned by a human" from "owned by a
service principal" is a one-line change to that logic and is the more
actionable version of the metric for production workloads.
`system.access.audit` shows which identities actually performed
production writes.

## References

- [Identity best practices](https://docs.databricks.com/aws/en/admin/users-groups/best-practices)
- [Phase 1: Design account and identity strategy](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/account-setup)
- [Secret management](https://docs.databricks.com/aws/en/security/secrets/)
- [Developer best practices on Databricks](https://docs.databricks.com/aws/en/developers/best-practices)
