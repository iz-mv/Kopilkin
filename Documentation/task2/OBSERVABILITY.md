# Observability

## Implemented stack

The project uses **Langfuse** for LLM/agent tracing and **Prometheus-compatible metrics** in the Agent Service.

## Langfuse tracing

Langfuse traces the main steps of the agent pipeline:

- `chat_endpoint`
- `orchestrator`
- `memory_search`
- `router_agent`
- `analyst_agent`
- `transaction_service_call`
- `advisor_agent`
- `memory_save`

This allows the developer to understand how a final answer was produced, which agent was called, where latency appeared, and whether memory/tool calls worked.

## Metrics

The Agent Service exposes `/metrics` for Prometheus-style monitoring.

Implemented metrics:

- `kopilkin_agent_chat_requests_total` - total chat requests.
- `kopilkin_agent_chat_errors_total` - failed chat requests.
- `kopilkin_agent_chat_latency_seconds` - latency histogram for `/chat`.

## Logs

The Agent Service uses structured logging with request start, request finish, duration, and error logs.

## Alerts

Alerting is not fully deployed in this MVP. For production, I would add Prometheus Alertmanager or Grafana alerts.

Recommended alert rules:

- High `/chat` error rate.
- High response latency.
- Transaction Service unavailable.
- Qdrant unavailable.
- Ollama unavailable.
- Langfuse unavailable.

## Why observability is important for agents

Agent systems are harder to debug than normal APIs because one user request may trigger multiple internal steps: memory search, routing, tool calls, LLM generation, and memory saving. Tracing helps show the real execution path instead of only the final text answer.
