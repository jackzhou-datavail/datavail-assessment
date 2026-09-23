# Databricks Patterns & Anti-Patterns

A reference library of Databricks platform patterns (things to do) and
anti-patterns (things to avoid), one file per pattern. Anti-patterns are
flagged with a `> ⚠️ **ANTI-PATTERN**` line immediately after the title so
they're unmistakable at a glance.

Each entry includes a **How to detect** section — where the signal is
realistically observable from Unity Catalog system tables, it's written to
line up with what `data_collection/collect_data.py` (on the `real_data`
branch) actually queries, so this library and the assessment tool stay
consistent with each other.

Content is verified against current Databricks documentation (linked in
each file's References section) as of 2026-09, not written from memory
alone — see individual files for exact source quotes.

## Categories

- **[Data Ingestion](data-ingestion/)** — landing raw data into the lakehouse
  - [Auto Loader / Lakeflow Connect for incremental ingestion](data-ingestion/autoloader-incremental-ingestion.md)
  - [Idempotent ingestion via Structured Streaming checkpoints](data-ingestion/idempotent-ingestion-with-checkpoints.md)
  - [Bronze layer immutability](data-ingestion/bronze-layer-immutability.md)
  - [Change data capture (CDC) for database ingestion](data-ingestion/change-data-capture-ingestion.md)
  - [Direct writes to bronze tables](data-ingestion/direct-writes-to-bronze-tables.md) — ⚠️ anti-pattern
  - [Full-table reload instead of incremental](data-ingestion/full-reload-instead-of-incremental.md) — ⚠️ anti-pattern
  - [Missing schema enforcement / evolution handling](data-ingestion/missing-schema-enforcement.md) — ⚠️ anti-pattern
  - [Small-file accumulation at landing](data-ingestion/small-file-accumulation.md) — ⚠️ anti-pattern

## File template

```markdown
# <Pattern Name>

> ⚠️ **ANTI-PATTERN**   <!-- omit this line entirely for a positive pattern -->

**Category:** <category>

<one- or two-sentence summary>

## Why it matters
## What good looks like        <!-- positive patterns -->
## Why it happens / How to fix  <!-- anti-patterns -->
## How to detect
## References
```
