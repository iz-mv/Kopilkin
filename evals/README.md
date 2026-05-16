# Kopilkin Agent Evaluations

This folder contains a small evaluation environment for the multi-agent system.

## What is evaluated

- Routing quality: whether the orchestrator selects analyst or advisor logic correctly.
- Grounding: whether the answer references real spending categories and numbers.
- Language consistency: whether the system answers in the user's language.
- Latency: how long a `/chat` request takes on local hardware.
- Memory stability: whether memory search/save works without breaking the chat flow.

## How to run

```bash
python evals/run_evals.py
```

The script sends predefined requests to the running `agent-service` and writes `last_eval_report.json`.
