-- Databricks Platform Assessment — result schema
--
-- Written to a DEDICATED catalog that is itself excluded from every
-- assessment scope, so the act of recording results never changes them.
-- Substitute ${results_catalog} (default: assessment) and
-- ${results_schema} (default: results) before executing.
--
-- Grain summary:
--   assessment_run   1 row per run
--   pattern_registry 1 row per pattern per run  (registry snapshot)
--   check_result     1 row per pattern per run  (the score)
--   check_finding    N rows per pattern per run (the evidence)
--   category_score   1 row per category per run (rollup)
--   assessment_score 1 row per run              (headline)

CREATE CATALOG IF NOT EXISTS ${results_catalog}
  COMMENT 'Databricks platform assessment results. Excluded from assessment scope by definition.';

CREATE SCHEMA IF NOT EXISTS ${results_catalog}.${results_schema}
  COMMENT 'Assessment run history, per-pattern conformance, and evidence.';

-- ---------------------------------------------------------------------
-- One row per assessment run.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ${results_catalog}.${results_schema}.assessment_run (
  run_id              STRING    COMMENT 'UUID for this run; foreign key for every other table',
  run_ts              TIMESTAMP COMMENT 'When the run started',
  status              STRING    COMMENT 'RUNNING | COMPLETE | FAILED',
  account_id          STRING    COMMENT 'Databricks account the run observed',
  workspace_id        STRING    COMMENT 'Workspace the collector executed in',
  metastore_id        STRING    COMMENT 'Unity Catalog metastore id',
  runner_principal    STRING    COMMENT 'Identity that executed the run (should be a service principal)',
  scope_catalogs      ARRAY<STRING> COMMENT 'Catalogs in assessment scope; empty = all except excluded',
  excluded_catalogs   ARRAY<STRING> COMMENT 'Catalogs deliberately out of scope, always including the results catalog',
  lookback_days       INT       COMMENT 'Observation window for activity-based checks',
  registry_version    STRING    COMMENT 'Version string of the pattern registry used',
  registry_checksum   STRING    COMMENT 'SHA-256 of registry.yaml, so a score can be tied to exact definitions',
  library_commit      STRING    COMMENT 'Git commit of the pattern library, when available',
  duration_seconds    DOUBLE    COMMENT 'Total wall-clock runtime',
  notes               STRING    COMMENT 'Free-text run annotation'
)
USING DELTA
COMMENT 'One row per assessment execution.';

-- ---------------------------------------------------------------------
-- Registry snapshot. Copied per run so historical scores stay
-- interpretable after weights or thresholds change.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ${results_catalog}.${results_schema}.pattern_registry (
  run_id           STRING  COMMENT 'Run this snapshot belongs to',
  pattern_id       STRING  COMMENT 'Stable id; matches the markdown filename stem',
  category         STRING  COMMENT 'Pattern category (directory name)',
  title            STRING  COMMENT 'Human-readable pattern title',
  is_anti_pattern  BOOLEAN COMMENT 'TRUE when the document describes something to avoid',
  severity         STRING  COMMENT 'CRITICAL | HIGH | MEDIUM | LOW',
  weight           DOUBLE  COMMENT 'Scoring weight derived from severity',
  check_tier       STRING  COMMENT 'SYSTEM_TABLE | TABLE_DETAIL | WORKSPACE_API | ACCOUNT_API | REPO_SCAN | MANUAL',
  implemented      BOOLEAN COMMENT 'TRUE when a collector check exists for this pattern',
  target_pct       DOUBLE  COMMENT 'Conformance at or above this scores GOOD',
  floor_pct        DOUBLE  COMMENT 'Conformance below this scores POOR; between floor and target is FAIR',
  applicability    STRING  COMMENT 'ALWAYS | IF_ML | IF_GENAI | IF_STREAMING | IF_SHARING | IF_MULTI_WORKSPACE',
  root_cause       STRING  COMMENT 'Grouping key so overlapping patterns roll up to one underlying problem',
  doc_path         STRING  COMMENT 'Relative path to the pattern markdown'
)
USING DELTA
COMMENT 'Per-run snapshot of pattern definitions, weights, and thresholds.';

-- ---------------------------------------------------------------------
-- The core result. Exactly one row per pattern per run.
--
-- status = MEASURED       -> conformance_pct is populated
--          NOT_AVAILABLE  -> data could not be read; reason says why
--          NOT_APPLICABLE -> nothing in scope to assess (denominator 0)
--          ERROR          -> the check failed; reason carries the error
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ${results_catalog}.${results_schema}.check_result (
  run_id           STRING    COMMENT 'Run this result belongs to',
  pattern_id       STRING    COMMENT 'Pattern being scored',
  category         STRING    COMMENT 'Denormalized for convenient rollup',
  status           STRING    COMMENT 'MEASURED | NOT_AVAILABLE | NOT_APPLICABLE | ERROR',
  conformance_pct  DOUBLE    COMMENT 'Percent of in-scope objects following the good practice; NULL unless MEASURED',
  grade            STRING    COMMENT 'GOOD | FAIR | POOR, from target_pct/floor_pct; NULL unless MEASURED',
  numerator        BIGINT    COMMENT 'Objects conforming to the practice',
  denominator      BIGINT    COMMENT 'Objects in scope for this check',
  unit             STRING    COMMENT 'What is being counted: tables, jobs, pipelines, endpoints, warehouses, dbus, queries',
  reason           STRING    COMMENT 'Why no measurement exists — the "no data available" explanation',
  evidence_query   STRING    COMMENT 'SQL actually executed, retained for auditability',
  finding_count    BIGINT    COMMENT 'Number of rows written to check_finding for this pattern',
  measured_at      TIMESTAMP COMMENT 'When this individual check completed'
)
USING DELTA
COMMENT 'Per-pattern conformance result, including explicit non-measurement.';

-- ---------------------------------------------------------------------
-- Evidence rows: the specific objects behind a non-conforming result.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ${results_catalog}.${results_schema}.check_finding (
  run_id        STRING    COMMENT 'Run this finding belongs to',
  pattern_id    STRING    COMMENT 'Pattern that produced the finding',
  object_type   STRING    COMMENT 'TABLE | JOB | PIPELINE | WAREHOUSE | CLUSTER | ENDPOINT | MODEL | EXPERIMENT | CATALOG | QUERY',
  object_id     STRING    COMMENT 'Stable identifier where one exists',
  object_name   STRING    COMMENT 'Human-readable name, fully qualified where applicable',
  workspace_id  STRING    COMMENT 'Workspace the object belongs to',
  owner         STRING    COMMENT 'Owner or run-as principal, when known',
  metric_name   STRING    COMMENT 'What was measured about this object',
  metric_value  DOUBLE    COMMENT 'The measured value',
  detail        STRING    COMMENT 'JSON blob with check-specific context',
  observed_at   TIMESTAMP COMMENT 'When the object was observed'
)
USING DELTA
COMMENT 'Object-level evidence supporting each check result.';

-- ---------------------------------------------------------------------
-- Rollups. Scores are computed over MEASURED checks only, and always
-- published alongside coverage so a high score on thin data is visible
-- as such.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ${results_catalog}.${results_schema}.category_score (
  run_id             STRING COMMENT 'Run this rollup belongs to',
  category           STRING COMMENT 'Pattern category',
  weighted_score     DOUBLE COMMENT 'Weighted mean conformance across MEASURED checks (0-100)',
  coverage_pct       DOUBLE COMMENT 'Measured weight divided by applicable weight (0-100)',
  weight_applicable  DOUBLE COMMENT 'Total weight of applicable patterns in this category',
  weight_measured    DOUBLE COMMENT 'Total weight actually measured',
  n_measured         INT    COMMENT 'Checks that produced a percentage',
  n_not_available    INT    COMMENT 'Checks with no obtainable data',
  n_not_applicable   INT    COMMENT 'Checks with nothing in scope',
  n_error            INT    COMMENT 'Checks that failed',
  n_poor             INT    COMMENT 'Measured checks graded POOR'
)
USING DELTA
COMMENT 'Per-category weighted score and measurement coverage.';

CREATE TABLE IF NOT EXISTS ${results_catalog}.${results_schema}.assessment_score (
  run_id             STRING COMMENT 'Run this headline belongs to',
  overall_score      DOUBLE COMMENT 'Weighted mean conformance across all MEASURED checks (0-100)',
  coverage_pct       DOUBLE COMMENT 'Share of applicable weight that could actually be measured (0-100)',
  confidence         STRING COMMENT 'HIGH (coverage >= 70) | MEDIUM (>= 40) | LOW (< 40)',
  weight_applicable  DOUBLE COMMENT 'Total applicable weight across the library',
  weight_measured    DOUBLE COMMENT 'Total measured weight',
  n_patterns         INT    COMMENT 'Patterns in the registry',
  n_measured         INT    COMMENT 'Checks that produced a percentage',
  n_not_available    INT    COMMENT 'Checks with no obtainable data',
  n_not_applicable   INT    COMMENT 'Checks with nothing in scope',
  n_error            INT    COMMENT 'Checks that failed',
  critical_gaps      INT    COMMENT 'CRITICAL-severity checks graded POOR — the headline remediation list'
)
USING DELTA
COMMENT 'One headline row per run: score, coverage, and confidence.';

-- ---------------------------------------------------------------------
-- Convenience view: the report most consumers want.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW ${results_catalog}.${results_schema}.v_latest_report AS
SELECT
  r.run_ts,
  reg.category,
  reg.pattern_id,
  reg.title,
  reg.severity,
  reg.check_tier,
  res.status,
  res.conformance_pct,
  res.grade,
  res.numerator,
  res.denominator,
  res.unit,
  res.reason,
  res.finding_count,
  reg.doc_path
FROM ${results_catalog}.${results_schema}.check_result res
JOIN ${results_catalog}.${results_schema}.pattern_registry reg
  ON reg.run_id = res.run_id AND reg.pattern_id = res.pattern_id
JOIN ${results_catalog}.${results_schema}.assessment_run r
  ON r.run_id = res.run_id
WHERE r.run_id = (
  SELECT run_id
  FROM ${results_catalog}.${results_schema}.assessment_run
  WHERE status = 'COMPLETE'
  ORDER BY run_ts DESC
  LIMIT 1
);
