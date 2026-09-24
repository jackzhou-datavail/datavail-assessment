# Deploy Code, Not Models

**Category:** ML & AI Lifecycle

Training code is promoted through development → staging → production,
and the model is retrained in each environment, rather than a model
artifact being trained once in dev and carried forward as a binary.

## Why it matters

Databricks recommends the "deploy code" approach "in most situations."
The reasoning is about which artifact carries the review: when code is
the thing promoted, "all code undergoes the same review and testing
processes, guaranteeing production models are trained on production
code." When a model binary is the thing promoted, the code that
produced it may never have been reviewed at production standards, and
the model may have been trained on whatever data dev happened to have.

Two consequences follow that matter most in regulated or
access-restricted environments:

- "In organizations where access to production data is restricted, this
  pattern allows the model to be trained on production data in the
  production environment" — the data never has to leave prod.
- "Automated model retraining is safer, since the training code is
  reviewed, tested, and approved for production." Retraining becomes a
  scheduled job rather than a human ritual.

## What good looks like

- Separate execution environments for dev, staging, and production,
  with explicitly defined transitions between them — not one workspace
  with naming conventions standing in for isolation.
- Data scientists have read-write access to development catalogs and
  **read-only** access to production data; ML engineers own the
  automated training, validation, deployment, and monitoring in prod.
- The training pipeline, the inference pipeline, and their supporting
  code all travel the same path, so nothing gets deployed out of band.
- Retraining is triggered on a schedule or by a monitoring signal, and
  runs the same reviewed code.
- The "deploy models" alternative is used deliberately and only where
  it fits: "model training is very expensive or hard to reproduce," all
  work happens in a single workspace, and there is no external repo or
  CI/CD process. That choice is documented, because it forecloses
  automated retraining.

## How to detect

`system.mlflow.runs_latest` carries `experiment_id`, `workspace_id`, and
`created_by` per run — a production model whose training runs all
originate from the development workspace, or from an individual's
identity rather than an automation principal, indicates the artifact
was carried forward rather than retrained in place. Cross-reference
registered model versions against training runs: a production model
version with no corresponding production-workspace run is the finding.
`system.access.audit` shows model registry events and where they came
from.

## References

- [MLOps workflows on Databricks](https://docs.databricks.com/aws/en/machine-learning/mlops/mlops-workflow)
- [Model deployment patterns](https://docs.databricks.com/aws/en/machine-learning/mlops/deployment-patterns)
- [MLflow system tables](https://docs.databricks.com/aws/en/admin/system-tables/mlflow)
