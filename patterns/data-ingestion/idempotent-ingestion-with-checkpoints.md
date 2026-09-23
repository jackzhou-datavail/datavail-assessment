# Idempotent Ingestion via Structured Streaming Checkpoints

**Category:** Data Ingestion

Ingestion jobs track their own progress in a checkpoint, so re-running a
failed job — or running it twice by accident — never produces duplicate or
missing rows.

## Why it matters

Ingestion jobs fail: a cluster gets preempted, a source API times out, a
job gets manually cancelled and re-triggered. Without a durable record of
exactly what has already been committed, a retry either re-processes data
that already landed (duplicates) or skips data that was in flight when the
failure happened (gaps). Both corrupt every downstream table without
throwing an error anyone notices.

## What good looks like

- Structured Streaming (including Auto Loader) writes its checkpoint to a
  durable location (a UC volume or cloud storage path) that is never shared
  between two different streams and is never deleted casually. A checkpoint
  directory holds **offsets** (source positions already processed, so a
  restart resumes exactly where it left off), **commits** (which
  micro-batches reached the sink, enabling exactly-once semantics), **state**
  (for stateful operations like aggregations/joins), and query **metadata**.
- Certain changes break checkpoint compatibility and force a fresh start —
  changing the input source type/count, or the schema of a stateful
  operation (aggregation, join, dedup) — so those are treated as
  deliberate, reviewed changes, not casual edits. Deleting the checkpoint or
  pointing at a new location silently restarts the query from scratch with
  no error.
- Batch ingestion that can't use a streaming checkpoint uses an equivalent
  idempotency key — `MERGE` on a natural/source key, or a `WHERE NOT EXISTS`
  guard — so re-running the same batch is a no-op the second time.
- The checkpoint/idempotency mechanism is part of the pipeline definition,
  not something bolted on after the first duplicate-data incident.

## How to detect

`system.lakeflow.job_run_timeline` / `pipeline_update_timeline` show
`result_state = 'FAILED'` or `'CANCELED'` runs for an ingestion job or
pipeline — a retried run right after a failure is expected. The anti-pattern
signal is the retry showing up in `system.access.table_lineage` as a fresh
full write to the *same* target table with no corresponding checkpoint
location in the job configuration, or a target table's row count growing by
more than one run's worth of data after a retry (worth spot-checking
manually; not something system tables expose directly).

## References

- [Structured Streaming checkpoints](https://docs.databricks.com/aws/en/structured-streaming/checkpoints)
- [Production considerations for Structured Streaming](https://docs.databricks.com/aws/en/structured-streaming/production)
- [Upsert into a Delta Lake table using merge](https://docs.databricks.com/aws/en/delta/merge)
