# Unmanaged VACUUM Retention

> ⚠️ **ANTI-PATTERN**

**Category:** Table Optimization

Either `VACUUM` never runs on a table at all (unreferenced files
accumulate indefinitely, inflating storage cost), or its retention window
was shortened without understanding the risk (active long-running jobs or
needed time-travel history get deleted out from under them).

## Why it happens

Both directions come from the same root cause: nobody owns table
maintenance as an explicit policy. Never running `VACUUM` is simple
neglect — deleted/superseded files just pile up invisibly in cloud
storage, and nothing about query correctness signals the problem, only
the storage bill does, slowly. Over-aggressive retention usually happens
the opposite way: someone notices the storage cost and shortens
`delta.deletedFileRetentionDuration` without accounting for what else
depends on that window — in-flight long-running jobs, or team members
relying on time travel to recover from a bad write.

## Impact

- **Never vacuuming**: storage costs grow unbounded as old file versions
  accumulate — every `UPDATE`/`DELETE`/`MERGE`/`OPTIMIZE` leaves the
  previous file versions in place until `VACUUM` removes them.
- **Retention set too short**: Databricks is explicit that the default
  7-day window exists partly because "long-running jobs might write files
  that are not yet committed" — a retention period shorter than that risks
  `VACUUM` deleting files a still-running job needs, corrupting that job's
  output. Databricks "strongly recommends" never going below 7 days.
- **Deletion vectors, unpurged**: on tables with deletion vectors enabled,
  `VACUUM` alone doesn't reclaim the space soft-deleted rows still occupy —
  `REORG TABLE ... APPLY (PURGE)` has to run first, or file compaction
  from normal writes, since neither is guaranteed to resolve deletion-vector
  entries on its own. A table that "has VACUUM" but never purges deletion
  vectors is quietly not saving the storage it looks like it should.

## How to fix

1. Enable predictive optimization so `VACUUM` (and `PURGE`, where deletion
   vectors are in play) runs automatically and correctly sequenced,
   instead of depending on a manually scheduled job per table — see
   [`predictive-optimization-autopilot.md`](predictive-optimization-autopilot.md).
2. If managing retention manually, never set
   `delta.deletedFileRetentionDuration` below 7 days; raise it (e.g. to 30
   days) for tables where longer time-travel recovery is genuinely
   valuable, and treat that as a deliberate storage/recoverability
   trade-off, not a default left unexamined.
3. For tables with deletion vectors, schedule `REORG TABLE ... APPLY
   (PURGE)` before `VACUUM`, not after — reversing the order leaves
   soft-deleted data unreclaimed.

## How to detect

Not currently queried by `data_collection/collect_data.py` — VACUUM
history and the `delta.deletedFileRetentionDuration` table property
aren't in `system.information_schema.tables`. Confirming this needs
`DESCRIBE HISTORY <table>` (to check whether/when `VACUUM` last ran) and
`SHOW TBLPROPERTIES` per table.

## References

- [Remove unused data files with vacuum](https://docs.databricks.com/aws/en/tables/operations/vacuum)
- [Deletion vectors in Databricks](https://docs.databricks.com/aws/en/tables/features/deletion-vectors)
- [Predictive optimization for Unity Catalog managed tables](https://docs.databricks.com/aws/en/optimizations/predictive-optimization)
