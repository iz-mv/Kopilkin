# Task Block 2 - Multi-Agent System Report

**Project:** Kopilkin - personal finance web application with AI assistant  
**System:** Kopilkin Multi-Agent Financial Assistant  
**Author:** Mubarakov Islam

---

## 1. Project overview

Kopilkin is a mobile-first personal finance web application. Users can register, log in, add income and expense transactions, create savings goals, and ask an AI assistant questions about their spending.

For Task Block 2, I extended the project with a multi-agent AI system. The system helps the user understand where money goes and gives practical saving advice based on real transaction data from the application.

---

## 2. Agent specification

The Kopilkin agent system contains four logical agent components.

### Orchestrator Agent

The Orchestrator Agent coordinates the full request lifecycle. It receives the user message, searches memory, enriches the message with previous context, calls the router, runs the selected agent path, and saves the final interaction into memory.

### Router Agent

The Router Agent decides which path should process the request:

- `analyst` - for questions about numbers, totals, categories, statistics, and spending analysis.
- `advisor` - for questions about saving money, recommendations, and financial improvement.

### Analyst Agent

The Analyst Agent retrieves real financial data from Transaction Service and explains the user's spending patterns. It uses actual transaction numbers, such as total income, total expenses, and category breakdown.

### Advisor Agent

The Advisor Agent gives practical recommendations. It first receives the Analyst Agent output, then generates advice based on real numbers. This prevents generic advice and reduces hallucinations.

---

## 3. LLM engine selection

I considered several possible engines for local LLM execution:

| Engine | Advantages | Drawbacks | Decision |
|---|---|---|---|
| Ollama | Simple installation, local models, HTTP API, good for student hardware | Less optimized than vLLM for large-scale serving | Selected |
| llama.cpp | Very lightweight and efficient | More manual model management | Considered |
| vLLM | High-performance serving | Too heavy for this local MVP | Not selected |

I selected **Ollama** because it is easy to run locally, supports many lightweight open-source models, and provides an HTTP API that can be called from FastAPI services.

---

## 4. LLM model comparison

The instructor did not require a specific LLM model. The requirement was to test several lightweight local models and justify the final choice. I tested three models through Ollama using the same prompt:

```text
Привет! Я трачу 5000 рублей в месяц на кафе и 3000 на транспорт. Что посоветуешь?
```

| Criteria | llama3.2:3b | qwen2.5:3b | gemma3:4b |
|---|---|---|---|
| Context understanding | Good general topic understanding | Weak: assumed the user owns a cafe | Good: understood personal expenses |
| Russian language quality | Weak: mixed languages and unstable phrasing | Good Russian, but wrong context | Good Russian |
| Practical usefulness | Low | Low | High |
| Hallucination tendency | Present | Present | Minimal in this test |
| Final result | Not selected | Not selected | Selected |

**Final choice:** `gemma3:4b`.

Gemma 3 4B was selected because it gave the best balance between Russian language quality, context understanding, usefulness, and low hallucination tendency. It correctly understood that cafe and transport were personal expense categories.

---

## 5. Multi-agent architecture

The system is not a set of independent single agents. It is integrated through routing and chaining.

Main flow:

```text
User -> Frontend AI Chat -> Agent Service /chat
     -> Orchestrator
     -> Memory Search
     -> Router Agent
     -> Analyst Agent
     -> Advisor Agent if advice is needed
     -> Memory Save
     -> Response
```

The Advisor Agent depends on the Analyst Agent output. This means saving advice is grounded in real financial data.

---

## 6. Diagrams

The report includes new diagrams for the agent system:

- C4 L1 - Kopilkin with Multi-Agent AI Assistant.
- C4 L2 - Multi-Agent System Containers.
- C4 L3 - Agent Service Components.
- AI Chat Flow / Sequence Diagram.

These diagrams are stored in:

```text
Documentation/agent-diagrams/
```

---

## 7. Isolation strategy

The agent system is deployed in an isolated Docker-based environment.

Containerized components:

- `agent-service` - FastAPI multi-agent service.
- `qdrant` - vector database for memory.
- `langfuse` - LLM/agent tracing platform.
- `langfuse-db` - PostgreSQL database for Langfuse.

Ollama remains on the host machine and is accessed through `host.docker.internal:11434`. This is a practical hybrid setup because local model execution depends on the host model runtime and hardware resources.

| Option | Decision |
|---|---|
| No isolation | Rejected because dependencies are not reproducible |
| Python venv | Not enough because it does not isolate databases/services |
| Docker | Selected |
| Full VM | Too heavy for local student hardware |
| Kubernetes | Future improvement, not required for local MVP |

---

## 8. System prompts

System prompts are implemented in:

```text
agent-service/app/prompts/system_prompts.py
```

There are prompts for:

- Orchestrator Agent.
- Analyst Agent.
- Advisor Agent.

The prompts instruct the agents to use real financial data, avoid generic advice, and answer in the same language as the user.

---

## 9. Skills and semantic markdown files

Skills are defined as Markdown files:

```text
agent-service/app/skills/analyze_spending.md
agent-service/app/skills/give_advice.md
```

Semantic agent identity is defined in:

```text
agent-service/soul.md
```

The project also includes a skill loader:

```text
agent-service/app/skills/skill_loader.py
```

This loader reads the `.md` skill files and `soul.md` so they can be used inside the prompt context. This makes the Markdown files meaningful for the agent instead of being only documentation.

---

## 10. Memory management

The system uses **Mem0 + Qdrant + Ollama embeddings**.

- Mem0 manages memory search and memory saving.
- Qdrant stores vector representations of memories.
- Ollama `nomic-embed-text` creates embeddings.
- Memory is filtered by `user_id`.

### Why Mem0 was chosen

Kopilkin needs personalized long-term memory, not only retrieval from static documents. A classic RAG system is better for document question answering, while Kopilkin needs evolving user-specific memory across conversations.

### Memory types

- **Short-term memory:** current message, transaction summary, analyst result.
- **Long-term memory:** previous user interactions stored in Mem0/Qdrant.

### Limitations

- Vector memory may retrieve semantically similar but not logically relevant memories.
- There is no temporal knowledge graph yet.
- Memory deletion/export should be improved for production.

Future improvement: Graphiti-style temporal memory or a hybrid graph + vector memory system.

---

## 11. Evaluations

The project includes an `evals` folder:

```text
evals/test_cases.json
evals/run_evals.py
evals/README.md
```

Evaluation dimensions:

| Metric | Meaning |
|---|---|
| Routing accuracy | Correct Analyst/Advisor routing |
| Groundedness | Answer uses real transaction data |
| Hallucination rate | Model does not invent data |
| Language consistency | Response language matches user language |
| Tool success rate | Transaction Service call succeeds |
| Memory relevance | Retrieved memory is useful |
| Latency | `/chat` response time |
| Error rate | Failed request percentage |

The evaluation runner sends predefined requests to the running agent service and saves a JSON report.

---

## 12. Observability

The implemented observability stack includes **Langfuse** and Prometheus-compatible metrics.

### Langfuse traces

The system traces:

- `chat_endpoint`
- `orchestrator`
- `memory_search`
- `router_agent`
- `analyst_agent`
- `transaction_service_call`
- `advisor_agent`
- `memory_save`

This allows inspection of the complete agent execution path.

### Metrics

The Agent Service exposes:

```text
GET /metrics
```

Implemented metrics:

- `kopilkin_agent_chat_requests_total`
- `kopilkin_agent_chat_errors_total`
- `kopilkin_agent_chat_latency_seconds`

### Logs

The Agent Service logs request start, request finish, duration, and errors.

### Alerts

Full alerting is planned as a production improvement. Recommended alerts:

- High error rate.
- High latency.
- Ollama unavailable.
- Qdrant unavailable.
- Transaction Service unavailable.
- Langfuse unavailable.

---

## 13. Limitations

- Some business services still use in-memory storage for MVP demonstration.
- Secrets should be moved from Docker Compose to `.env` or a secret manager.
- Full alerting is not deployed yet.
- Automated evaluations are basic and should be expanded.
- Local LLM latency can be high on student hardware.

---

## 14. Conclusion

The Kopilkin project now includes a working multi-agent AI system with local LLM execution, Docker-based isolation, long-term memory, semantic skills, system prompts, LLM comparison, evaluation files, and observability through Langfuse and metrics. The selected model is `gemma3:4b` because it performed best in the local comparison. The current implementation is suitable for an MVP and oral defense, while production improvements would include stronger alerting, persistent databases for all services, stronger secret management, and more advanced memory evaluation.
