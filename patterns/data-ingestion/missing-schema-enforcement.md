# Missing Schema Enforcement / Evolution Handling

> ⚠️ **ANTI-PATTERN**

**Category:** Data Ingestion

The ingestion job infers the schema fresh on every run (or otherwise
doesn't pin a schema at all) and has no explicit policy for what happens
when the source adds, removes, renames, or changes the type of a column.

## Why it happens

Schema inference is the zero-config default in most read paths, and most of
the time the source doesn't change shape, so it's invisible until it does.
Nobody decides to skip schema handling — it's just never added because the
first version of the pipeline didn't need it.

## Impact

- A silently dropped or renamed source column produces `NULL`s downstream
  with no error, and the first sign of trouble is a wrong number in a
  report weeks later.
- A source column that changes type (e.g. an ID field going from `INT` to
  `STRING`) can fail the write outright, or worse, silently coerce and lose
  precision.
- Every consumer of the table is exposed to the same instability
  independently — there's no single place where a schema change is
  reviewed and handled once.

## How to fix

1. Use Auto Loader's schema inference **with** an explicit
   `cloudFiles.schemaEvolutionMode` (`addNewColumns`, `rescue`, `failOnNewColumns`,
   or `none`) instead of the unmanaged default, and store the inferred
   schema so it's stable across runs.
2. For Lakeflow Connect / structured sources, rely on the connector's
   built-in schema-change handling rather than re-inferring per run.
3. Add a rescued-data column (`_rescued_data`) so unexpected fields are
   captured instead of silently dropped, and alert on it being non-empty.
4. Define `CONSTRAINT`s or DLT expectations for the columns downstream
   consumers actually depend on, so a breaking change fails the pipeline
   run instead of passing through quietly.

## How to detect

Not directly queryable from Unity Catalog system tables (schema-evolution
configuration lives in pipeline/job source code, not metadata). The
practical proxy this repo's assessment tooling uses instead is table
comment coverage and naming-convention compliance from
`system.information_schema.tables` — a codebase where bronze tables
generally lack comments and consistent naming is also, empirically, one
where schema-handling conventions were never established. Treat that as a
signal to go read the ingestion source, not as proof on its own.

## References

- <https://docs.databricks.com/ingestion/auto-loader/schema.html>
