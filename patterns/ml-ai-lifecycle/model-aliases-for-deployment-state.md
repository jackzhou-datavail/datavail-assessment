# Model Aliases for Deployment State

**Category:** ML & AI Lifecycle

Which model version is live is expressed with a mutable **alias** —
`champion`, `challenger` — that serving endpoints and batch jobs
reference by name, so promoting a model does not require changing or
redeploying any workload code.

## Why it matters

"Model aliases allow you to assign a mutable, named reference to a
particular version of a registered model." The point is indirection: a
scoring job that loads `models:/prod.fraud.txn_scorer@champion` keeps
working when version 7 replaces version 6, and promotion becomes a
single metadata operation instead of a code change moving through
review.

That indirection is what makes safe rollout patterns cheap. A
`challenger` alias can point at a candidate while a traffic split sends
it a slice of production requests; rollback is re-pointing `champion`
at the previous version, which takes seconds and needs no deploy.

Aliases replace MLflow model *stages*, which Unity Catalog does not
carry forward — Databricks recommends abandoning stages entirely. The
reason is the one in
[`models-in-unity-catalog.md`](models-in-unity-catalog.md): the
catalog and schema already encode environment and governance, so
stages were encoding the same thing a second time, inconsistently.

## What good looks like

- A small, documented alias vocabulary used consistently across models
  — typically `champion` for what serves production traffic and
  `challenger` for the candidate being evaluated against it.
- No workload anywhere pins a numeric model version. Jobs, serving
  endpoints, and notebooks resolve models by alias.
- Alias reassignment is the promotion gate: it happens after validation
  passes, is performed by the deployment pipeline's service principal,
  and is therefore auditable.
- Rollback is defined in advance as "re-point the alias," and has been
  exercised at least once.
- Where a candidate is being compared live, the endpoint's traffic
  split routes a controlled percentage to the challenger rather than
  swapping wholesale. See
  [`production-serving-endpoint-configuration.md`](production-serving-endpoint-configuration.md).

## How to detect

Aliases are read per model through the MLflow client
(`get_model_version_by_alias`) or the UC Models API; the finding is
registered models with production consumers and no aliases defined.
`system.serving.served_entities` records what each endpoint serves — an
entity pinned to a specific version number rather than resolved by
alias is the concrete instance of this gap. Alias changes appear in
`system.access.audit` as model-version events, which also tells you
whether promotions are being made by a pipeline principal or by hand.

## References

- [Manage model lifecycle in Unity Catalog](https://docs.databricks.com/aws/en/machine-learning/manage-model-lifecycle/)
- [Model deployment patterns](https://docs.databricks.com/aws/en/machine-learning/mlops/deployment-patterns)
