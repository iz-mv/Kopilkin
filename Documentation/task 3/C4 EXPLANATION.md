# Task Block 3 - C4 Diagrams

**Project:** Kopilkin - Mobile-first personal finance application  
**Author:** Mubarakov Islam

---

## 1. Purpose of this document

This document explains the updated C4 architecture diagrams for the current version of Kopilkin.

The diagrams were updated because the project architecture changed significantly after the previous version. The system now includes:

- Kafka-based event publishing;
- PostgreSQL data persistence;
- Redis caching and rate limiting;
- an API Gateway;
- an Nginx Load Balancer;
- a recommendation service;
- a local multi-agent AI assistant with Qdrant and Langfuse;
- Docker Compose infrastructure.

The goal of the updated diagrams is to show the architecture as it actually exists in the current project archive, not only as a planned design.

---

## 2. Diagram set

The updated package contains 7 C4 diagrams.

| # | File | C4 level / type | Purpose |
|---:|---|---|---|
| 1 | `01_C4_L1_System_Context` | C4 Level 1 | Shows Kopilkin as one software system and its external users/systems |
| 2 | `02_C4_L2_Container_Overview` | C4 Level 2 | Shows all major deployable containers and infrastructure components |
| 3 | `03_C4_L2_Data_Events_Routing_View` | C4 Level 2 focused view | Shows Kafka, Redis, PostgreSQL, routing and data responsibilities |
| 4 | `04_C4_L3_API_Gateway_Components` | C4 Level 3 | Shows routing, proxying and Redis rate limiting inside the gateway |
| 5 | `05_C4_L3_Transaction_Service_Components` | C4 Level 3 | Shows transaction endpoints, SQL persistence, Redis cache and Kafka producer |
| 6 | `06_C4_L3_AI_Agent_Service_Components` | C4 Level 3 | Shows orchestrator, router, analyst, advisor, memory and observability components |
| 7 | `07_C4_Dynamic_Add_Transaction_Flow` | C4 Dynamic Diagram | Shows runtime flow for adding a transaction and refreshing recommendations |

---

## 3. Diagram 1 — C4 L1 System Context

**Purpose:** show the system from the outside.

Main elements:

- **Personal Finance User** uses Kopilkin to track income, expenses, goals, recommendations, and AI chat.
- **Developer / Instructor** can inspect Kafka UI, Langfuse traces, metrics, logs and diagrams during defense.
- **Kopilkin System** represents the whole application.
- **Ollama Runtime** is modeled as an external local LLM runtime because it runs on the host machine and is accessed from Docker through `host.docker.internal:11434`.

This diagram is useful at the beginning of a report or oral defense because it explains what the system is before showing containers.

---

## 4. Diagram 2 — C4 L2 Container Overview

**Purpose:** show the current microservice architecture.

Main containers:

- Frontend static web app;
- Nginx Load Balancer;
- API Gateway service with two Docker instances;
- Auth Service;
- Transaction Service;
- Savings Service;
- Agent Service;
- RecSys Service;
- PostgreSQL;
- Redis;
- Kafka;
- Kafka UI;
- Qdrant;
- Langfuse;
- Langfuse DB;
- Ollama Runtime.

Important architectural decisions shown in this diagram:

- Frontend no longer calls business services directly.
- All frontend backend traffic goes through `nginx-balancer:8088` and the API Gateway.
- The API Gateway routes requests to services by URL prefix.
- Core services use PostgreSQL for persistent data.
- Kafka is used for event publication.
- Redis is used for cache and rate limiting.
- AI memory is separated into Qdrant.

---

## 5. Diagram 3 — Data, Events, Routing and Cache View

**Purpose:** directly support Block 3 requirements 5–8.

This diagram focuses on:

- **Kafka / EDA:** event topics and producers;
- **Data:** PostgreSQL logical databases per service;
- **Redis:** cache keys and rate limiter counters;
- **Routing layer:** Nginx Load Balancer + API Gateway;
- **RecSys:** recommendation request/generation events.

This is the most useful diagram for explaining why requirements 5, 6, 7 and 8 are connected.

---

## 6. Diagram 4 — API Gateway Component Diagram

**Purpose:** show what happens inside `api-gateway`.

Main components:

- CORS Middleware;
- Redis Rate Limiter Middleware;
- Route Mapping Layer;
- HTTP Proxy Client;
- Health Endpoint;
- Service URL Configuration.

The gateway accepts public requests from Nginx and proxies them to internal services:

```text
/auth/*              → auth-service
/transactions/*      → transaction-service
/summary/*           → transaction-service
/goals/*             → savings-service
/agent/*             → agent-service
/recommendations/*   → recsys-service
```

The rate limiter uses Redis keys like:

```text
rate_limit:{client_ip}:{minute_window}
```

---

## 7. Diagram 5 — Transaction Service Component Diagram

**Purpose:** show the most important business service in detail.

Main components:

- Transaction API endpoints;
- Pydantic schemas;
- SQLAlchemy database session;
- Transaction model/table;
- Redis cache adapter;
- Kafka event publisher.

Important runtime behavior:

- `POST /transactions` writes a transaction to PostgreSQL.
- After commit, the service publishes `transaction.created` to Kafka.
- The service invalidates `summary:{user_id}` in Redis.
- `GET /transactions/{user_id}/summary` first checks Redis; on cache miss it calculates summary from PostgreSQL and stores it in Redis for 60 seconds.
- `DELETE /transactions/{transaction_id}` removes the row, publishes `transaction.deleted`, and invalidates the summary cache.

---

## 8. Diagram 6 — AI Agent Service Component Diagram

**Purpose:** preserve and update the multi-agent architecture from Task Block 2 inside the new Block 3 system.

Main components:

- `/chat` endpoint;
- metrics endpoint;
- Orchestrator Agent;
- Router Agent;
- Analyst Agent;
- Advisor Agent;
- Prompt and skill loader;
- Mem0 memory adapter;
- Langfuse decorators/tracing;
- Prometheus metrics.

External dependencies:

- Transaction Service for real financial data;
- Ollama Runtime for local LLM calls;
- Qdrant for vector memory;
- Langfuse for traces.

---

## 9. Diagram 7 — Dynamic Add Transaction Flow

**Purpose:** show an important runtime scenario instead of only static boxes.

Scenario:

```text
User adds a new transaction from the frontend.
```

Main steps:

1. User submits a transaction form in the frontend.
2. Frontend sends `POST /transactions` to Nginx on port `8088`.
3. Nginx balances the request to one of the API Gateway instances.
4. API Gateway checks Redis rate limit counter.
5. API Gateway proxies the request to Transaction Service.
6. Transaction Service stores the transaction in PostgreSQL.
7. Transaction Service publishes `transaction.created` to Kafka.
8. Transaction Service deletes `summary:{user_id}` from Redis.
9. Frontend refreshes summary and recommendations.
10. RecSys fetches transactions and publishes recommendation events.

This dynamic diagram proves that Kafka, Redis, routing, database persistence and RecSys are connected in one real user flow.

---

## 10. Why these 7 diagrams are enough

The requirement asks for seven updated and correct C4 diagrams. This set covers the system from different architectural levels:

- Level 1 explains the system boundary.
- Level 2 explains deployable containers.
- Focused Level 2 explains Block 3 infrastructure requirements.
- Level 3 diagrams explain important internal implementation details.
- Dynamic C4 diagram explains runtime behavior.

Together, the diagrams show not only what containers exist, but also how data, events, caching, routing and AI integration work in the current project.

---

## 11. Available formats

The diagrams are provided in several formats:

| Format | Folder | Use case |
|---|---|---|
| PNG | `images/` | Insert into report or presentation |
| Graphviz DOT | `graphviz_dot/` | Edit and re-render locally |
| Mermaid | `mermaid/` | Render in Markdown/GitHub/online Mermaid tools |
| Structurizr DSL | `structurizr/workspace.dsl` | Paste into Structurizr Playground |

---

## 12. Current limitations to mention in defense

The current system is correct for a local educational microservice project, but it is not production-ready yet.

Important limitations:

- Kafka currently has producers, but not real business consumers.
- Kafka is single-node in Docker Compose.
- PostgreSQL uses separate logical databases in one PostgreSQL container.
- API Gateway implements rate limiting, but not full authentication/authorization validation.
- The MVP still uses a fake access token and plain-text passwords.
- Ollama runs outside Docker on the host machine.
- RecSys is a rule-based and synthetic collaborative filtering educational implementation, not a trained production ML model.

These limitations should be presented as future improvements, not hidden.
