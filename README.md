# Databricks Workspace Assessment

Tooling that measures a Databricks workspace and writes the results to a
dedicated Unity Catalog catalog, where dashboards read them.

Two assessments, deliberately separate because they answer different
questions:

| | Question | Status |
|---|---|---|
| **[Conformance](src/conformance/)** | How well does this workspace do the things it is already doing? | Working — 98 patterns, 42 implemented checks |
| **[Adoption](src/adoption/)** | How much of the Databricks platform has this workspace actually adopted? | Not started |

## Layout

```
src/
  core/          shared runtime — execution, preflight, scoring, persistence
  conformance/   conformance to documented Databricks practice
  adoption/      platform adoption (placeholder)
patterns/        the pattern library: 98 documented patterns and anti-patterns
databricks.yml   bundle that deploys the conformance collector as a job
```

`src/core/` exists so a second assessment does not reimplement the run
loop. It owns the result vocabulary (`model.py`), the weighted scoring
and coverage maths (`scoring.py`), both executors (`warehouse.py` for a
SQL warehouse, `spark.py` for a job), the result schema (`schema.sql`),
and the run loop itself (`runner.py`). An assessment supplies only its
scorable items and its checks.

## Running the conformance assessment

From a laptop — no cluster, no pyspark, just a CLI profile and a
warehouse id:

```bash
python -m src.conformance.run \
  --profile <cli-profile> \
  --warehouse-id <warehouse-id> \
  --dry-run          # run every check, print the result, write nothing
```

Drop `--dry-run` to write a run. As a scheduled job instead:

```bash
databricks bundle deploy -p <profile> --var alert_email=<group-alias>
databricks bundle run  platform_assessment_collect -p <profile> --var alert_email=<group-alias>
```

The job runs the same entry point with `--spark`.

## Results

Six Delta tables plus a report view in `assessment.results` (catalog and
schema are configurable). Every item produces either a conformance
percentage or an explicit reason no measurement was possible — never a
silent pass.

```sql
SELECT * FROM assessment.results.v_latest_report ORDER BY category, severity;
```

**Scores are always published with the coverage they were computed
from.** A score of 57 at 33% coverage means two thirds of the library
could not be measured on this workspace, and saying so is the point.

See [src/conformance/README.md](src/conformance/README.md) for check tiers, what
is and is not measurable, and the known approximations.
