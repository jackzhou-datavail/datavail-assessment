# Platform Assessment Collector

Measures a Databricks workspace against the [pattern library](../patterns/),
and writes the result to a dedicated catalog that is itself excluded
from assessment scope.

Every pattern yields exactly one row with one of two things: a
**percentage of objects following the good practice**, or an explicit
**reason no measurement was possible**. There is no third option, and a
missing measurement is never silently treated as a pass.

## Running it

There are **two independent ways to run the collector, and both are
supported**. Deploying the scheduled job does not replace, disable or
take precedence over the local script — they are separate entry points
over the same registry and the same checks, writing to the same result
tables. Use whichever suits the moment.

### 1. Locally, from a laptop (no cluster required)

`run_via_sql_warehouse.py` drives everything through the SQL Statement
Execution API using the Databricks CLI. It needs no pyspark, no
databricks-connect and no cluster — just a profile and a warehouse id.
This is the fastest loop for developing checks and for one-off runs.

```bash
python run_via_sql_warehouse.py \
  --profile uc-semantics \
  --warehouse-id <warehouse-id> \
  --results-catalog assessment \
  --lookback-days 30

# run every check and print the result, writing nothing
python run_via_sql_warehouse.py --profile <p> --warehouse-id <id> --dry-run
```

### 2. As a scheduled Databricks job

`run_assessment.py` is the same collector against a Spark session, for
running inside the workspace on serverless job compute. It is deployed
by the bundle in `databricks.yml`:

```bash
cd assessment
databricks bundle deploy -p <profile>
databricks bundle run platform_assessment_collect -p <profile> --var alert_email=<group-alias>
```

The schedule ships **PAUSED** — deploying does not start collecting on
its own.

### Which is which

| | Local | Job |
|---|---|---|
| Script | `run_via_sql_warehouse.py` | `run_assessment.py` |
| Compute | SQL warehouse via the CLI | serverless job compute |
| Needs pyspark | no | provided by the runtime |
| Good for | developing checks, ad-hoc runs, debugging | scheduled refresh |

Both honour the same flags for scope and window, and both append a new
`run_id` to the same tables. The dashboard always reads the latest
`COMPLETE` run, so it does not care which produced it.

Additional catalogs can be kept out of scope with repeated
`--exclude-catalog` flags. `system`, `samples`,
`__databricks_internal` and the results catalog itself are always
excluded.

**Requirements.** SELECT on the `system` catalog. Several checks need
account-admin visibility — `system.query.history` is account-admin-only
by default — and report `NOT_AVAILABLE` with that reason rather than
failing when it is absent. Run as a service principal with a stable
identity, not a personal account.

## What comes out

Six Delta tables in `<results_catalog>.<results_schema>`:

| Table | Grain | Holds |
|---|---|---|
| `assessment_run` | 1 per run | scope, lookback, registry version and checksum, runner |
| `pattern_registry` | 1 per pattern per run | weights and thresholds as they were at run time |
| `check_result` | 1 per pattern per run | the score, or the reason there isn't one |
| `check_finding` | N per pattern per run | the specific objects behind a finding |
| `category_score` | 1 per category per run | weighted score and coverage |
| `assessment_score` | 1 per run | headline score, coverage, confidence |

Start here:

```sql
SELECT * FROM assessment.results.v_latest_report
ORDER BY category, severity;
```

The registry is snapshotted into `pattern_registry` on every run, and
`assessment_run` stores a SHA-256 of `registry.yaml`, so a historical
score stays interpretable after weights or thresholds change.

## Result semantics

`check_result.status` is one of:

- **`MEASURED`** — `conformance_pct` is populated, along with
  `numerator` (objects following the practice), `denominator` (objects
  in scope) and `unit`.
- **`NOT_AVAILABLE`** — the signal exists in principle but this
  collector could not read it. `reason` says exactly why: a system
  schema that isn't enabled, a missing grant, a renamed column, or a
  check tier that requires an API this collector doesn't call.
- **`NOT_APPLICABLE`** — nothing in scope. Either the workspace has no
  workloads of that kind (no ML, no GenAI, single workspace) or the
  denominator came back zero.
- **`ERROR`** — the check failed; `reason` carries the exception.

`grade` is derived from `conformance_pct` against the pattern's
`target_pct` and `floor_pct`: **GOOD** at or above target, **POOR**
below floor, **FAIR** between.

## Scoring

- `overall_score` and `weighted_score` are the weighted mean
  conformance across **`MEASURED` checks only**, weighted by severity
  (CRITICAL 5, HIGH 3, MEDIUM 2, LOW 1).
- `coverage_pct` is measured weight over applicable weight — the share
  of what *should* have been assessed that actually was.
- `confidence` is `HIGH` at coverage ≥ 70%, `MEDIUM` ≥ 40%, else `LOW`.

**Never quote the score without the coverage.** A score of 78 at 35%
coverage means most of the platform was not examined. `critical_gaps`
(CRITICAL-severity checks graded POOR) is the headline remediation
list.

## Check tiers and why coverage is partial

`registry.yaml` assigns each pattern a `check_tier`. Only
`SYSTEM_TABLE` is implemented here:

| Tier | Patterns | Implemented |
|---|---|---|
| `SYSTEM_TABLE` | 49 | 42 |
| `WORKSPACE_API` | 14 | — Genie, Dashboards, Workspace/Git, Jobs settings, `SHOW GRANTS` |
| `TABLE_DETAIL` | 6 | — needs `DESCRIBE DETAIL` per table |
| `MANUAL` | 6 | — design judgment, requires a conversation |
| `ACCOUNT_API` | 3 | — workspace inventory, admin roles, budgets |

So 42 of 78 patterns (54%) can produce a number today. The rest report
`NOT_AVAILABLE` with the tier's reason attached. That is the intended
behaviour, not a defect — see [../patterns/GAPS.md](../patterns/GAPS.md)
for the full gap analysis.

## Status of the SQL — read this before trusting a first run

**No check in `checks.py` has been executed against a live workspace.**
Column names were taken from Databricks system-table documentation where
it exists (`system.mlflow.*`, `system.compute.warehouses`,
`system.query.history`, `system.serving.served_entities`,
`system.billing.usage`) and inferred from schema descriptions otherwise.

The design compensates rather than hides: each check declares the
tables and columns it needs, a preflight probe verifies them, and
anything missing becomes `NOT_AVAILABLE` naming the exact object. A
wrong guess therefore produces an honest "could not measure" instead of
a crash or — much worse — a confident wrong number. Expect the first
real run to convert several checks from `MEASURED` to `NOT_AVAILABLE`;
those reasons are the to-do list for the second pass.

## Known approximations

Some checks measure a proxy. Each says so in its `note`, and the
significant ones are:

- **`always-on-oversized-warehouses`** — auto-stop and size-versus-load
  are not exposed by `system.compute.warehouses`, so this measures only
  whether a live warehouse ran any query in the window.
- **`stale-models-in-production`** — uses experiment update recency, not
  a direct serving-endpoint-to-training-run join.
- **Layer detection** (`bronze`/`gold`) is a naming-convention regex.
  A workspace that names layers differently will score badly for the
  wrong reason. Tune `BRONZE_RX` / `GOLD_RX` in `checks.py` per
  engagement.
- **`infrastructure-as-code-*`** — detects the `[target]` name prefix
  that bundle deployment applies, so it undercounts Terraform-managed
  jobs.
- **Paired checks** (`service-principals-for-automation` /
  `personal-identity-in-production`, and three other pairs) share one
  measure by design. They group via `root_cause` so a report can roll
  them into a single finding.

## Layout

```
assessment/
  registry.yaml        78 patterns: severity, weight, tier, thresholds, applicability
  schema.sql           result schema DDL (${results_catalog} / ${results_schema})
  lib.py               registry loader, capability preflight, scoring
  checks.py            the 42 implemented checks
  run_assessment.py    driver / entry point
```

`registry.yaml` stores no titles — they are read from the markdown at
load time, so the registry cannot drift from the documents it scores.
The loader works without PyYAML, so the registry can be validated off
cluster.
