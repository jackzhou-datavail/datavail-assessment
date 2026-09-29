# Adoption Assessment

**Not implemented.** This folder is the home for the second assessment:
how much of the Databricks platform a workspace has actually adopted.

## How it differs from conformance

[Conformance](../conformance/) asks *how well is this workspace doing the things
it already does* — is bronze append-only, are jobs owned by service
principals, are columns documented. It scores conformance against
documented practice.

Adoption asks a different question: *which parts of the platform are in
use at all.* A workspace can score well on conformance while using a tenth
of what it pays for — no Lakeflow pipelines, no metric views, no
predictive optimization, no Delta Sharing, no serverless.

The two are independent. High conformance on a narrow footprint and low
conformance on a broad one are both real, and conflating them hides which
conversation to have.

## What it can reuse

Everything in [`../core/`](../core/): the executors, the preflight
probe, the MEASURED / NOT_AVAILABLE / NOT_APPLICABLE vocabulary, the
weighted scoring and coverage maths, the result schema, and the run
loop. An assessment supplies two things:

- **items** — scorable definitions with severity, weight, check tier,
  target and floor. See `src/datavail_assessment/conformance/registry.py` for the shape;
  adoption will want its own, since a pattern registry is not the right
  model for feature adoption.
- **checks** — a module exposing `CHECKS` and `PY_CHECKS` keyed by item
  id, each declaring the system tables and columns it needs so the
  preflight can turn anything missing into an honest NOT_AVAILABLE.

Then an entry point roughly the length of `src/datavail_assessment/conformance/run.py`.

## Starting points already identified

`system.billing.usage.billing_origin_product` is the single most useful
signal — it shows which Databricks products a workspace consumes at all,
with values including `MODEL_SERVING`, `GENAI_API`, `AI_SEARCH`,
`AGENT_BRICKS`, `KNOWLEDGE_ASSISTANT` and `DATABRICKS_APPS`. Two
existing conformance patterns already sketch this ground and are worth
reading first:

- [`platform-usage-profile`](../../patterns/platform-onboarding/platform-usage-profile.md)
- [`genai-readiness-foundations`](../../patterns/ml-ai-lifecycle/genai-readiness-foundations.md)

## Open question

Whether adoption writes to the same result tables as conformance (one
`assessment_run` history, distinguished by a kind column) or to its own.
Sharing them makes a combined dashboard trivial and mixes two different
meanings of "score" in one table. That decision should be made before
the first row is written.
