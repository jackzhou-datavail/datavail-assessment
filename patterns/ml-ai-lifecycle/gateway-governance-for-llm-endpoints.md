# Gateway Governance for LLM Endpoints

**Category:** ML & AI Lifecycle

All LLM traffic — Databricks-hosted foundation models, external
providers, and custom agents — goes through governed serving endpoints
with rate limits, guardrails, payload logging, usage tracking, and
fallbacks, rather than direct SDK calls from application code.

## Why it matters

Centralized API governance is one of the six ways LLMOps differs from
MLOps, and Databricks frames the benefit as optionality: it "provides
the ability to easily switch between API providers." A team that calls
a provider SDK directly from twenty notebooks has twenty places to
change when the provider, the model, or the contract changes.

The gateway layer (Unity Gateway, formerly Mosaic AI Gateway) supplies
the controls that make LLM usage safe to hand to a wide audience:

- **Rate limits** "enforce consumption limits on model services and MCP
  services to manage capacity and cost" — the only real defence against
  a runaway loop billing per token.
- **Guardrails / service policies** "control how each request and
  response proceeds, based on its content and on who is making the
  call."
- **Payload logging** records "requests and responses to Unity Catalog
  Delta tables for monitoring and debugging."
- **Usage tracking** follows "requests, token usage, and latency ...
  using system tables."
- **Traffic splitting and fallbacks** "distribute requests across
  multiple model destinations and add failover to increase
  availability."

## What good looks like

- One endpoint per logical model capability, with application code
  pointing at the endpoint rather than at a provider.
- External model credentials held once, at the endpoint, in a secret
  scope — never distributed to callers. See
  [`ungoverned-external-llm-access.md`](ungoverned-external-llm-access.md).
- Rate limits set per endpoint and per principal, sized from observed
  usage, with the limit treated as a cost control rather than a
  formality.
- Guardrails applied where user-supplied content reaches a model, and
  reviewed as the application's exposure changes.
- Fallback destinations configured for anything user-facing, so a
  provider outage degrades rather than fails.
- Payload logging on, feeding the same evaluation and monitoring loop
  used for agents. See
  [`genai-evaluation-and-human-feedback.md`](genai-evaluation-and-human-feedback.md).

## How to detect

`system.ai_gateway` carries gateway usage and external model spend, and
is the direct source for requests, token consumption, and latency per
endpoint — endpoints with traffic but no rate limit configured are the
first finding. `system.serving.served_entities` reveals external model
endpoints and what they point at. Traffic that bypasses the gateway
entirely is, by definition, not in these tables: the complementary
check is a code and secret scan for provider SDK calls and API keys
outside endpoint configuration, plus egress or billing evidence of
direct provider usage.

## References

- [Unity Gateway](https://docs.databricks.com/aws/en/ai-gateway/)
- [LLMOps workflows on Databricks](https://docs.databricks.com/aws/en/machine-learning/mlops/llmops)
- [Model Serving](https://docs.databricks.com/aws/en/machine-learning/model-serving/)
