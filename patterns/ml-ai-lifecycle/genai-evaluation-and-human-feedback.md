# GenAI Evaluation and Human Feedback

**Category:** ML & AI Lifecycle

Agent and LLM application quality is measured with traced runs, scored
by LLM judges and code-based checks against a versioned evaluation
dataset, with human feedback captured as a first-class input rather
than gathered ad hoc in Slack threads.

## Why it matters

The question an evaluation framework exists to answer is "whether your
agent is actually good — is the response correct, grounded, safe, and
complete?" Nothing about a GenAI application's outputs makes that
answerable by inspection, and no offline accuracy number substitutes
for it.

Databricks is unusually direct about the human half: "human feedback is
essential for evaluating and testing LLMs. You should incorporate user
feedback directly into the MLOps process," and "human feedback loops
are essential in most LLM applications," monitored "based on near
real-time streaming." That is a statement about system design, not
about diligence — if there is no path for a user's thumbs-down to reach
the evaluation set, the application cannot improve on the dimension
users actually care about.

The other structural difference from MLOps: in LLM work "the ML
artifacts packaged and promoted to production might be these
pipelines, rather than models." Evaluation therefore has to score the
pipeline end to end — retrieval, prompt, model, post-processing — not a
model in isolation.

## What good looks like

- MLflow Tracing on in development and production, so each run records
  its intermediate steps and unexpected behavior is debuggable rather
  than inferred.
- Scorers attached to traces: pre-built judges (Correctness,
  Completeness, Fluency) plus custom scorers registered for what the
  application specifically cares about, and code-based checks where the
  answer is deterministic.
- A versioned **evaluation dataset** used to compare agent versions, so
  "the new prompt is better" is a measured claim. `mlflow.genai.evaluate()`
  runs it programmatically in CI, not only in the UI.
- Production monitoring wired to automated scoring, so quality is
  tracked continuously rather than at release time.
- Human feedback captured in the application, attached to the trace it
  refers to, and fed back into the evaluation dataset.
- Prompts treated as versioned artifacts under prompt management, since
  prompt engineering is a first-class part of the pipeline.
- The same dev/staging/prod separation, Git version control, and MLflow
  management used for classical ML — LLMOps changes the artifacts, not
  the discipline.

## How to detect

Traces, evaluation runs, and their scores live in MLflow experiments,
so `system.mlflow.experiments_latest` and `system.mlflow.runs_latest`
show whether evaluation runs exist at all and when they last ran — an
agent serving production traffic whose experiment has no recent
evaluation runs is the finding. Cross-reference
`system.serving.served_entities` and `system.serving.endpoint_usage`
for agent endpoints carrying traffic, and `system.ai_gateway` for token
volume, then ask which of those have a corresponding evaluation
history. Whether human feedback is captured is an application-design
question, visible as feedback records attached to traces.

## References

- [Evaluate and improve](https://docs.databricks.com/aws/en/generative-ai/agent-evaluation/)
- [LLMOps workflows on Databricks](https://docs.databricks.com/aws/en/machine-learning/mlops/llmops)
- [MLflow on Databricks](https://docs.databricks.com/aws/en/mlflow/)
