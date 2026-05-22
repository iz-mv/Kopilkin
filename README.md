# Kopilkin

**Kopilkin** is a mobile-first personal finance web application with microservices, event-driven communication, caching, a routing layer, a recommendation service, and a local multi-agent AI assistant.

**Author:** Mubarakov Islam  
**Current architecture version:** Block 3 / updated C4 architecture  
**Main public entrypoint for the application backend:** `http://127.0.0.1:8088`

---

## 1. What the system does

Users can:

- register and log in;
- add income and expense transactions;
- view financial summaries;
- create and update savings goals;
- receive smart recommendations based on spending behavior;
- ask a local AI assistant to analyze expenses and give budgeting advice.

The project started as a simple MVP and was extended into a microservice-based system for the software engineering task block.

---

## 2. Current architecture summary

```text
Frontend :5500
   ↓
Nginx Load Balancer :8088
   ↓
API Gateway service, 2 Docker instances
   ↓
   ├── Auth Service        → PostgreSQL auth_db + Redis cache + Kafka events
   ├── Transaction Service → PostgreSQL transaction_db + Redis cache + Kafka events
   ├── Savings Service     → PostgreSQL savings_db + Kafka events
   ├── Agent Service       → Ollama + Mem0 + Qdrant + Langfuse + Prometheus metrics
   └── RecSys Service      → Transaction Service + Kafka events
```

Supporting infrastructure:

```text
PostgreSQL 16       core business data, logically separated databases
Kafka 3.8           event log and event-driven integration
Kafka UI            topic/message inspection
Redis 7             cache and rate limiter counters
Qdrant              vector memory for the AI assistant
Langfuse + Postgres LLM/agent traces
Nginx               load balancing between API Gateway instances
Ollama              local LLM runtime on the host machine
```

---

## 3. Services and ports

| Component | Port | Type | Responsibility |
|---|---:|---|---|
| `frontend` | `5500` | Static HTML/CSS/JS | Mobile-first user interface |
| `nginx-balancer` | `8088` | Nginx | Public backend entrypoint and load balancer |
| `api-gateway-1` | internal `8000` | FastAPI | Routing and Redis-based rate limiting |
| `api-gateway-2` | internal `8000` | FastAPI | Second gateway instance for load balancing |
| `auth-service` | `8001` | FastAPI | Registration, login, user profile |
| `transaction-service` | `8002` | FastAPI | Income/expense transactions and summaries |
| `savings-service` | `8003` | FastAPI | Savings goals |
| `agent-service` | `8004` | FastAPI | Multi-agent AI assistant |
| `recsys-service` | `8005` | FastAPI | Smart recommendations |
| `kafka-ui` | `8080` | Web UI | Kafka topic inspection |
| `postgres` | `5432` | PostgreSQL | `auth_db`, `transaction_db`, `savings_db` |
| `redis` | `6379` | Redis | Cache and rate limit counters |
| `qdrant` | `6333` | Vector DB | Long-term AI memory |
| `langfuse` | `3000` | Web UI | LLM/agent observability |

---

## 4. Block 3 requirements covered by the current architecture

### 5. Communication between microservices via Kafka / EDA

Kafka is used as the event backbone. Services publish business events after important state changes.

Current topics:

```text
user.registered
transaction.created
transaction.deleted
goal.created
goal.updated
recommendation.requested
recommendation.generated
```

Implemented producers:

- `auth-service/app/events.py`
- `transaction-service/app/events.py`
- `savings-service/app/events.py`
- `recsys-service/app/events.py`

The current implementation mainly uses Kafka as an event log / asynchronous integration base. This is enough to demonstrate Event-Driven Architecture, and it can later be extended with consumers for analytics, notifications, fraud checks, or materialized recommendation views.

### 6. Data layer

Core business data is stored in PostgreSQL using a logical database-per-service pattern:

| Service | Database | Main table |
|---|---|---|
| Auth Service | `auth_db` | `users` |
| Transaction Service | `transaction_db` | `transactions` |
| Savings Service | `savings_db` | `savings_goals` |

Additional storage:

| Component | Storage role |
|---|---|
| Qdrant | Vector memory for AI assistant |
| Redis | Cache and operational counters |
| Kafka | Event log |
| Langfuse DB | LLM trace storage |

### 7. Redis-like caching

Redis is used for:

```text
user:{user_id}                      user profile cache, TTL 300 seconds
summary:{user_id}                   transaction summary cache, TTL 60 seconds
rate_limit:{client_ip}:{window}     API Gateway rate limiter counter
```

### 8. Routing layer

The routing layer is implemented as:

```text
Frontend → Nginx Load Balancer → API Gateway replicas → Microservices
```

The API Gateway routes:

```text
/auth/*              → auth-service
/transactions/*      → transaction-service
/summary/*           → transaction-service
/goals/*             → savings-service
/agent/*             → agent-service
/recommendations/*   → recsys-service
```

Rate limiting is implemented inside the gateway with Redis counters.

### 9. C4 Diagrams

The updated C4 diagrams are stored in:

```text
Documentation/Block3-C4/
```

The package contains 7 updated diagrams:

1. C4 L1 — System Context
2. C4 L2 — Container Overview
3. C4 L2 — Data, Events, Routing and Cache View
4. C4 L3 — API Gateway Components
5. C4 L3 — Transaction Service Components
6. C4 L3 — AI Agent Service Components
7. C4 Dynamic — Add Transaction, Cache Invalidation, Kafka Event and Recommendation Refresh

Available formats:

```text
Documentation/Block3-C4/images/          PNG images for report/screenshots
Documentation/Block3-C4/graphviz_dot/    editable Graphviz DOT sources
Documentation/Block3-C4/mermaid/         Mermaid sources
Documentation/Block3-C4/structurizr/     Structurizr DSL workspace
```

---

## 5. Run locally

### 1. Start Ollama on the host machine

```bash
ollama serve
ollama pull gemma3:4b
ollama pull nomic-embed-text
```

### 2. Start Docker Compose

```bash
docker compose up --build
```

### 3. Start frontend

```bash
cd frontend
python -m http.server 5500
```

Open:

```text
http://127.0.0.1:5500/login.html
```

---

## 6. Useful local URLs

| URL | Purpose |
|---|---|
| `http://127.0.0.1:5500/login.html` | Frontend login page |
| `http://127.0.0.1:8088/health` | Load-balanced API Gateway health check |
| `http://127.0.0.1:8080` | Kafka UI |
| `http://127.0.0.1:3000` | Langfuse UI |
| `http://127.0.0.1:8004/metrics` | Agent Service Prometheus metrics |
| `http://127.0.0.1:6333/dashboard` | Qdrant dashboard, if enabled by image version |

---

## 7. Example API checks

### Gateway health through Nginx balancer

```bash
curl http://127.0.0.1:8088/health
```

Expected result should include one of the gateway instance names:

```json
{
  "service": "api-gateway",
  "instance": "api-gateway-1",
  "status": "running",
  "rate_limit_per_minute": 60
}
```

Repeated requests may show `api-gateway-1` and `api-gateway-2`, depending on balancing.

### Create a transaction through the gateway

```bash
curl -X POST http://127.0.0.1:8088/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo-user",
    "amount": 500,
    "category": "Groceries",
    "type": "expense",
    "description": "Test transaction",
    "date": "2026-05-22"
  }'
```

This should:

1. store the transaction in `transaction_db`;
2. publish `transaction.created` to Kafka;
3. invalidate `summary:demo-user` in Redis.

---
