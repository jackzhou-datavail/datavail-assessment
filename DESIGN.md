# How collection works

What starts a run, what runs, and how the results reach a dashboard.
Covers **both** assessments, which share less than their layout
suggests — see [What the two actually share](#what-the-two-actually-share).

## What starts a collection

Three entry points, all reaching the same code:

| | |
|---|---|
| **Schedule** | Mondays 06:00 UTC. Ships `pause_status: PAUSED`, so deploying does not start collecting. |
| **Manual** | `databricks bundle run platform_assessment_collect` |
| **Laptop** | `python -m datavail_assessment.<assessment>.run --profile <p> --warehouse-id <id> [--dry-run]` |

`--dry-run` executes every check and prints the result without creating
the results schema or writing a row.

## The job

```
Job  "Datavail Assessment — Collect"              max_concurrent_runs: 1
│
├── task: collect ──────────► ./job_conformance.py   ─┐  parallel,
└── task: collect_adoption ─► ./job_adoption.py      ─┘  no dependency

     each task:  environment_key: collector
                 serverless client "4"
                 dependencies: ./dist/*.whl, pyyaml
                 max_retries 2, timeout_seconds 3600
```

The two tasks are independent on purpose: one failing does not block the
other. The cost is that a half-failed run leaves one dashboard page
fresh beside a stale one, since each half resolves its own latest run.

### Why the launchers are three lines

`job_conformance.py` and `job_adoption.py` do nothing but import `main`
from the wheel and call it. Two constraints force that:

- `spark_python_task` **`exec()`s the file without defining `__file__`**,
  so anything resolving its own location raises `NameError` before the
  job starts. This is why `core/paths.py` exists — it resolves paths via
  the imported package instead.
- On serverless the file is `exec()`d inside an IPython kernel where even
  `SystemExit(0)` is reported as a workload failure. So the launchers
  signal only on a non-zero result; the collector would otherwise write
  its results and still fail the task.

## Conformance: the run loop

```
conformance/run.py
   │  --spark ? SparkExecutor : WarehouseExecutor
   │  load_registry(registry.yaml, patterns/) → 98 patterns + version + sha
   ▼
core/runner.py  execute()
   1. drift guard    a check defined but marked impl: false → abort, named
   2. probe_facts    IF_ML / IF_GENAI / IF_SHARING / IF_STREAMING /
                     IF_MULTI_WORKSPACE, from the workspace itself
   3. per pattern    run_check()
   4. core/scoring   per-category and overall score + coverage
   5. ensure_schema  core/schema.sql → tables + v_latest_report
   6. persist        six tables, unless --dry-run
```

`run_check()` resolves one pattern four ways:

| Condition | Outcome |
|---|---|
| `impl: false` | `NOT_AVAILABLE` with the tier's reason — **no query is issued** |
| in `PY_CHECKS` | a Python function: `table_detail` (DESCRIBE DETAIL, sampled 50), `grants` (SHOW GRANTS per catalog), `workspace_api` (Jobs / Secrets / permissions REST) |
| in `CHECKS` | **preflight first**: is each required table readable, are its columns present? If not, `NOT_AVAILABLE` naming what is missing. Then the measure SQL returns `numerator`/`denominator`, plus an optional findings query for evidence rows. |
| `denominator = 0` | `NOT_APPLICABLE` — the check ran and found nothing in scope |

The preflight is what makes `NOT_APPLICABLE` trustworthy: an unreadable
table is caught *before* the query, so an empty result can only mean
genuine absence, never a permission problem.

## Adoption: its own loop

Adoption does **not** go through `core/runner.py`. `adoption/run.py`
holds its own loop, its own table DDL, and `adoption/scoring.py` its own
model. The two scoring models are deliberately not merged:

- **Conformance** — weighted mean conformance percentage over measured
  checks, with coverage reported beside it. Per-pattern `target`/`floor`
  thresholds decide GOOD / FAIR / POOR.
- **Adoption** — an ordinal per check (2 in real use, 1 barely used,
  0 not used), rolled up by section weights.

Forcing both through one model would flatten the difference between
"what share of these objects follow the practice" and "is this used at
all".

Four checks need per-object inspection no single query provides, so
`adoption/run.py` carries samplers: `delta_history`, `clustering`,
`sharing_inventory` and `abac_policies`.

## What the two actually share

| | Conformance | Adoption |
|---|---|---|
| `core/warehouse.py`, `core/spark.py` | yes | yes |
| `core/sqlutil.py` | via runner | yes |
| `core/runner.py` | **yes** | no — own loop |
| `core/scoring.py` | **yes** | no — own `scoring.py` |
| `core/schema.sql` | **yes** | no — inline DDL |
| `core/paths.py` | yes | no |
| Results catalog | shared | shared |
| Reporting categories | shared six | shared six |

So the real shared surface is **the executors, the results catalog, and
the category vocabulary**. The run loop and scoring are separate by
design.

## The two executors

One interface, so every check runs unchanged on either path:

```
WarehouseExecutor                      SparkExecutor
  query/execute → CLI subprocess         query/execute → spark.sql
                → SQL Statement API      api()         → databricks-sdk
  api()         → databricks api get                     (absent → raises
  capability    → information_schema                      NotImplementedError,
                                                          recorded as
                                                          NOT_AVAILABLE)
```

The warehouse path shells out once per call, which is cheap for SQL and
expensive for REST: a run making ~40 API calls once pushed past ten
minutes and timed out unrelated SQL behind it. Hence the bounded
samplers. A persistent HTTP session is the real fix and is not built.

## Sources and outputs

Read: `system.access.*`, `system.billing.*`, `system.compute.*`,
`system.lakeflow.*`, `system.query.*`, `system.mlflow.*`,
`system.serving.*`, `system.information_schema.*`, plus
`DESCRIBE DETAIL`, `SHOW GRANTS` and the Jobs/Secrets/permissions APIs.

Written to `assessment.results` — **always excluded from assessment
scope**, so recording results never changes them. `ALWAYS_EXCLUDED`
in `core/runner.py` also drops `system`, `samples` and
`__databricks_internal`.

| | Tables |
|---|---|
| Conformance | `assessment_run`, `pattern_registry`, `check_result`, `check_finding`, `category_score`, `assessment_score`, `v_latest_report` (view) |
| Adoption | `adoption_check_history`, `adoption_section_score` |

## Dashboards

**Dashboards never trigger collection.** They read whatever the latest
`COMPLETE` run wrote. Two independent staleness sources follow: the
schedule ships paused, and Lakeview does not re-query until someone
reloads the page.

| Dashboard | Pages |
|---|---|
| Datavail Assessment | Adoption, Conformance: Scorecard, Conformance: Findings |
| Conformance Assessment | the same two, plus Coverage & Blind Spots |

Both conformance pages come from one builder, so a change reaches both.
Host and workspace id are baked in at generation time, because a
dashboard's SQL cannot learn either and the Findings page links to the
offending object:

```bash
python -m datavail_assessment.dashboard.build \
  --workspace-url https://<host> --org-id <workspace_id>
```
