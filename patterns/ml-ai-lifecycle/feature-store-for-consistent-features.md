# Feature Store for Consistent Features

**Category:** ML & AI Lifecycle

Features are defined once in Unity Catalog — as Feature Views or
feature tables — and both training and inference read them through the
Feature Store, so the transformation that produced a training feature
is the same one that produces it at serving time.

## Why it matters

Databricks Feature Store is "a central registry for the features used
in your AI and ML models," and registering features in Unity Catalog
brings "governance, lineage tracking, point-in-time joins, and
cross-workspace sharing."

The headline benefit is eliminating training-serving skew by
construction. Because the model packages its feature lookups, at
inference time "the model automatically looks up the latest feature
values" and the Feature Store "handles all feature computation tasks."
There is no second implementation of the feature logic in the serving
path, so there is nothing to drift. See
[`training-serving-skew.md`](training-serving-skew.md) for what happens
without it.

Point-in-time joins are the second benefit and the one that silently
decides whether a model is honest. A training set built with
point-in-time lookups reflects "feature values as of the time a label
observation was recorded," which is what prevents label leakage from
features computed after the fact.

## What good looks like

- **Feature Views** for most new projects — features are defined
  declaratively and "Databricks creates and manages the feature
  pipelines," including time-windowed aggregations, with Stream Feature
  Views for sub-second freshness.
- **Feature tables** where the project already uses Lakeflow or Spark
  Declarative Pipelines, or needs Delta Sharing, a third-party online
  store, or GA-only authoring — here the team owns the pipeline and
  writes to Delta tables with primary keys.
- Training sets built with point-in-time lookups against a label
  timestamp, not naive joins against current values.
- Real-time serving backed by the Online Feature Store for
  millisecond-latency lookups and on-demand computation.
- Feature tables owned and governed like any other UC asset, so
  consumers are discoverable through lineage rather than tribal
  knowledge.
- Unity Catalog enabled — it is a hard requirement for Feature Store.

## How to detect

Feature tables and Feature Views are UC objects, so they appear in
`system.information_schema.tables` alongside everything else; the
useful check is coverage rather than existence — how many production
models package feature lookups versus how many take a pre-joined
DataFrame. UC lineage (`system.access.table_lineage`) shows which
tables feed training runs and whether the serving path reads the same
ones. A feature table whose upstream pipeline has not run recently is
visible through `system.lakeflow.pipeline_update_timeline`.

## References

- [Databricks Feature Store](https://docs.databricks.com/aws/en/machine-learning/feature-store/)
- [MLOps workflows on Databricks](https://docs.databricks.com/aws/en/machine-learning/mlops/mlops-workflow)
