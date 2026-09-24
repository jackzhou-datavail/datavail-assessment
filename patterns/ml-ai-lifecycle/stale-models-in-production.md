# Stale Models in Production

> ⚠️ **ANTI-PATTERN**

**Category:** ML & AI Lifecycle

A model is trained once, deployed, and then left alone — no retraining
schedule, no monitoring to say when retraining is due, and often
upstream feature pipelines that stopped running months ago — so it
keeps serving confident predictions from a world that no longer exists.

## Why it happens

Deployment feels like the finish line. The project that funded the
model ends when it goes live, the data scientist moves to the next
problem, and nothing in the system asks for attention afterwards
because the endpoint stays green: latency is fine, error rate is zero,
and the only thing degrading is accuracy, which nothing is measuring.

The structural cause is usually the one described in
[`deploy-code-not-models.md`](deploy-code-not-models.md) — a model
artifact was carried into production rather than a training pipeline.
Retraining then requires a person to re-run a notebook they may no
longer have access to, so it never becomes routine. Databricks names
this drawback of the deploy-models pattern directly: "automated
retraining is challenging."

Stale *features* are the version of this that surprises teams most. The
model is fine; the pipeline computing its inputs failed six weeks ago,
and the model has been scoring against frozen values ever since.

## Impact

- Accuracy decays silently. Predictions stay well-formed, so downstream
  systems and business users keep trusting them.
- Decisions compound on bad inputs — pricing, risk scoring, and
  recommendation systems propagate the degradation into the data the
  next model will train on.
- A model serving stale features is worse than an outage, because an
  outage is noticed.
- Retraining after a long gap is a project rather than a job: the
  environment, dependencies, and data schema have all moved, and the
  original author is often gone.
- No baseline exists to quantify how much was lost, so the case for
  fixing it is hard to make.

## How to fix

1. Deploy the training pipeline, not the artifact, so retraining is a
   scheduled job running reviewed code — the pattern that makes
   "automated model retraining safer, since the training code is
   reviewed, tested, and approved for production."
2. Turn on inference tables and a data profiling monitor with the
   training data as the baseline, so drift becomes an alert. See
   [`inference-tables-and-drift-monitoring.md`](inference-tables-and-drift-monitoring.md).
3. Define the retraining trigger explicitly — scheduled, drift-based,
   or both — and write down what the alert means someone should do.
4. Monitor the upstream feature pipelines as production dependencies of
   the model, not as separate ETL, so their failure pages the model's
   owner.
5. Give every production model a named owning team, so there is someone
   for the alert to reach.
6. Promote retrained versions by re-pointing the alias, so the routine
   path is cheap enough to actually follow. See
   [`model-aliases-for-deployment-state.md`](model-aliases-for-deployment-state.md).

## How to detect

The clearest signal pairs recent serving traffic with old training:
`system.serving.served_entities` joined to
`system.serving.endpoint_usage` on `served_entity_id` shows endpoints
carrying current requests, while `system.mlflow.runs_latest`
(`start_time`, `experiment_id`) shows when the backing model was last
trained — a large gap between the two is the finding, ranked by request
volume. `system.mlflow.experiments_latest.update_time` gives the same
staleness view per experiment. For stale features, check the freshness
of the upstream pipelines in `system.lakeflow.pipeline_update_timeline`
and of the feature tables themselves against the endpoints that depend
on them.

## References

- [Model deployment patterns](https://docs.databricks.com/aws/en/machine-learning/mlops/deployment-patterns)
- [Inference tables for monitoring and debugging models](https://docs.databricks.com/aws/en/machine-learning/model-serving/inference-tables)
- [MLflow system tables](https://docs.databricks.com/aws/en/admin/system-tables/mlflow)
