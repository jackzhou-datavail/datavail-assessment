# Data Copies Instead of Sharing

> ⚠️ **ANTI-PATTERN**

**Category:** Data Sharing & Collaboration

Data is shared by copying it — scheduled CSV/Parquet exports to SFTP or
a partner's bucket, tables replicated between the organization's own
workspaces or metastores by ETL, spreadsheets emailed from query
results — instead of granting access to the governed source.

## Why it happens

Exports are the pattern everyone already knows, and they need no
agreement from the recipient's platform team. Before Unity Catalog,
there often wasn't an alternative across workspaces, so copy jobs were
built and then kept running out of inertia after UC made them
unnecessary. Partners ask for "a file every morning," and a file every
morning is what they get.

## Impact

- **Governance ends at the export.** Row filters, column masks, lineage,
  and audit apply to the source table; the copy has none of them.
  Revoking access means asking the recipient to delete files.
- **Staleness and drift.** Each copy is a snapshot; consumers act on
  yesterday's data, and schema changes break the export silently.
- **Cost multiplies.** Compute to produce the copy, storage for every
  copy, egress to ship it — for data the recipient could read in place.
- **Security exposure.** Credentials for SFTP servers and external
  buckets live in jobs and scripts, and files land in systems the
  organization doesn't monitor.
- **Duplicate truth** internally: two metastores each with "the"
  customer table, diverging.

## How to fix

1. Inventory outbound copies (see detection) and group by recipient.
2. For internal consumers, replace ETL copies with grants on the source
   catalog, or with cross-metastore / cross-region internal sharing.
3. For external Databricks recipients, move to Databricks-to-Databricks
   sharing; for others, open sharing with token expiry and IP lists —
   see [`governed-data-sharing.md`](governed-data-sharing.md).
4. Share curated views, not raw tables, so the shared contract is
   explicit and filtering happens at the source.
5. Where multi-party computation on sensitive data is the real need,
   consider Clean Rooms rather than exchanging extracts.
6. Retire the export jobs and the credentials they used.

## How to detect

`system.query.history` / `statement_text` with `INSERT OVERWRITE
DIRECTORY`, `COPY INTO` targeting external locations, or large
scheduled `SELECT *` reads by JDBC/ODBC clients; jobs in
`system.lakeflow.jobs` whose code writes to external paths or SFTP
libraries (repo scan). `system.access.table_lineage` showing a table in
one catalog repeatedly written from a table of the same name/shape in
another catalog indicates internal replication. Outbound volume shows in
billing as `NETWORKING` egress. A cross-check: external partners with
steady data exchange but no recipient objects in `SHOW RECIPIENTS`.

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **Data sharing and collaboration › Use of external/internal sharing** — *supporting;* primary pattern is [`governed-data-sharing.md`](governed-data-sharing.md).

## References

- [What is OpenSharing?](https://docs.databricks.com/aws/en/opensharing)
- [Set up OpenSharing for your account (providers)](https://docs.databricks.com/aws/en/opensharing/set-up)
- [Lineage in Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-lineage)
