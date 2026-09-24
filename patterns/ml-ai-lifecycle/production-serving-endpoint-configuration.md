# Production Serving Endpoint Configuration

**Category:** ML & AI Lifecycle

Production model serving endpoints are sized for guaranteed capacity
rather than minimum idle cost, owned by a long-lived service principal,
and roll out new versions through traffic splitting instead of
wholesale swaps.

## Why it matters

Model Serving gives "a unified interface to deploy, govern, and query
AI models for real-time and batch inference," and is built for
production scale — "over 25K queries per second with an overhead
latency of less than 50 ms." Reaching that in practice depends on a few
configuration choices that are easy to get wrong because the wrong
setting is the cheaper-looking one.

The clearest example is scale to zero. Databricks states it plainly:
"scale to zero is not recommended for production endpoints, as capacity
is not guaranteed when scaled to zero." It is an excellent default for
a development or demo endpoint and a poor one for anything with an SLA,
because the saving is paid for in cold-start latency and in capacity
that may not be there when traffic returns.

Ownership is the other quiet failure. Databricks recommends creating
endpoints with "long-lived service principals rather than personal
accounts, ensuring the creator maintains workspace membership
throughout the endpoint's lifecycle" — an endpoint created by someone
who later leaves is a production dependency on a disabled account.

## What good looks like

- Production endpoints keep warm capacity; scale to zero is reserved
  for dev, test, and intermittently used internal tools.
- Workload size chosen against the model's actual memory and latency
  profile — `CPU_MEDIUM` / `CPU_LARGE` for models needing more memory,
  GPU sizes (`GPU_SMALL` through `GPU_MEDIUM_8`) only where the model
  genuinely requires acceleration.
- Concurrency set explicitly with `min_provisioned_concurrency` and
  `max_provisioned_concurrency` (values must be multiples of 4) rather
  than left to defaults that were never load-tested.
- New versions rolled out via the endpoint's **traffic split** — a
  small percentage to the candidate, watched, then increased — which
  pairs naturally with a `challenger` alias.
- Endpoints created and managed by a service principal, through the
  bundle that deploys the rest of the project.
- Route optimization enabled for high-throughput endpoints.
- Inference tables on from the start, not added after the first
  incident. See
  [`inference-tables-and-drift-monitoring.md`](inference-tables-and-drift-monitoring.md).

## How to detect

`system.serving.served_entities` gives per-endpoint configuration and
the entity being served; joining it to
`system.serving.endpoint_usage` on `served_entity_id` gives request
volume, which is how you separate production endpoints from abandoned
experiments. The findings worth ranking: endpoints with sustained
traffic configured to scale to zero, endpoints whose creator is an
individual user, and endpoints serving a pinned version number rather
than an alias. Serving spend is attributable through the billable usage
system table for the model serving SKUs.

## References

- [Create custom model serving endpoints](https://docs.databricks.com/aws/en/machine-learning/model-serving/create-manage-serving-endpoints)
- [Model Serving](https://docs.databricks.com/aws/en/machine-learning/model-serving/)
- [Monitor model serving costs](https://docs.databricks.com/aws/en/admin/system-tables/model-serving-cost)
