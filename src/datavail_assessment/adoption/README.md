# Adoption Assessment

Measures how much of the Databricks platform a workspace actually uses.
76 checks across six areas, all implemented.

## The question it answers

[Conformance](../conformance/) asks *how well is this workspace doing
the things it already does* — is bronze append-only, are jobs owned by
service principals, are columns documented. Adoption asks a different
question: *which parts of the platform are in use at all.*

A workspace can score well on conformance while using a tenth of what it
pays for. The two are independent, and a strong score on a narrow
footprint is a different conversation from a weak score on a broad one.

## Scoring

Each check scores an ordinal rather than a percentage:

| | |
|---|---|
| **2 — In real use** | clear evidence of regular activity |
| **1 — Barely used** | switched on, little activity. Usually the cheapest gap to close, since the setup cost is already paid |
| **0 — Not used** | no evidence |

A section scores `points / max_points`, where max is two per *measurable*
check. The overall is the **weighted sum of the section percentages**,
not the ratio of total points — the two differ, which is why the
`OVERALL` row leaves `points` and `max_points` NULL.

| Section | Weight |
|---|---|
| Workspace | 0.22 |
| Data Engineering | 0.22 |
| SQL | 0.18 |
| AI/ML | 0.18 |
| Governance & Security | 0.12 |
| Data Sharing | 0.08 |

Grades: **STRONG** ≥ 75, **DEVELOPING** ≥ 40, **EARLY** ≥ 10, else
**NOT ADOPTED**. Overall: **FULLY LEVERAGED** ≥ 80, **BROADLY ADOPTED**
≥ 60, **PARTIALLY ADOPTED** ≥ 35, **EARLY STAGE** ≥ 10, else **NOT
ADOPTED**.

Deliberately not `core.scoring`, which produces a percentage per item.
Forcing both models through one would flatten the difference between
"what share of these objects follow the practice" and "is this used at
all".

## Unmeasurable is not unused

A check that cannot be observed is **excluded from the denominator**,
not scored zero. Scoring it zero would read as "unused" when the truth
is "unlooked-at" — blaming the workspace for a gap in the tooling. Every
section therefore reports `coverage_pct` alongside its score.

Two related mechanisms:

- `absent_means_zero` — for feature-gated system tables like
  `system.data_quality_monitoring`, which only exists once the feature
  is used. There, absence genuinely *is* the answer, so a missing table
  resolves to 0 rather than an error.
- Four checklist items were **removed** rather than approximated,
  because no data source answers them: dashboard parameters and Agent
  Bricks tiles have no inventory outside their APIs,
  `system.lakeflow.job_tasks` has no `task_type` column, and
  `system.serving.served_entities` carries no inference-table setting.

## Layout

```
checks.py    76 checks as data: 66 single-query, 10 compound
scoring.py   ordinal scoring, section rollup, grade bands
run.py       entry point, samplers, persistence
```

Most checks are one scalar query plus two thresholds. Ten need more:
either several queries combined by a rule two thresholds cannot express,
or a **sampler** for per-object inspection no single query provides —
`delta_history` and `clustering` (DESCRIBE per table, sampled),
`sharing_inventory` (SHOW SHARES / RECIPIENTS / PROVIDERS), and
`abac_policies` (SHOW POLICIES per catalog).

## Running

```bash
python -m datavail_assessment.adoption.run \
  --profile <cli-profile> --warehouse-id <id> --dry-run
```

Drop `--dry-run` to write. `--spark` runs it inside a job instead. Both
paths share `core`'s executors and produce identical results.

## Results

`adoption_check_history` — one row per check per run, carrying the score,
the raw value, and `value_display`, which renders the value with its
unit. That column exists because `raw_value` is a DOUBLE holding
whatever the check counted — people, queries, DBUs, a percentage — and
shown bare they are indistinguishable: 64 active users displayed as
"64.00" reads as a percentage.

`adoption_section_score` — per-section rollup plus one `OVERALL` row.

## Provenance

The checks began as the `Adoption Baseline Checks` notebook and were
extended from the pattern library. [`adoption_checks/`](../../../adoption_checks/)
holds the checklist, the derivation, and the pattern-area map. The
checklist's **Implemented** column is kept in step with `checks.py`:
every row reads *Yes*, and anything that could not be implemented was
removed rather than left aspirational.
