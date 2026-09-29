# Governed Data Sharing with Delta Sharing / OpenSharing

**Category:** Data Sharing & Collaboration

Data shared with other business units, partners, or customers is shared
in place through Unity Catalog shares — Databricks-to-Databricks where
the recipient is on Databricks, open sharing otherwise — with
recipients, tokens, and access audited, rather than exported as files.

## Why it matters

OpenSharing (formerly Delta Sharing) is "Databricks' open protocol for
securely sharing data and AI assets with users outside your
organization, whether or not they use Databricks." The recipient reads
the provider's live data; no copy is made, so there is nothing to keep
in sync and nothing left behind when access is revoked. Shares can
contain tables and streaming tables, views (including dynamically
filtered ones), volumes, ML models, materialized and metric views, and
— Databricks-to-Databricks only — notebooks. The same mechanism powers
Databricks Marketplace and Clean Rooms, and internal sharing across
metastores and regions.

Sharing is also a governance surface. Every recipient is an external
identity with access to production data, and open-sharing bearer tokens
are credentials: "tokens are valid for a maximum of one year after
creation," and a leaked activation link is a leaked credential.

## What good looks like

- **Databricks-to-Databricks** for any recipient with a UC-enabled
  workspace (stronger authentication, richer asset types, row/column
  controls); open sharing (bearer token or OIDC federation) only for
  non-Databricks recipients.
- **Cross-region / cross-metastore internal sharing** used instead of
  replicating tables between the organization's own metastores.
- Shares scoped to purpose — one per recipient relationship or data
  product — containing views or filtered objects rather than whole
  schemas.
- **Recipient hygiene:** metastore default token lifetime set (not
  unlimited), IP access lists on open recipients, tokens rotated before
  expiry, and compromised tokens force-expired immediately.
- Every share and recipient has an owner group and a review date;
  unused recipients are removed.
- Egress cost considered for cross-cloud/cross-region consumers.

## How to detect

Inventory via `SHOW SHARES`, `SHOW RECIPIENTS`, `DESCRIBE RECIPIENT`
(authentication type, token expiry, IP access list) or the Shares /
Recipients APIs. Activity via `system.access.audit` — provider-side
`action_name` values include `deltaSharingQueriedTable`,
`deltaSharingQueriedTableChanges`, `generateTemporaryTableCredential`,
and `generateTemporaryVolumeCredential`. `system.billing.usage` with
`billing_origin_product` `DATA_SHARING` or `CLEAN_ROOMS` shows usage.
Findings: open recipients with no expiry or IP list, recipients with no
activity in 90 days, and shares containing entire schemas of
unclassified data.

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **Data sharing and collaboration › Use of external/internal sharing** — *primary.* Is data shared in place via Delta Sharing / OpenSharing with governed recipients, rather than by exporting copies?

## References

- [What is OpenSharing?](https://docs.databricks.com/aws/en/opensharing)
- [Create a recipient using bearer tokens (Databricks-to-Open)](https://docs.databricks.com/aws/en/delta-sharing/create-recipient-token)
- [Create data recipients (Databricks-to-Databricks)](https://docs.databricks.com/aws/en/delta-sharing/create-recipient)
- [Audit and monitor data sharing](https://docs.databricks.com/aws/en/delta-sharing/audit-logs)
