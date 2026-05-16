# Evaluation Plan

## LLM evaluation

The LLM was evaluated manually with the same financial prompt across three local models:

- `llama3.2:3b`
- `qwen2.5:3b`
- `gemma3:4b`

Evaluation criteria:

- Context understanding.
- Russian language quality.
- Usefulness of financial advice.
- Hallucination tendency.
- Ability to give structured output.
- Suitability for local execution.

## Agentic system evaluation

The agentic system is evaluated not only by the final answer, but also by the internal process.

| Metric | Meaning |
|---|---|
| Routing accuracy | Whether Orchestrator chooses Analyst/Advisor correctly |
| Tool success rate | Whether Transaction Service calls succeed |
| Groundedness | Whether answer uses real transaction numbers |
| Hallucination rate | Whether model invents non-existing data |
| Language consistency | Whether answer follows the user's language |
| Memory relevance | Whether retrieved memory is useful |
| Latency | How long `/chat` takes |
| Error rate | Percentage of failed chat requests |

## Implemented eval folder

The project contains:

```text
evals/test_cases.json
evals/run_evals.py
evals/README.md
```

The runner sends predefined prompts to `/chat` and saves a JSON report with pass/fail status and latency.

## Example test cases

- Russian saving advice about cafe and transport expenses.
- English spending analysis question.
- English saving advice question.
- Russian memory follow-up question.

## Continuous performance monitoring

For continuous monitoring, the service exposes `/metrics` and sends traces to Langfuse. In a production setup, Prometheus and Grafana could collect these metrics and trigger alerts.
