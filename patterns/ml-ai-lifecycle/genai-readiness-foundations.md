# GenAI Readiness Foundations

**Category:** ML & AI Lifecycle

Before building GenAI applications, the platform has the foundations
they depend on: governed and documented data, a governed route to
models, retrieval over unstructured content, tracing and evaluation,
and a way to deploy — so the first agent isn't also the first time
each of these is figured out.

## Why it matters

GenAI projects fail on foundations more often than on models. An agent
answering questions over company data is only as good as the data it
can find and the descriptions attached to it; it's only as safe as the
access controls on that data; and it can only be improved if its
behavior is traced and evaluated. Teams that skip these ship a demo,
then stall when legal, security, or quality questions arrive.

Databricks' AI stack maps directly onto the readiness questions:
Databricks-hosted foundation models and external models for access;
**AI Gateway** for model endpoint governance; **AI Search** (vector and
hybrid search, formerly Vector Search) for retrieval; Knowledge
Assistant / custom agents, MCP servers, and Unity Catalog functions for
building agents; **MLflow Tracing** and **MLflow Evaluation** for
quality; Model Serving and Databricks Apps for deployment; and Unity
Catalog governing all of it. Product names are moving quickly — check
current docs.

## What good looks like

- **Data readiness:** the tables and documents an agent will use are in
  Unity Catalog, with table and column comments
  ([`../sql-analytics/documented-tables-and-columns.md`](../sql-analytics/documented-tables-and-columns.md)),
  sensitive data classified and masked
  ([`../unity-catalog-governance/automated-pii-classification.md`](../unity-catalog-governance/automated-pii-classification.md)),
  and unstructured content landed in UC volumes.
- **Model access governed:** all LLM traffic, internal and external,
  goes through serving endpoints with gateway controls — see
  [`gateway-governance-for-llm-endpoints.md`](gateway-governance-for-llm-endpoints.md)
  and the anti-pattern
  [`ungoverned-external-llm-access.md`](ungoverned-external-llm-access.md).
- **Retrieval ready:** at least one AI Search index built and synced
  from a governed source table, with an owner.
- **Quality loop:** tracing on from the first prototype, and evaluation
  datasets plus human feedback before production — see
  [`genai-evaluation-and-human-feedback.md`](genai-evaluation-and-human-feedback.md).
- **Path to production:** agents deployed through the same CI/CD and
  UC model registration as other models
  ([`cicd-for-ml-pipelines.md`](cicd-for-ml-pipelines.md)).
- **Cost visibility:** GenAI spend attributable by use case from day one.

## How to detect

`system.billing.usage.billing_origin_product` shows which GenAI products
are in use at all — `MODEL_SERVING`, `GENAI_API`, `AI_SEARCH`,
`AGENT_BRICKS`, `KNOWLEDGE_ASSISTANT`, `DATABRICKS_APPS`. `system.serving.served_entities`
and `system.serving.endpoint_usage` list endpoints and their traffic;
`system.mlflow.*` shows experiments with traces and evaluation runs.
Readiness gaps show as: GenAI spend with no tracing or evaluation
activity; external-model traffic not through gateway-enabled endpoints;
and candidate source tables with low comment coverage
(`system.information_schema.tables.comment` /
`columns.comment` null).

## Assessment items addressed

Items from the assessment checklist (`init_items` sheet) that this pattern helps answer.

- **AI/ML › Gen AI readiness** — *primary.* Are the foundations in place: documented governed data, gateway-governed model access, retrieval indexes, tracing / evaluation, and a CI/CD path to production?

## References

- [Databricks AI capabilities](https://docs.databricks.com/aws/en/generative-ai/guide/gen-ai-capabilities)
- [Concepts: AI on Databricks](https://docs.databricks.com/aws/en/generative-ai/guide/concepts/)
- [Databricks AI Search](https://docs.databricks.com/aws/en/vector-search/vector-search)
- [Billable usage system table reference](https://docs.databricks.com/aws/en/admin/system-tables/billing)
