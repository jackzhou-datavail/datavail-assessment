# Models in Unity Catalog

**Category:** ML & AI Lifecycle

Every model that anyone depends on is a registered model in Unity
Catalog, addressed as `<catalog>.<schema>.<model>`, governed by the
same privilege model as tables — not a file in DBFS, a pickle in a
repo, or an entry in the legacy workspace model registry.

## Why it matters

Registering models in Unity Catalog is what makes a model a governed
asset rather than a private artifact. It supplies "centralized
governance for models" with cross-workspace access and lineage
tracking — the same three-level namespace, the same grants, and the
same audit trail already used for data.

The namespace does real work here. The documentation is precise about
what it means: "the registered model's enclosing catalog, schema, and
registered model reflect its environment (`prod`) and associated
governance rules... but not its deployment status." Where a model lives
tells you who may touch it; *which version is live* is a separate
question answered by aliases. See
[`model-aliases-for-deployment-state.md`](model-aliases-for-deployment-state.md).

Lineage is the underrated benefit. A registered model links back to the
run that produced it and the tables that fed it, which is the only
practical way to answer "what would break if we changed this table" or
"what data went into the model that made this decision."

## What good looks like

- Models are `FUNCTION` securables: access is managed with `GRANT ON
  FUNCTION`, and registering requires `CREATE MODEL` (or `CREATE
  FUNCTION`) on the schema plus usage on the catalog and schema.
- Production models live in a production catalog whose grants reflect
  that — write access limited to the training job's service principal,
  read access to the consumers that serve or score with it.
- Every model version is logged with a **signature**. With MLflow 2.5.0
  and above, passing an input example to `mlflow.<flavor>.log_model`
  infers the signature automatically, so there is no reason for a
  version to lack one.
- Promotion across environments is handled by deploying "ML pipelines
  as code," which "eliminates the need to promote models across
  environments." Where a model genuinely must be copied between
  catalogs, `copy_model_version()` does it while preserving access
  controls.
- Compute running these workloads uses **Dedicated** access mode
  (formerly single user), which UC model workloads require.

## How to detect

Registered models are listed with `SHOW MODELS IN <catalog>.<schema>`
or the Unity Catalog Models API; the gap to look for is models being
served or scored that have no UC registration behind them.
`system.serving.served_entities` names the entity behind each serving
endpoint — an entity that is not a UC-registered model is the finding.
`system.access.audit` records registry events (`createModelVersion`,
`setModelVersionTag`) and who performed them. Model versions without a
signature are visible through the MLflow API per version rather than
through a system table.

## References

- [Manage model lifecycle in Unity Catalog](https://docs.databricks.com/aws/en/machine-learning/manage-model-lifecycle/)
- [MLflow on Databricks](https://docs.databricks.com/aws/en/mlflow/)
- [MLOps workflows on Databricks](https://docs.databricks.com/aws/en/machine-learning/mlops/mlops-workflow)
