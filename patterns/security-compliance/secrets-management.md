# Secrets Managed in Secret Scopes or Unity Catalog

**Category:** Security & Compliance

Every credential a workload needs — database passwords, API keys, service
tokens — is stored in a Databricks secret scope or as a Unity Catalog
secret and read at runtime, never written into notebooks, job parameters,
Spark configuration, or files in the repo.

## Why it matters

A credential pasted into a notebook is visible to everyone who can read
that notebook, is copied into every Git commit and export of it, and
survives long after the person who pasted it has left. Rotating it means
finding every copy. Secret management inverts that: the value lives in
one encrypted store, code holds only a reference, and access to the value
is itself a governed permission.

Databricks secret scopes are "stored in an encrypted database owned and
managed by Databricks," and values read through `dbutils.secrets.get()`
are masked in output — "when displayed, the secret values are replaced
with `[REDACTED]`." Redaction is a safety net, not a boundary: it
"applies only to literal secret values" and "does not prevent deliberate
and arbitrary transformations," so anyone who can `READ` a scope can
still exfiltrate what's in it. The permission model is the real control.

## What good looks like

- **Scopes aligned to applications or roles, not people.** Databricks
  recommends organizing scopes by role or application; a scope per
  individual reproduces the personal-identity problem in a new place.
- **Least-privilege ACLs.** Scope permissions are `READ`, `WRITE`, and
  `MANAGE`; the creator gets `MANAGE` by default. Production scopes grant
  `READ` to the service principal that runs the job and `MANAGE` to a
  small admin group — not to all users.
- **Unity Catalog secrets for cross-workspace or governed use.** UC
  secrets are securables in the three-level namespace
  (`catalog.schema.secret`), shared across workspaces on the metastore,
  and governed with `CREATE SECRET`, `READ SECRET`, `WRITE SECRET`, and
  `REFERENCE SECRET` — the last lets code reference a secret "without
  exposing the value in code."
- **External vault backing** (AWS Secrets Manager, Azure Key Vault) where
  the organization already runs one, so rotation happens in one place.
- **Rotation is scheduled and automated**, and credentials are replaced
  by federated identity (OAuth, service-principal tokens, UC storage
  credentials and connections) wherever the target system supports it —
  the best secret is one that doesn't exist.

## How to detect

Secret *configuration* is not in system tables; list scopes and their
ACLs through the Secrets API (`databricks secrets list-scopes`,
`list-acls`) and flag scopes where `users` or large groups hold `READ` or
`MANAGE`. Usage is visible in `system.access.audit` with
`service_name = 'secrets'` and `action_name` in `getSecret`, `putSecret`,
`deleteSecret`, `createSecretScope`, `deleteSecretScope` — a scope read by
many distinct human identities is a sign it is being used interactively
rather than by automation. The absence of secrets is the harder finding:
it needs a repository / workspace-file scan for credential-shaped strings
(the same scan named in
[`personal-identity-in-production.md`](../platform-onboarding/personal-identity-in-production.md)).

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **Security and Identity › Secrets** — *primary.* Are credentials held in secret scopes or UC secrets with least-privilege ACLs, and is code free of hard-coded credentials?

## References

- [Secret management](https://docs.databricks.com/aws/en/security/secrets/)
- [Secrets in Unity Catalog](https://docs.databricks.com/aws/en/security/secrets/unity-catalog-secrets)
- [Audit log reference](https://docs.databricks.com/aws/en/admin/account-settings/audit-logs)
