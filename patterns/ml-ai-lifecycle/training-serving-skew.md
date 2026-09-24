# Training-Serving Skew

> ⚠️ **ANTI-PATTERN**

**Category:** ML & AI Lifecycle

Feature transformations are implemented twice — once in the training
pipeline, once in the application or scoring path — so the model is
served inputs computed differently from the ones it learned on.

## Why it happens

The two paths are written by different people, at different times, in
different languages, for different constraints. Training runs in a
Spark job over a historical table; serving runs in application code
against a request payload. Reimplementing "average order value over the
last 30 days" in the second context is the obvious thing to do, and it
is usually correct on the day it is written.

Then it drifts. Someone fixes a null-handling bug in the training
pipeline, or changes a window from 30 days to 28, and the serving copy
is not touched — because nothing links them. The model does not error;
it just gets quietly worse, and the degradation looks like data drift
rather than a bug.

A subtler form is leakage in the opposite direction: a training set
built by joining features at their *current* values rather than as of
the label's timestamp, so the model trains on information that did not
exist at prediction time and scores far better offline than it ever
will in production.

## Impact

- Silent accuracy loss with no error signal — the failure mode that
  takes longest to find because nothing is broken.
- Offline evaluation stops predicting online performance, which
  undermines every deployment decision made from it.
- Point-in-time leakage produces models that look excellent in
  validation and disappoint in production, often after the launch has
  been announced.
- Debugging is expensive: reconciling two implementations requires
  reading both carefully, and the discrepancy is usually in an edge
  case neither author documented.
- Every new feature doubles the surface, so the problem compounds with
  the model's usefulness.

## How to fix

1. Define features once in the Feature Store and let the model package
   its lookups, so at inference time "the model automatically looks up
   the latest feature values" and the Feature Store "handles all
   feature computation tasks." There is then only one implementation.
   See [`feature-store-for-consistent-features.md`](feature-store-for-consistent-features.md).
2. Prefer Feature Views for new work, where "Databricks creates and
   manages the feature pipelines" — including time-windowed
   aggregations, which are where hand-written skew concentrates.
3. Build training sets with **point-in-time joins**, so features
   reflect "feature values as of the time a label observation was
   recorded."
4. For real-time serving, back lookups with the Online Feature Store
   rather than recomputing features in application code.
5. Where a second implementation genuinely cannot be avoided, add a
   reconciliation test that scores the same inputs through both paths
   in CI and fails on divergence.
6. Use inference tables to compare the feature values actually received
   in production against their training distributions. See
   [`inference-tables-and-drift-monitoring.md`](inference-tables-and-drift-monitoring.md).

## How to detect

Lineage is the most direct signal: `system.access.table_lineage` shows
which tables feed training runs, and a serving path that reads
different tables — or no UC tables at all — indicates a separate
implementation. Models in `system.serving.served_entities` that accept
pre-computed feature vectors rather than entity keys are serving
features computed by someone else, which is the structural precondition
for skew. Where inference tables exist, comparing logged input
distributions against the training baseline via a data profiling
monitor surfaces the divergence quantitatively.

## References

- [Databricks Feature Store](https://docs.databricks.com/aws/en/machine-learning/feature-store/)
- [Data profiling](https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-quality-monitoring/data-profiling)
- [MLOps workflows on Databricks](https://docs.databricks.com/aws/en/machine-learning/mlops/mlops-workflow)
