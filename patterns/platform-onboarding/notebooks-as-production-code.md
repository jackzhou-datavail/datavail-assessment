# Notebooks as Production Code

> ⚠️ **ANTI-PATTERN**

**Category:** Platform Onboarding

Business logic lives inside notebooks in the production workspace,
edited in place, with no version control, no tests, and no promotion
path — the notebook *is* the deployment artifact.

## Why it happens

Notebooks are the fastest way to get something working on Databricks,
and the thing that works is already sitting in the workspace. Turning
it into a job is one click; turning it into a tested, versioned,
bundle-deployed module is a week of unfamiliar work. So the prototype
gets scheduled, and the prototype is now production.

Editing in place then becomes the incident-response habit: a pipeline
fails at 2am, someone fixes the notebook directly, and the fix exists
only in the workspace. Nobody deliberately chose this architecture —
it's what accumulates when the CI/CD path is slower than the UI path.

## Impact

- No history and no review. Nobody can answer what changed, when, or
  why a pipeline that worked last week doesn't now.
- No testable unit. Logic embedded in notebook cells can't be imported
  by pytest, so the three-layer testing model (unit tests, `bundle
  validate`, staging integration tests) has nothing to attach to.
- Dev and prod diverge permanently — the workspace copy is the truth,
  and the repo copy, if one exists, silently rots.
- No rollback. Recovering from a bad change means remembering what the
  old code was.
- Duplicated logic, since the only way to reuse a notebook's logic is
  to copy its cells into another notebook.
- Hardcoded environment values are near-inevitable, because there's no
  parameterization layer to put them in.

## How to fix

1. Extract the logic: "store core logic in importable `.py` modules and
   queries in `.sql` files; use notebooks only for orchestration and
   visualization." The notebook shrinks to a thin caller.
2. Put everything in Git — notebooks, source, and `databricks.yml` —
   and develop through Databricks Git folders or VS Code with the
   Databricks extension, so the workspace is a view onto the repo. See
   [`git-backed-development-and-cicd.md`](git-backed-development-and-cicd.md).
3. Deploy via Declarative Automation Bundles so production code arrives
   through a pipeline, and make production workspace paths writable only
   by the deployment service principal.
4. Replace hardcoded cross-task values with dynamic references
   (`{{tasks.<task_key>.values.<value_key>}}`).
5. Give developers personal schemas (`dev_${user_name}`) so the
   temptation to iterate against shared or production tables goes away.
6. Add the test layers incrementally — `bundle validate` in CI is
   nearly free and catches a surprising amount.

## How to detect

The Workspace API reports whether a notebook path sits inside a Git
folder; production notebooks outside one are the direct finding. In
system tables, `system.access.audit` records notebook and workspace
file events, so interactive edits in a production workspace — and who
made them — are visible there.
`data_collection/collect_data.py` reads `system.access.table_lineage`
filtered on `entity_type` of `NOTEBOOK` / `DBSQL_QUERY` to find direct
ad-hoc writes to tables, which is the closely related signal: a notebook
or ad-hoc query writing to a production table outside any pipeline.
See also
[`../data-ingestion/direct-writes-to-bronze-tables.md`](../data-ingestion/direct-writes-to-bronze-tables.md).

## References

- [Developer best practices on Databricks](https://docs.databricks.com/aws/en/developers/best-practices)
- [Best practices for operational excellence](https://docs.databricks.com/aws/en/lakehouse-architecture/operational-excellence/best-practices)
- [Declarative Automation Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/)
