# Ungoverned External LLM Access

> ⚠️ **ANTI-PATTERN**

**Category:** ML & AI Lifecycle

Notebooks, jobs, and applications call external LLM providers directly
with the provider's SDK and an embedded API key, bypassing governed
serving endpoints — so there are no rate limits, no guardrails, no
logged payloads, and no way to see what is being spent or sent.

## Why it happens

It is three lines of code and it works immediately. A data scientist
prototyping a summarization step does not need a platform team, an
endpoint, or a review — just a key, often one billed to a personal or
team account rather than through the platform at all. The prototype
then becomes the pipeline, and the key spreads by copy-paste into the
next notebook that needs it.

Nothing pushes back, because direct calls succeed. The absence of rate
limits, logging, and content controls is invisible until one of them is
needed, and by then the calls are scattered across a dozen places with
no inventory of where.

## Impact

- **No cost ceiling.** Per-token billing with no rate limit means a
  retry loop or an oversized batch job can spend a great deal very
  quickly, and the spend is discovered on an invoice rather than an
  alert.
- No usage visibility — requests, token consumption, and latency are
  not tracked anywhere queryable, so capacity planning and chargeback
  are impossible.
- No guardrails on content, so whatever a user types can reach an
  external provider, and whatever the provider returns can reach a
  user, unfiltered.
- **Data exposure.** Prompts frequently contain customer records
  assembled from governed tables; sending them directly to a third
  party moves that data outside Unity Catalog's audit boundary with no
  record that it happened.
- Keys in notebooks are readable by anyone with notebook access,
  survive in Git history, and cannot be rotated centrally.
- Provider lock-in by accretion: switching models or vendors means
  finding and editing every call site, which is the specific problem
  "centralized API governance" exists to prevent.
- No fallback, so a provider outage takes the application down.

## How to fix

1. Put every external model behind a serving endpoint and point
   application code at the endpoint, not the provider. See
   [`gateway-governance-for-llm-endpoints.md`](gateway-governance-for-llm-endpoints.md).
2. Move provider credentials into a secret scope held by the endpoint,
   then rotate every key that was ever pasted into a notebook —
   deleting the cell does not delete it from Git history.
3. Apply rate limits per endpoint and per principal to "manage capacity
   and cost," sized from observed usage.
4. Enable payload logging to Unity Catalog Delta tables, which is also
   what makes evaluation and debugging possible later. See
   [`genai-evaluation-and-human-feedback.md`](genai-evaluation-and-human-feedback.md).
5. Apply guardrails (service policies) wherever user-supplied content
   reaches a model or model output reaches a user.
6. Configure fallback destinations for anything user-facing so a
   provider outage degrades rather than fails.
7. Audit for direct calls as part of code review, so the governed path
   stays the only path.

## How to detect

By construction, ungoverned traffic is absent from the tables that
would describe it — `system.ai_gateway` covers gateway usage and
external model spend, and `system.serving.served_entities` lists
endpoints configured for external models, so a GenAI application with
real usage and no presence in either is the finding. The complementary
checks are outside system tables: scan repos and exported notebook
sources for provider SDK imports and API-key-shaped strings, and look
for direct provider charges on accounts outside the Databricks bill.

## References

- [Unity Gateway](https://docs.databricks.com/aws/en/ai-gateway/)
- [LLMOps workflows on Databricks](https://docs.databricks.com/aws/en/machine-learning/mlops/llmops)
- [Secret management](https://docs.databricks.com/aws/en/security/secrets/)
