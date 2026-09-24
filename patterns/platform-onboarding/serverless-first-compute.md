# Serverless-First Compute

**Category:** Platform Onboarding

Serverless compute is the default for new workloads — jobs, pipelines,
notebooks, SQL warehouses, and model serving — with classic compute
reserved for the cases where a specific network, compliance, or
runtime requirement rules serverless out.

## Why it matters

Databricks' compute guidance leads with serverless: it "requires no
configuration, is always available, and scales automatically with
workloads in seconds." For a team onboarding onto the platform, that
removes the single largest source of early operational mistakes —
cluster sizing, instance-type selection, auto-termination settings, and
idle spend — by not making them user-facing decisions at all.

The cost argument is the same argument. Serverless services "terminate
idle compute resources to save costs," which is exactly the discipline
that classic clusters require an administrator to enforce with policies
and that gets forgotten on the clusters created before those policies
existed.

## What good looks like

- New workloads default to serverless; choosing classic compute is a
  documented decision with a stated reason (private networking that
  serverless doesn't support, an unsupported runtime feature, a
  specific instance type requirement).
- Workspaces themselves are created as serverless workspaces, with
  classic reserved for specific network or compliance requirements.
- SQL workloads run on SQL warehouses rather than all-purpose compute —
  Photon is included, and the warehouse autoscales on query throughput,
  queue size, and predicted demand.
- Warehouse sizing follows the two-axis rule: **increase size (XS–XL)
  to make single queries faster; increase cluster count to handle more
  concurrent users** — roughly ten concurrent queries per cluster.
- Serverless usage still gets attributed: serverless usage policies
  apply tags that land in the billable-usage system table. See
  [`cost-attribution-tagging-and-budgets.md`](cost-attribution-tagging-and-budgets.md).
- Where classic compute is genuinely needed, it starts from a baseline
  configuration and is tuned against measured metrics rather than
  guessed at, and it always runs under a compute policy — see
  [`compute-policies-and-standard-sizing.md`](compute-policies-and-standard-sizing.md).

## How to detect

`system.billing.usage` carries the SKU per usage record, so serverless
versus classic DBU consumption is directly measurable — group spend by
`sku_name` and look at the classic share and which workloads produce
it. `system.compute.clusters` lists classic clusters with their
`cluster_source`, autoscaling bounds, and auto-termination minutes;
long-lived classic clusters with no auto-termination are the ones worth
asking about first. `data_collection/collect_data.py` does not currently
read either table — it reads `system.lakeflow.*` for job and pipeline
metadata, which tells you *what* runs but not what it runs on.

## References

- [Phase 8: Design compute strategy](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/compute)
- [Best practices for cost optimization](https://docs.databricks.com/aws/en/lakehouse-architecture/cost-optimization/best-practices)
- [Phase 2: Design workspace strategy](https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/workspace-strategy)
