# Coverage Gaps in the Pattern Library

Status as of 2026-09-23. 78 patterns across 7 categories, ~35K words.

This file records what the library does **not** cover, and the known
structural weaknesses inside what it does cover. It exists so that an
assessment built on this library can state its own blind spots rather
than presenting a partial review as a complete one.

## 1. Missing categories

### ~~Orchestration & job reliability~~ — **CLOSED 2026-09-23**

Added as [orchestration-reliability](orchestration-reliability/) (9
patterns, 4 with implemented checks). Covers task dependencies vs.
schedule chaining, retries and timeouts, failure notification and
duration thresholds, pipeline/job decomposition, and pipeline
expectations.

Still open within it: cross-job chaining detection needs a lineage
join, and retry/timeout/notification *configuration* is Jobs API rather
than system tables, so four of the nine report NOT_AVAILABLE.

### Data quality & reliability

Lakeflow pipeline expectations, quarantine patterns, table constraints
(`NOT NULL`, `CHECK`), primary/foreign key declarations, freshness
SLAs, and data profiling monitors on gold tables.
[medallion-layering-for-analytics.md](sql-analytics/medallion-layering-for-analytics.md)
mentions "quality checks at each layer" in passing and nothing follows
it up. Partly queryable via
`system.information_schema.table_constraints` and
`system.data_quality_monitoring`.

Estimated: 6–8 patterns.

### Security & network

Customer-managed encryption keys, private/secure cluster connectivity,
egress controls, IP access lists, compliance security profiles,
production data in DBFS, token management policies. Identity is covered
in [account-first-identity-federation.md](platform-onboarding/account-first-identity-federation.md);
the rest of the security surface is not. Mostly account/workspace API
rather than system tables, so it scores poorly on measurability — but
it is the domain clients most often name explicitly.

Estimated: 6–8 patterns.

### Lower priority

- **Streaming & real-time** — trigger modes, watermarks, stateful
  operations, state store sizing, exactly-once semantics. Partly
  covered by
  [idempotent-ingestion-with-checkpoints.md](data-ingestion/idempotent-ingestion-with-checkpoints.md).
- **HA / disaster recovery** — Phase 10 of the deployment guide:
  replication, RPO/RTO, multi-region posture. Small but high-stakes;
  `system.replication` exists.
- **Delta Sharing & data products** — shares, recipients, Marketplace,
  clean rooms. Relevant only where external sharing happens;
  `system.sharing` exists.

## 2. Imbalance inside existing categories

| Category | Patterns | Avg words |
|---|---|---|
| platform-onboarding | 16 | ~500 |
| orchestration-reliability | 9 | ~500 |
| ml-ai-lifecycle | 15 | ~500 |
| sql-analytics | 15 | ~500 |
| unity-catalog-governance | 9 | ~330 |
| data-ingestion | 8 | ~350 |
| table-optimization | 6 | ~330 |

The four newer categories were written in one pass and are both more
numerous and more detailed. The three oldest are thinner than their
real-world importance justifies — table layout in particular is where a
large share of avoidable cost sits.

**Consequence for scoring:** any scheme that weights by pattern count
will over-weight platform/ML/SQL and under-report the data layer. The
registry compensates with explicit per-pattern weights, but the
underlying content still deserves expansion.

Planned: bring table-optimization to ~10 and data-ingestion to ~12.

## 3. Overlapping root causes

Several patterns will fire together on a single underlying problem.
They are genuinely distinct findings, but an assessment report must
roll them up or it will read as repetitive:

- **Credentials / non-human identity** —
  [service-principals-for-automation](platform-onboarding/service-principals-for-automation.md),
  [personal-identity-in-production](platform-onboarding/personal-identity-in-production.md),
  [ungoverned-external-llm-access](ml-ai-lifecycle/ungoverned-external-llm-access.md)
- **Idle / mis-typed compute** —
  [all-purpose-compute-for-jobs](platform-onboarding/all-purpose-compute-for-jobs.md),
  [always-on-oversized-warehouses](sql-analytics/always-on-oversized-warehouses.md),
  [serverless-first-compute](platform-onboarding/serverless-first-compute.md)
- **Code not under version control** —
  [git-backed-development-and-cicd](platform-onboarding/git-backed-development-and-cicd.md),
  [notebooks-as-production-code](platform-onboarding/notebooks-as-production-code.md),
  [untracked-model-development](ml-ai-lifecycle/untracked-model-development.md)
- **Full rebuild instead of incremental** —
  [full-reload-instead-of-incremental](data-ingestion/full-reload-instead-of-incremental.md),
  [scheduled-snapshot-rebuilds](sql-analytics/scheduled-snapshot-rebuilds.md)

The registry assigns each a `root_cause` so findings can be grouped.

## 4. Measurability

54% of patterns (42 of 78) have an implemented check against `system.*`
tables.
The rest need the Account API, workspace APIs (Genie, Dashboards,
Workspace/Git), repository scans, or a human conversation. An
assessment that silently skips the non-SQL tiers will report a
flattering and wrong result.

This is why every check reports a `status` and, where it cannot
measure, a `reason` — and why the overall score is always published
alongside a `coverage_pct`. See
[`../assessment/README.md`](../assessment/README.md).

## 5. Framing limits

- The library measures **conformance to documented Databricks
  guidance**. It is not a compliance audit (no SOC 2 / HIPAA mapping)
  and carries no cost benchmarks — it can show that spend is
  unattributable, not whether it is high.
- It has nothing on team capability, runbooks and on-call practice,
  chargeback culture, or cases where a Databricks feature is the wrong
  choice.
- No detection logic in the library has been executed against a real
  workspace. Column names were verified from documentation for
  `system.mlflow.*`, `system.compute.warehouses`, `system.query.history`
  and `system.serving.*`; others were inferred from schema descriptions
  and may need correction on first run.

## 6. Currency

Verified against Databricks documentation as of 2026-09. The docs are
actively changing — within this pass alone: Databricks Asset Bundles →
**Declarative Automation Bundles**, Mosaic AI Gateway → **Unity
Gateway**, and Genie's own pages disagreeing on the per-space table
ceiling (30 vs 50). Plan a re-verification pass roughly every two
quarters.
