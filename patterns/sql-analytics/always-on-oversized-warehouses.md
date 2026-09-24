# Always-On, Oversized Warehouses

> ⚠️ **ANTI-PATTERN**

**Category:** SQL & Analytics

SQL warehouses run with auto-stop disabled or pushed out to hours,
sized far above what their queries need, and multiplied one per team or
per analyst — so the largest line on the analytics bill is compute that
was idle.

## Why it happens

Every step is a reasonable local decision. Someone waits eight seconds
for a classic warehouse to start, so they raise auto-stop to four hours
and the wait goes away. A dashboard feels slow, so the warehouse is
bumped from Small to Large and the complaint stops — nobody checks
whether the bottleneck was size. A team wants isolation from another
team's heavy queries, so they get their own warehouse, and the pattern
repeats.

None of it is revisited, because nothing forces a review. An idle
warehouse produces no errors, no alerts, and no complaints — only DBUs.
The oversizing in particular is self-concealing: a Large warehouse
running Small-sized queries performs flawlessly.

## Impact

- Idle spend, continuously. A warehouse with auto-stop disabled bills
  through nights and weekends whether or not anyone queries it.
- Oversizing multiplies that: the idle rate is proportional to size, so
  an oversized always-on warehouse is the most expensive way to serve a
  quiet dashboard.
- Warehouse sprawl fragments capacity — ten small per-team warehouses
  cannot absorb a burst that one shared warehouse with multiple
  clusters would have handled, so each team is both over-provisioned
  and under-served at peak.
- Untagged warehouses make all of it unattributable, so the cost lands
  on the platform team's budget rather than on the teams generating it.
  See
  [`../platform-onboarding/untagged-unmonitored-spend.md`](../platform-onboarding/untagged-unmonitored-spend.md).
- Classic and Pro warehouses kept alive for startup-latency reasons are
  solving a problem serverless does not have.

## How to fix

1. Move to serverless, where warehouses "start and scale up in seconds,
   so both instant availability and idle termination can be achieved" —
   this removes the reason auto-stop was disabled in the first place.
2. Restore auto-stop to the recommended defaults: **10 minutes for
   serverless**, **45 minutes for Pro and Classic**.
3. Right-size from evidence, not complaints. Check the query profile
   for disk spill before sizing up, and the Peak Queued Queries metric
   before adding clusters. See
   [`serverless-sql-warehouses.md`](serverless-sql-warehouses.md).
4. Consolidate per-team warehouses into per-workload warehouses, and
   let cluster count — not warehouse count — absorb concurrency.
5. Tag every warehouse and put a budget alert behind the analytics
   workload, so the next drift is caught in days rather than quarters.
6. Define warehouses in IaC so size and auto-stop are reviewed changes
   rather than a dropdown anyone can nudge.

## How to detect

`system.compute.warehouses` carries `warehouse_id`, `warehouse_name`,
`warehouse_type`, `warehouse_size`, and `change_time` per configuration
snapshot — that identifies oversized and classic/pro warehouses and,
through `change_time` history, when someone last changed a setting.
Join to `system.query.history` for query counts and durations per
warehouse: high uptime with low query volume is the idle finding, and
consistently short, non-spilling queries on a large warehouse is the
oversizing finding. Billable usage ranks both by actual cost, which is
the version that gets acted on.

## References

- [SQL warehouse sizing, scaling, and queuing behavior](https://docs.databricks.com/aws/en/compute/sql-warehouse/warehouse-behavior)
- [Best practices for cost optimization](https://docs.databricks.com/aws/en/lakehouse-architecture/cost-optimization/best-practices)
- [Warehouses system table](https://docs.databricks.com/aws/en/admin/system-tables/warehouses)
