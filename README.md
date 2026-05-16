# Kopilkin

Kopilkin is a mobile-first personal finance web application with a multi-agent AI assistant.

Users can:

- register and log in;
- add income and expense transactions;
- create savings goals;
- ask an AI assistant where their money goes and how to save money.

## Services

| Service | Port | Description |
|---|---:|---|
| frontend | 5500 | HTML/CSS/JS interface |
| auth-service | 8001 | registration, login, user profile |
| transaction-service | 8002 | income/expense transactions and summary |
| savings-service | 8003 | savings goals |
| agent-service | 8004 | multi-agent AI assistant |
| qdrant | 6333 | vector memory database |
| langfuse | 3000 | LLM/agent tracing UI |

## Multi-agent system

The AI assistant contains several integrated agents:

- **Orchestrator Agent** - coordinates the full flow.
- **Router Agent** - chooses analyst or advisor path.
- **Analyst Agent** - retrieves and analyzes real transaction data.
- **Advisor Agent** - gives saving advice based on Analyst output.

Flow:

```text
User -> Frontend -> Agent Service /chat
     -> Orchestrator -> Memory Search -> Router
     -> Analyst -> Advisor if needed
     -> Memory Save -> Response
```

## LLM

The local LLM engine is **Ollama**.

Tested models:

- `llama3.2:3b`
- `qwen2.5:3b`
- `gemma3:4b`

Selected model:

```text
gemma3:4b
```

Reason: best balance between Russian language quality, context understanding, usefulness, and low hallucination tendency in local tests.

## Memory

Long-term memory is implemented with:

- **Mem0** as the memory layer;
- **Qdrant** as the vector database;
- **Ollama `nomic-embed-text`** as the embedding model.

## Observability

Implemented:

- Langfuse traces for the full agent flow.
- Prometheus-compatible `/metrics` endpoint in agent-service.
- Structured logs in agent-service.

Important traced spans:

- `chat_endpoint`
- `orchestrator`
- `memory_search`
- `router_agent`
- `analyst_agent`
- `transaction_service_call`
- `advisor_agent`
- `memory_save`

## Run locally

### 1. Start Ollama locally

```bash
ollama serve
ollama pull gemma3:4b
ollama pull nomic-embed-text
```

### 2. Start Docker infrastructure and agent service

```bash
docker compose up --build
```

### 3. Start business services locally

In separate terminals:

```bash
cd auth-service
uvicorn app.main:app --reload --port 8001
```

```bash
cd transaction-service
uvicorn app.main:app --reload --port 8002
```

```bash
cd savings-service
uvicorn app.main:app --reload --port 8003
```

### 4. Start frontend

```bash
cd frontend
python -m http.server 5500
```

Open:

```text
http://127.0.0.1:5500/login.html
```

## Test agent manually

```bash
curl -X POST http://127.0.0.1:8004/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test-user","message":"Привет! Я трачу 5000 рублей в месяц на кафе и 3000 на транспорт. Что посоветуешь?"}'
```

## Run evaluations

```bash
python evals/run_evals.py
```

## Documentation for Task Block 2

Main files:

```text
Documentation/task2/TASK_BLOCK_2_MULTIAGENT_REPORT.md
Documentation/task2/AGENT_SPEC.md
Documentation/task2/LLM_COMPARISON.md
Documentation/task2/MEMORY_MANAGEMENT.md
Documentation/task2/OBSERVABILITY.md
Documentation/task2/EVALUATION_PLAN.md
Documentation/task2/ISOLATION_STRATEGY.md
Documentation/task2/FRAMEWORKS_CONSIDERED.md
Documentation/task2/DEFENSE_QA.md
```

Agent diagrams:

```text
Documentation/agent-diagrams/
```

## Known limitations

- Business services still use in-memory storage in the MVP.
- Full alerting is planned but not fully deployed.
- Secrets should be moved to `.env` or a secret manager in production.
- Local LLM response time depends on student hardware.
