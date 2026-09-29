# Customer-Managed Keys for Encryption

**Category:** Security & Compliance

Where the organization's policy or regulators require control over
encryption keys, the workspace is configured with customer-managed keys
(CMK) for both managed services and workspace storage — decided at
design time, not retrofitted after an audit finding.

## Why it matters

Databricks encrypts data at rest by default. Customer-managed keys add
the ability to own, rotate, and revoke the key in your own cloud KMS,
which is what many security policies and regulated-industry frameworks
actually ask for. The decision has two parts that are easy to conflate:

- **Managed services** — data held in the Databricks control plane:
  "notebook source in the Databricks control plane," secrets, SQL query
  history, and interactive notebook results, plus AI/BI dashboards, Git
  integration credentials, and search indexes.
- **Workspace storage** — the workspace storage bucket (DBFS root,
  FileStore, MLflow models) and, optionally, the EBS volumes of classic
  compute.

A workspace with CMK on storage but not managed services still has
notebook source and query text encrypted under a Databricks-held key,
which is often exactly the content a reviewer is worried about. For
serverless workspaces, Databricks notes "you only need to configure keys
for managed services."

The feature "requires the Enterprise tier" on AWS, and configuration is
at the account level, so it belongs in Phase 1 planning alongside
network design rather than as a later add-on.

## What good looks like

- A documented decision per workspace: CMK required or not, and why —
  driven by data classification, not applied everywhere by reflex.
- Where required, keys configured for **both** use cases (managed
  services and workspace storage), created and referenced through IaC so
  every environment matches.
- Key policies grant Databricks only the operations it needs, and key
  rotation follows the organization's KMS policy.
- Unity Catalog managed storage in the customer's own buckets encrypted
  with the organization's cloud-native key policy (SSE-KMS), so data in
  UC catalogs is covered, not only the workspace root.
- A tested runbook for key revocation — what stops working, and how to
  restore — because revoking a key is effectively turning the workspace
  off.

## How to detect

Not observable from system tables. Use the Account API: workspace
objects expose `managed_services_customer_managed_key_id` and
`storage_customer_managed_key_id` (AWS), and the encryption-keys
endpoint lists configured keys and their use cases. The finding is a
workspace handling data classified as confidential/regulated where
either field is empty. `system.access.audit` with
`service_name = 'accountsManager'` records workspace and storage
configuration changes for change history. The
[Security Analysis Tool](security-analysis-tool-baseline.md) includes
encryption checks and is the easiest way to run this across many
workspaces.

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **Security and Identity › CMEK** — *primary.* Where policy requires it, are customer-managed keys configured for both managed services and workspace storage?
- **Compliance/regulatory alignment › Requirements for regulatory framework(s)?** — *supporting;* primary pattern is [`compliance-security-profile.md`](compliance-security-profile.md).

## References

- [Customer-managed keys for encryption](https://docs.databricks.com/aws/en/security/keys/customer-managed-keys)
- [Configure customer-managed keys for encryption](https://docs.databricks.com/aws/en/security/keys/configure-customer-managed-keys)
- [Data security and encryption](https://docs.databricks.com/aws/en/security/keys)
