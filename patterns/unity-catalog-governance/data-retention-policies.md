# Explicit Data Retention Policies

**Category:** Unity Catalog Governance

How long each class of data is kept — and how it is removed when that
time is up or a deletion request arrives — is defined per domain and
implemented in table settings and automation, rather than being
whatever the Delta defaults happen to produce.

## Why it matters

Retention has two failure modes and most workspaces have both. Data is
kept forever because nobody decided otherwise, which grows storage cost
and turns every old table into regulatory exposure. And, at the same
time, history someone assumes exists has already been removed, because
Delta's defaults are short: `delta.logRetentionDuration` defaults to 30
days and `delta.deletedFileRetentionDuration` to 7. Databricks is
direct about it: "Don't use table history as a long-term backup
solution for data archival."

Deletion requests (GDPR, CCPA) add a third requirement: a `DELETE` is
not the end. On tables with deletion vectors "you must also run
`REORG TABLE ... APPLY (PURGE)`," and old file versions remain in
storage until `VACUUM` removes them.

## What good looks like

- A retention schedule per data class (raw landing, curated,
  PII-bearing, logs) owned by the data governance function and recorded
  somewhere discoverable — table comments or governed tags on the
  catalog/schema.
- **Row-level expiry automated** with auto time-to-live where it fits:
  `ALTER TABLE t DELETE ROWS <n> DAYS AFTER <time_column>` on UC managed
  Delta/Iceberg tables and streaming tables. It relies on predictive
  optimization to run `DELETE` and `VACUUM`.
- **Table history sized to need**, not left at default: longer
  `logRetentionDuration`/`deletedFileRetentionDuration` only where time
  travel is a real requirement (accepting the storage cost), and a
  proper backup/DR copy where history is a recovery mechanism — see
  [`../platform-onboarding/disaster-recovery-strategy.md`](../platform-onboarding/disaster-recovery-strategy.md).
- **A tested deletion path** for subject-access and erasure requests:
  delete → `REORG ... APPLY (PURGE)` where deletion vectors are on →
  `VACUUM` → propagate downstream (materialized views handle source
  deletes; streaming tables need `skipChangeCommits` or a full refresh).
- VACUUM retention managed consistently — see
  [`../table-optimization/unmanaged-vacuum-retention.md`](../table-optimization/unmanaged-vacuum-retention.md).
- Audit logs retained for the period compliance requires, which is
  usually longer than the system table keeps them.

## How to detect

`SHOW TBLPROPERTIES` (or `DESCRIBE DETAIL`) per table exposes
`delta.logRetentionDuration`, `delta.deletedFileRetentionDuration`, and
the auto-TTL properties `autottl.expireInDays` / `autottl.timestampColumn`.
Findings: PII-tagged tables with no TTL and no documented retention;
tables whose retention settings differ from the schema's documented
policy; and very old, unqueried tables (last read in
`system.access.table_lineage` / `system.query.history` long ago) still
holding sensitive columns. `DESCRIBE DETAIL` (`sizeInBytes`) shows what indefinite retention is costing.

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **Compliance/regulatory alignment › Data retention policies** — *primary.* Is there a documented retention schedule, implemented with auto-TTL / table retention settings, and a tested deletion (erasure) path?
- **Compliance/regulatory alignment › PII handling** — *supporting;* primary pattern is [`automated-pii-classification.md`](automated-pii-classification.md).

## References

- [Work with table history](https://docs.databricks.com/aws/en/tables/history)
- [Automatic row deletion with auto time-to-live](https://docs.databricks.com/aws/en/tables/operations/auto-ttl)
- [Prepare your data for GDPR compliance](https://docs.databricks.com/aws/en/ldp/gdpr)
- [Remove unused data files with vacuum](https://docs.databricks.com/aws/en/delta/vacuum)
