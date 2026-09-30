# Databricks Workspace Assessment

Measures a Databricks workspace and writes the results to a dedicated
Unity Catalog catalog, where a dashboard reads them.

Two assessments, deliberately separate because they answer different
questions:

| | Question | Status |
|---|---|---|
| **[Conformance](src/datavail_assessment/conformance/)** | Of the things this workspace does, how well does it do them? | 98 patterns, 42 implemented checks |
| **[Adoption](src/datavail_assessment/adoption/)** | How much of the Databricks platform does it use at all? | 76 checks, all implemented |

They are independent on purpose. A workspace can run a narrow footprint
impeccably, or sprawl across the whole platform and run all of it badly.
Collapsing the two into one number hides which conversation to have.

## Layout

```
src/datavail_assessment/
  core/          shared runtime — executors, preflight, scoring, persistence
  conformance/   conformance to documented Databricks practice
  adoption/      breadth and depth of platform usage
  dashboard/     the Datavail Assessment dashboard, one module per page
patterns/        98 documented patterns and anti-patterns
adoption_checks/ the adoption checklist and its derivation from the patterns
databricks.yml   deploys both collectors as one job, plus the dashboard
pyproject.toml   src layout; `pip install -e .` to work on it
```

`core/` exists so a second assessment does not reimplement the run loop.
It owns the result vocabulary (`model.py`), the scoring and coverage
maths (`scoring.py`), both executors (`warehouse.py` for a SQL
warehouse, `spark.py` for a job), the result schema (`schema.sql`), and
the loop itself (`runner.py`). An assessment supplies only its scorable
items and its checks.

`src/` is a container, not a package — the importable package is
`datavail_assessment`, so imports resolve from any working directory
once installed.

## Running

Either assessment runs the same two ways. From a laptop, through a SQL
warehouse — no cluster, no pyspark:

```bash
pip install -e .

python -m datavail_assessment.conformance.run \
  --profile <cli-profile> --warehouse-id <warehouse-id> --dry-run

python -m datavail_assessment.adoption.run \
  --profile <cli-profile> --warehouse-id <warehouse-id> --dry-run
```

`--dry-run` executes every check and prints the result without creating
the results catalog or writing a row. Drop it to record a run.

As a scheduled job, where both run in parallel as two tasks:

```bash
databricks bundle deploy -p <profile> \
  --var warehouse_id=<id> --var alert_email=<group-alias>
databricks bundle run platform_assessment_collect -p <profile> \
  --var warehouse_id=<id> --var alert_email=<group-alias>
```

The job runs the same entry points with `--spark`. The schedule ships
**paused** — deploying does not start collecting on its own.

## Results

Written to `assessment.results` (catalog and schema configurable via
`--results-catalog` / `--results-schema` or the
`ASSESSMENT_RESULTS_CATALOG` / `ASSESSMENT_RESULTS_SCHEMA` environment
variables). The results catalog is always excluded from assessment
scope, so recording results never changes them.

| Tables | |
|---|---|
| Conformance | `assessment_run`, `pattern_registry`, `check_result`, `check_finding`, `category_score`, `assessment_score`, `v_latest_report` |
| Adoption | `adoption_check_history`, `adoption_section_score` |

```sql
SELECT * FROM assessment.results.v_latest_report ORDER BY category, severity;
SELECT * FROM assessment.results.adoption_section_score WHERE section = 'OVERALL';
```

**Every check produces either a measurement or an explicit reason there
isn't one — never a silent pass.** Conformance publishes a coverage
percentage alongside every score: 57 at 33% coverage means two thirds of
the library could not be measured here, and saying so is the point.
Adoption excludes anything unobservable from its denominator rather than
scoring it zero, because "we cannot see it" is not "they do not use it".

## Dashboard

**Datavail Assessment** — deployed by the bundle, one page per question.
Today: Adoption and Conformance.

It is bundle-managed, so edit the generator rather than the dashboard in
the UI. A UI edit makes the next `bundle deploy` fail rather than
silently lose the change, and recovering means `bundle generate` or
`--force`.

```bash
python -m datavail_assessment.dashboard.build --results-catalog assessment
```

Adding a page is a module under `dashboard/pages/` supplying
`datasets()` and `layout()`, plus one entry in `PAGES`.

## Further reading

- [src/datavail_assessment/conformance/README.md](src/datavail_assessment/conformance/README.md) — check tiers, what is and is not measurable, known approximations
- [src/datavail_assessment/adoption/README.md](src/datavail_assessment/adoption/README.md) — scoring model and how the checks were derived
- [patterns/README.md](patterns/README.md) — the pattern library index
- [patterns/GAPS.md](patterns/GAPS.md) — what the library still does not cover
