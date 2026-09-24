# Serverless SQL Warehouses, Sized Down Not Up

**Category:** SQL & Analytics

BI and interactive SQL run on serverless SQL warehouses, started at a
generous size and reduced based on measured behavior, with auto-stop
left near its default rather than disabled.

## Why it matters

Databricks recommends serverless warehouses for most workloads because
of Intelligent Workload Management — "a set of AI-powered features that
process queries quickly and cost-effectively without requiring you to
manage infrastructure." IWM predicts each incoming query's resource
needs, starts it immediately if capacity exists, queues it if not, and
provisions more clusters when wait times grow.

The sizing advice is counterintuitive and worth stating plainly:
**start with a single larger warehouse and size down**. Databricks'
reasoning is that "it is usually more efficient to size down if
necessary than to start small and scale up" — an undersized warehouse
spills to disk and queues, and both cost more in wall-clock time than
the larger instance would have cost in DBUs.

Auto-stop is what makes a generous size affordable. Serverless
warehouses "start and scale up in seconds, so both instant
availability and idle termination can be achieved."

## What good looks like

- Serverless for interactive and BI workloads; Pro/Classic only where a
  specific requirement rules serverless out.
- Two independent axes kept straight: **size (2X-Small through
  5X-Large) makes individual queries faster; cluster count handles more
  concurrent users.** Classic and Pro warehouses hold "a fixed limit of
  one cluster per 10 concurrent queries."
- Auto-stop left at the recommended default — **10 minutes for
  serverless**, **45 minutes for Pro and Classic** (minimum 10, or 5
  via the UI; the API allows as low as 1 minute for serverless).
- Sizing decisions made from two specific signals: disk **spill** in
  the query profile means size up; the **Peak Queued Queries** metric
  on the warehouse monitoring page means add clusters. Queues cap at
  1,000 queries per warehouse.
- Warehouses organized by workload and SLA — a dashboard-serving
  warehouse, an ad-hoc analyst warehouse — not one per team or per
  person.
- Warehouses defined in IaC with tags attached, so spend is
  attributable.

## How to detect

`system.compute.warehouses` gives a snapshot row per configuration
change: `warehouse_id`, `warehouse_name`, `warehouse_type` (CLASSIC /
PRO / SERVERLESS), `warehouse_size`, `change_time`, `delete_time`.
Findings worth ranking: classic/pro warehouses where serverless would
serve, oversized warehouses with low query volume, and a warehouse
count far exceeding the number of distinct workloads.
`system.query.history` (`statement_id`, `workspace_id`,
`executed_by_user_id`, `start_time`) gives per-warehouse query volume,
duration, and queue time — join it to the warehouse snapshot to see
which sizes are actually justified. Billable usage attributes the cost.

## References

- [SQL warehouse sizing, scaling, and queuing behavior](https://docs.databricks.com/aws/en/compute/sql-warehouse/warehouse-behavior)
- [Best practices for cost optimization](https://docs.databricks.com/aws/en/lakehouse-architecture/cost-optimization/best-practices)
- [Warehouses system table](https://docs.databricks.com/aws/en/admin/system-tables/warehouses)
