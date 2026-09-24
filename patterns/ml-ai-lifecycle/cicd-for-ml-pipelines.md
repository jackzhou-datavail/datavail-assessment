# CI/CD for ML Pipelines

**Category:** ML & AI Lifecycle

ML projects are deployed the way application code is — a repo, pull
requests that trigger tests in staging, and bundles that deploy
training, inference, and serving resources — with data, code, models,
and predictions all treated as things that need tracking.

## Why it matters

Databricks names four things CI/CD for ML has to cover, and the first
is the one traditional CI/CD misses: "training data, including data
quality, schema changes, and distribution changes," then input data
pipelines, then "code for training, validating, and serving models,"
then "model predictions and performance." An ML system can break
without a single line of code changing, so a pipeline that only watches
code is watching the wrong half.

MLOps Stacks is the packaged version of this. A default project
"includes an ML pipeline with CI/CD workflows to test and deploy
automated model training and batch inference jobs across development,
staging, and production Databricks workspaces" — which is the same
dev/staging/prod separation the MLOps workflow calls for, expressed as
something you can generate rather than assemble.

## What good looks like

- The documented flow: data scientists iterate in the development
  workspace and file PRs, which "trigger unit tests and integration
  tests in an isolated staging Databricks workspace." On merge to main,
  staging training and batch inference jobs pick up the latest code;
  a release branch then promotes to production.
- Declarative Automation Bundles (formerly Databricks Asset Bundles)
  deploy the ML resources — "jobs, registered models, and serving
  endpoints" — so the serving endpoint is versioned alongside the model
  that fills it.
- Git folders for code version control; the workspace is a view onto
  the repo, not a parallel copy.
- DataOps, ModelOps, and DevOps treated as one pipeline rather than
  three teams' concerns: Auto Loader and Delta for the data layer,
  MLflow for tracking and registry, Lakeflow Jobs for scheduling.
- Model validation is an automated gate, not a review meeting — the
  promotion step runs the evaluation and only then re-points the alias.
  See [`model-aliases-for-deployment-state.md`](model-aliases-for-deployment-state.md).
- Terraform reserved for the account- and workspace-level resources
  underneath all of this.

## How to detect

The reconciliation check is the real one: compare the training and
inference jobs in `system.lakeflow.jobs` against what the repos
declare. Two system-table proxies for "deployed by hand": jobs whose
creator is an individual rather than a deployment service principal,
and job or pipeline names lacking the `[<target>] <name>` prefix that
bundle deployment applies. In `system.mlflow.runs_latest`, runs whose
`tags` carry no git commit or source-version tag indicate training that
did not come from a versioned pipeline.

## References

- [How does Databricks support CI/CD for machine learning?](https://docs.databricks.com/aws/en/machine-learning/mlops/ci-cd-for-ml)
- [MLOps Stacks: model development process as code](https://docs.databricks.com/aws/en/machine-learning/mlops/mlops-stacks)
- [MLOps workflows on Databricks](https://docs.databricks.com/aws/en/machine-learning/mlops/mlops-workflow)
