# Inference Tables and Drift Monitoring

**Category:** ML & AI Lifecycle

Serving endpoints log every request and response to a Unity Catalog
Delta table, and a data profiling monitor runs over that table with the
model's training data as the baseline — so drift and quality
degradation raise an alert instead of being discovered by a business
user.

## Why it matters

An inference table "automatically captures incoming requests and
outgoing responses for a model serving endpoint and logs them as a
Unity Catalog Delta table" — request and response payloads, HTTP status
codes, execution time in milliseconds, timestamps, request ids, and the
endpoint and model version that served it, landing within about an hour.

That table is the foundation for three things that are otherwise
impossible:

- **Quality monitoring.** Data profiling over the inference table
  "automatically generates data and model quality dashboards" and
  supports alerts "to know when you need to retrain your model based on
  shifts in incoming data or reductions in model performance."
- **Production debugging.** Historical request/response data is the only
  way to reconstruct what a model actually saw when it produced a
  disputed output.
- **Retraining corpora.** Joining logged inferences with ground-truth
  labels as they arrive builds the next training set and closes the
  feedback loop.

## What good looks like

- **AI Gateway-enabled inference tables**, which Databricks now
  recommends over legacy inference tables, on custom model, foundation
  model, and agent serving endpoints. Existing legacy deployments have
  a documented migration path.
- A monitor configured with an **inference profile** whose baseline is
  "the data that was used to train or validate the model being
  profiled" — that choice is what makes an alert mean "the world has
  moved away from what this model learned."
- Both drift types watched deliberately: consecutive drift (this window
  versus the previous one) catches sudden breaks, baseline drift (this
  window versus training) catches slow decay.
- Alerts routed to the team that owns the model and tied to a defined
  action — retrain, investigate, or roll back the alias — not to a
  dashboard nobody opens.
- Monitors on the models that matter, sized deliberately; profiling
  every endpoint at maximum granularity has its own compute cost.

## How to detect

`system.serving.served_entities` lists what each endpoint serves and
joins to `system.serving.endpoint_usage` on `served_entity_id` for
request volume — an endpoint with real traffic and no configured
inference table is the primary finding. Enabled monitors and their
computed metrics surface in the data quality monitoring tables in
`system`; an inference table that exists but has no monitor attached is
the second, quieter finding. Alert definitions and evaluation history
live in `system.alert`.

## References

- [Inference tables for monitoring and debugging models](https://docs.databricks.com/aws/en/machine-learning/model-serving/inference-tables)
- [Data profiling](https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-quality-monitoring/data-profiling)
- [Data quality monitoring](https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-quality-monitoring/)
