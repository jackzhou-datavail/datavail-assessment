# Untracked Model Development

> ⚠️ **ANTI-PATTERN**

**Category:** ML & AI Lifecycle

Models are trained in notebooks with no MLflow run behind them — no
logged parameters, no metrics, no signature, no link to the data or the
code version — so the model in production cannot be reproduced,
compared, or explained.

## Why it happens

Training a model does not require tracking it, and during exploration
tracking feels like overhead on work that is mostly going to be thrown
away. The run that eventually becomes the production model is rarely
recognized as such at the time — it is just the one that happened to
score well before the deadline.

Partial tracking is the more common shape: metrics get logged because
someone wanted a comparison, but parameters, the input dataset version,
and the git commit do not. That is enough to rank candidates and not
nearly enough to rebuild one.

## Impact

- **Irreproducibility.** Months later, nobody can rebuild the model,
  which means nobody can safely retrain it either — the retraining
  script and the original training are different things.
- No basis for comparison. "The new model is better" becomes an
  assertion, because the old model's evaluation was never recorded on
  comparable terms.
- Missing signatures mean serving has no schema contract; malformed
  inputs fail at inference time instead of at deployment time.
- No lineage from model to training data, so questions about what data
  influenced a decision have no answer — the question regulators and
  incident reviews actually ask.
- Institutional memory sits in one person's notebook. When they leave,
  the model becomes unmaintainable rather than merely unowned.
- Experiments scattered under personal home folders are invisible to
  the rest of the team, so work is silently duplicated.

## How to fix

1. Turn on Databricks Autologging so parameters, metrics, files, and
   lineage are captured without anyone remembering to. See
   [`mlflow-experiment-tracking.md`](mlflow-experiment-tracking.md).
2. Log an input example with every model, so the signature is inferred
   automatically (MLflow 2.5.0 and above).
3. Move experiments out of personal folders into team-owned paths, and
   name them after the project rather than the person.
4. Tag runs with the git commit and environment so a run points back at
   reviewed code — which is also what makes
   [`deploy-code-not-models.md`](deploy-code-not-models.md) enforceable.
5. Make registration the gate: a model that is going to be served gets
   registered in Unity Catalog, and registration requires a run behind
   it.
6. Backfill selectively — the production models that matter get
   retrained under tracking rather than every historical experiment
   being reconstructed.

## How to detect

`system.mlflow.runs_latest` exposes `params`, `tags`, and
`aggregated_metrics` per run: runs with empty parameters or metrics
indicate manual, partial logging, and runs whose `tags` carry no git or
source-version entry indicate training outside a versioned pipeline.
`system.mlflow.experiments_latest` shows experiments concentrated under
one `created_by` or sitting in personal workspace paths. The sharpest
finding is the join gap — models served in
`system.serving.served_entities` with no traceable training run behind
them at all.

## References

- [MLflow on Databricks](https://docs.databricks.com/aws/en/mlflow/)
- [MLflow system tables](https://docs.databricks.com/aws/en/admin/system-tables/mlflow)
- [Manage model lifecycle in Unity Catalog](https://docs.databricks.com/aws/en/machine-learning/manage-model-lifecycle/)
