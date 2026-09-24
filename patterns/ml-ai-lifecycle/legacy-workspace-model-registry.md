# Legacy Workspace Model Registry and Stages

> ⚠️ **ANTI-PATTERN**

**Category:** ML & AI Lifecycle

Models are registered in the workspace-local MLflow model registry and
moved between `Staging` and `Production` stages, instead of being
registered in Unity Catalog and tracked with aliases.

## Why it happens

It is what every MLflow tutorial written before Unity Catalog teaches,
and it works well enough to never force a change. `transition_model_version_stage`
is one call; setting up a governed catalog, granting `CREATE MODEL`,
and rewriting loaders to resolve aliases is a project. So the workspace
registry stays, and each new workspace grows its own.

Stages in particular feel like the right abstraction the first time you
see them: a model *is* in staging or in production, so encoding that on
the model seems natural. The problem only appears once the same
registry serves more than one environment.

## Impact

- The registry is workspace-scoped, so models are invisible outside the
  workspace that created them. Sharing means copying, and copies drift.
- No unified governance: model permissions live in a different system
  from the grants on the tables the model was trained on, so access
  review has to be done twice and reconciled by hand.
- No lineage between model versions and the data that produced them,
  which is the piece auditors and incident responders actually ask for.
- Stages conflate two different things — governance environment and
  deployment status. Unity Catalog already expresses environment
  through the catalog and schema; a model in a `prod` catalog with
  stage `Staging` is ambiguous rather than informative.
- Stages are a fixed vocabulary, so patterns they do not anticipate —
  champion/challenger, shadow deployments, per-region variants — have
  nowhere to live.
- Unity Catalog does not carry stages forward, so the longer the delay,
  the more workloads have to be rewritten at once.

## How to fix

1. Register new models in Unity Catalog as `<catalog>.<schema>.<model>`
   and grant access with `GRANT ON FUNCTION`. See
   [`models-in-unity-catalog.md`](models-in-unity-catalog.md).
2. Replace stages with aliases — `champion`, `challenger` — and let
   catalog and schema carry the environment. Databricks recommends
   abandoning stages entirely.
3. Change consumers to resolve models by alias, which is also what
   makes future promotions code-free. See
   [`model-aliases-for-deployment-state.md`](model-aliases-for-deployment-state.md).
4. Migrate existing versions with `copy_model_version()`, which moves
   models between catalogs while preserving access controls.
5. Where possible, skip migration entirely: deploying "ML pipelines as
   code" retrains the model in the target environment and "eliminates
   the need to promote models across environments."
6. Ensure ML compute uses **Dedicated** access mode, which UC model
   workloads require — this is the step most likely to block a
   migration unexpectedly.

## How to detect

Compare what is served and scheduled against what exists in Unity
Catalog: `system.serving.served_entities` names each endpoint's entity,
and entities that do not resolve to a UC three-level name are being
served from the workspace registry. `SHOW MODELS IN <catalog>.<schema>`
enumerates the UC side. Training jobs in `system.lakeflow.jobs` that
produce models with no corresponding UC registration are the other
half. Stage transitions, where they still happen, appear in
`system.access.audit` as workspace model registry events.

## References

- [Manage model lifecycle in Unity Catalog](https://docs.databricks.com/aws/en/machine-learning/manage-model-lifecycle/)
- [MLOps workflows on Databricks](https://docs.databricks.com/aws/en/machine-learning/mlops/mlops-workflow)
- [Legacy Hive metastore usage](../unity-catalog-governance/legacy-hive-metastore-usage.md)
