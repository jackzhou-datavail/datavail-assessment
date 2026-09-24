# MLflow Experiment Tracking as the Default

**Category:** ML & AI Lifecycle

Every training run — including exploratory ones — is logged to an
MLflow experiment with its parameters, metrics, artifacts, and code
version, with autologging on so that recording is not something anyone
has to remember.

## Why it matters

MLflow lets teams "log and manage parameters, metrics, artifacts, and
code versions during machine learning training and agent development,"
and Databricks names "manage model development with MLflow" as one of
four core MLOps recommendations. The practical value shows up at three
moments: when a model needs to be reproduced months later, when two
candidates need to be compared on the same footing, and when someone
asks why the model in production was chosen over the alternatives.

Autologging is what makes this survive contact with real work.
Databricks Autologging "automatically captures model parameters,
metrics, files, and lineage," which means the record is complete even
for the run nobody expected to matter — and in practice the run that
matters is usually one of those.

MLflow 3 extends the same tracking spine to GenAI: tracing records the
intermediate steps of an agent, so debugging unexpected behavior works
the same way as inspecting a training run.

## What good looks like

- Autologging enabled so parameters, metrics, and lineage are captured
  without per-run instrumentation.
- Experiments organized to match the project structure and owned by a
  team, not scattered under individual users' home folders where they
  become invisible when that person leaves.
- Every logged model carries an input example, so its signature is
  inferred automatically.
- Runs tagged with the git commit and the bundle/environment they came
  from, so a run traces back to reviewed code. See
  [`cicd-for-ml-pipelines.md`](cicd-for-ml-pipelines.md).
- Experiment metadata is queried, not just browsed: the `system.mlflow`
  tables support "custom AI/BI dashboards, SQL alerts, or large-scale
  analytical queries" over runs and metrics.
- For GenAI work, MLflow Tracing is on in development and production so
  agent behavior is inspectable rather than inferred from outputs.

## How to detect

`system.mlflow.experiments_latest` (`experiment_id`, `workspace_id`,
`name`, `create_time`, `update_time`, `delete_time`) and
`system.mlflow.runs_latest` (`run_id`, `experiment_id`, `run_name`,
`status`, `params`, `tags`, `aggregated_metrics`, `start_time`,
`end_time`, `created_by`) are the direct sources. Useful signals:
experiments whose most recent run is far in the past; runs with empty
`params` or `aggregated_metrics`, which indicate logging was manual and
incomplete; experiments concentrated under a single `created_by` in a
personal path. `system.mlflow.run_metrics_history` gives metric
trajectories per run for deeper comparison.

## References

- [MLflow on Databricks](https://docs.databricks.com/aws/en/mlflow/)
- [MLflow system tables](https://docs.databricks.com/aws/en/admin/system-tables/mlflow)
- [Best practices for operational excellence](https://docs.databricks.com/aws/en/lakehouse-architecture/operational-excellence/best-practices)
