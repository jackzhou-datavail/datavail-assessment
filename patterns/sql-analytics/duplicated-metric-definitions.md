# Duplicated Metric Definitions

> ⚠️ **ANTI-PATTERN**

**Category:** SQL & Analytics

The same business metric is defined separately in each dashboard, BI
tool model, notebook, and Genie instruction — so "revenue" means
something slightly different depending on where you read it, and
meetings turn into reconciliation exercises.

## Why it happens

Each definition is created the fastest way available at the time. An
analyst building a dashboard writes the aggregate inline because
that takes a minute; a Power BI developer models it again because the
semantic layer lives in their tool; someone answering a one-off
question writes a third version in a notebook. All three are correct
on the day they are written.

Divergence comes later and quietly. The business decides that
cancelled orders no longer count. One definition is updated, the others
are not — because nothing connects them and nobody knows how many there
are. The versions were never wrong; they just stopped agreeing.

Traditional views do not solve it, because they "lock in aggregations
and groupings at creation time." A view per metric per grouping is a
combinatorial problem, so people stop creating views and go back to
inline SQL.

## Impact

- Numbers that disagree across dashboards, which costs more in
  credibility than in analyst time — once stakeholders learn the
  dashboards disagree, they stop trusting all of them.
- Reconciliation work becomes a standing tax on the analytics team,
  performed before every review cycle.
- Changing a definition means finding every copy, which nobody can
  enumerate, so definitions effectively become unchangeable.
- Genie and LLM-driven analytics inherit the ambiguity: with no single
  definition to anchor on, generated SQL picks one of the variants,
  and the answer is unpredictable rather than wrong in a visible way.
- Inline aggregates in dashboards also forgo materialization, so the
  duplication costs compute as well as trust.

## How to fix

1. Define each metric once as a Unity Catalog metric view, separating
   the measure from the fields used to group and filter it, so a single
   definition serves every slice. See
   [`metric-views-as-semantic-layer.md`](metric-views-as-semantic-layer.md).
2. Build complex measures through **composability** — referencing other
   measures "rather than rewriting their logic, which improves
   consistency, auditability, and maintenance."
3. Repoint every channel at the metric view: SQL editors, notebooks,
   dashboards, alerts, Genie agents, and external BI tools.
4. Retire the duplicates as you go rather than leaving them alongside
   the metric view, or you have added a definition rather than
   consolidated one.
5. Add agent metadata — display names, formats, synonyms — so the
   business vocabulary resolves to the governed definition.
6. Review metric view changes like code, since one edit moves every
   number downstream.

## How to detect

`system.query.history` is the practical detector: extract the aggregate
expressions in executed statements and look for near-identical
aggregations over the same fact tables issued by different dashboards,
users, or tools — clusters of similar-but-not-identical expressions are
duplicated definitions. `system.access.table_lineage` shows how many
distinct consumers read the same fact table directly rather than
through a metric view. The absence of metric views in the reporting
schemas of `system.information_schema` is the structural precondition.

## References

- [Unity Catalog metric views](https://docs.databricks.com/aws/en/uc-semantics/metric-views/)
- [Advanced techniques for metric views](https://docs.databricks.com/aws/en/business-semantics/metric-views/advanced-techniques)
- [Query history system table](https://docs.databricks.com/aws/en/admin/system-tables/query-history)
