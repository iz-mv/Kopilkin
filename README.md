# Kopilkin — Microservice Personal Finance Assistant

**Author:** Mubarakov Islam  
**Project type:** Semester project / Software Engineering  
**Main stack:** FastAPI, Docker Compose, PostgreSQL, Redis, Kafka, gRPC, MinIO, Nginx, Ollama, Qdrant, Langfuse, pytest  
**Main backend entrypoint:** `http://localhost:8088`  
**Frontend:** `http://localhost:5500`

---

## 1. Project Overview

**Kopilkin** is a personal finance assistant built as a microservice-based system. The application helps users track income and expenses, manage savings goals, receive recommendations, and ask a local AI assistant for financial analysis and budgeting advice.

The project was extended from a simple finance MVP into a distributed system that demonstrates the main course requirements:

- independent FastAPI microservices;
- API Gateway and Nginx load balancing;
- PostgreSQL data persistence;
- Redis caching, token blacklist, rate limiting, and worker locks;
- Kafka event-driven communication;
- gRPC communication between services;
- MinIO object storage for uploaded images;
- AI assistant with local LLM, memory, and observability;
- integration tests for real Docker Compose flows.

---

## 2. Main User Features

Users can:

- register and log in;
- upload a profile avatar;
- add income and expense transactions;
- view financial summaries;
- create savings goals;
- upload savings goal images;
- deposit money into savings goals;
- withdraw money from savings goals;
- receive automatic linked transactions for confirmed savings operations;
- receive heuristic recommendations based on real transaction history;
- ask an AI assistant to analyze expenses and give budgeting advice.

---

## 3. Architecture Summary

```text
User / Browser
    ↓
Frontend container :5500
    ↓ HTTP
Nginx Load Balancer :8088
    ↓
API Gateway replicas
    ├── api-gateway-1
    └── api-gateway-2
    ↓
Microservices:
    ├── Auth Service
    ├── Transaction Service
    ├── Savings Service
    ├── Worker Service
    ├── Recommendation Service
    └── Agent Service
```

Supporting infrastructure:

```text
PostgreSQL      persistent business data
Redis           cache, rate limiter, JWT blacklist, worker locks
Kafka           event-driven communication
Kafka UI        Kafka monitoring
MinIO           avatar and savings-goal image storage
Qdrant          vector memory for the AI assistant
Langfuse        LLM/agent observability
Ollama          local LLM runtime on the host machine
Nginx           load balancing for API Gateway replicas
```

---

## 4. Services and Ports

| Service | Port | Technology | Responsibility |
|---|---:|---|---|
| `frontend` | `5500` | Nginx + static HTML/CSS/JS | User interface |
| `nginx-balancer` | `8088` | Nginx | Public backend entrypoint and load balancing |
| `api-gateway-1` | internal `8000` | FastAPI | Routing, rate limiting, gRPC client calls |
| `api-gateway-2` | internal `8000` | FastAPI | Second gateway replica |
| `auth-service` | `8001` | FastAPI | Users, registration, login, JWT, avatars |
| `transaction-service` | `8002`, gRPC `50051` | FastAPI + gRPC | Transactions and financial summaries |
| `savings-service` | `8003`, gRPC `50052` | FastAPI + gRPC | Savings goals and goal operations |
| `worker-service` | internal | Python worker | Kafka consumer for goal operations |
| `agent-service` | `8004` | FastAPI + Ollama | Multi-agent AI assistant |
| `recsys-service` | `8005` | FastAPI | Recommendations from transaction data |
| `postgres` | `5432` | PostgreSQL 16 | `auth_db`, `transaction_db`, `savings_db` |
| `redis` | `6379` | Redis 7 | Cache, rate limiting, blacklist, locks |
| `kafka` | `9092` | Apache Kafka | Event streaming |
| `kafka-ui` | `8080` | Kafka UI | Kafka topic inspection |
| `minio` | `9000`, console `9001` | MinIO | Object storage for images |
| `qdrant` | `6333` | Qdrant | Vector memory |
| `langfuse` | `3000` | Langfuse | LLM traces and observability |

---

## 5. Databases and Storage

The project uses a logical database-per-service pattern inside PostgreSQL.

| Service | Database | Main tables |
|---|---|---|
| Auth Service | `auth_db` | `users` |
| Transaction Service | `transaction_db` | `transactions` |
| Savings Service | `savings_db` | `savings_goals`, `goal_operations` |

Additional storage:

| Component | Role |
|---|---|
| Redis | user cache, summary cache, rate limit counters, JWT blacklist, goal locks |
| Kafka | event log and asynchronous integration |
| MinIO | avatars and savings goal images |
| Qdrant | vector memory for AI assistant |
| Langfuse DB | traces and observability data |

---

## 6. Redis Usage

Redis is used for several independent responsibilities:

| Key pattern | Purpose |
|---|---|
| `user:{user_id}` | cached user profile |
| `summary:{user_id}` | cached transaction summary |
| `rate_limit:{client_ip}:{minute}` | API Gateway rate limiter counter |
| `jwt:blacklist:{jti}` | invalidated JWT token after logout |
| `lock:goal:{goal_id}` | worker lock for concurrent goal operation processing |

This demonstrates Redis as both a cache and an operational coordination component.

---

## 7. Kafka Events

Kafka is used for asynchronous communication and event logging.

Important topics/events:

| Topic | Producer | Consumer / Purpose |
|---|---|---|
| `user.registered` | Auth Service | event log / future analytics |
| `user.logged_in` | Auth Service | event log / future security analytics |
| `transaction.created` | Transaction Service | event log / recommendation refresh |
| `transaction.deleted` | Transaction Service | event log / cache invalidation history |
| `goal.created` | Savings Service | event log |
| `goal.image.updated` | Savings Service | event log |
| `goal.deleted` | Savings Service | event log |
| `goal.operation.created` | Savings Service | Worker Service processes deposit/withdraw operations |
| `recommendations.generated` | RecSys Service | event log |

The most important topic is `goal.operation.created`, because it drives the asynchronous savings-goal operation flow.

---

## 8. gRPC Communication

The project contains two meaningful gRPC flows.

### 8.1 Transaction Summary gRPC Flow

```text
Frontend
  ↓ HTTP
Nginx :8088
  ↓ HTTP
API Gateway
  ↓ gRPC
Transaction Service :50051
  ↓
PostgreSQL / Redis
```

Endpoint through API Gateway:

```http
GET /transactions/{user_id}/summary
```

The API Gateway calls `TransactionService.GetUserSummary` through gRPC and returns the financial summary to the client.

### 8.2 Savings Goal Operation gRPC Flow

```text
Frontend
  ↓ HTTP
Nginx :8088
  ↓ HTTP
API Gateway
  ↓ gRPC
Savings Service :50052
  ↓
Kafka topic: goal.operation.created
  ↓
Worker Service
  ↓
Savings DB + Transaction Service
```

Endpoint through API Gateway:

```http
POST /grpc/goals/{goal_id}/operations
```

The API Gateway calls `SavingsService.CreateGoalOperation` through gRPC. The Savings Service creates a `GoalOperation` with status `PENDING`, publishes a Kafka event, and then Worker Service processes it asynchronously.

---

## 9. Main Business Flow: Savings Goal Operation

This is the strongest end-to-end flow in the project.

```text
1. User clicks Deposit or Withdraw in the frontend.
2. Frontend sends an HTTP request to API Gateway.
3. API Gateway calls Savings Service through gRPC.
4. Savings Service creates GoalOperation with status PENDING.
5. Savings Service publishes Kafka event goal.operation.created.
6. Worker Service consumes the event.
7. Worker Service obtains Redis lock lock:goal:{goal_id}.
8. Worker changes operation status to PROCESSING.
9. Worker updates savings goal amount.
10. Worker creates linked transaction in Transaction Service.
11. Worker marks operation as CONFIRMED.
12. If withdrawal amount is too high, operation becomes FAILED and no transaction is created.
```

Operation statuses:

```text
PENDING → PROCESSING → CONFIRMED
PENDING → PROCESSING → FAILED
```

---

## 10. AI Assistant

The AI assistant is implemented in `agent-service`.

Main components:

- Orchestrator Agent;
- Router Agent;
- Analyst Agent;
- Advisor Agent;
- Mem0 memory adapter;
- Qdrant vector memory;
- Ollama local LLM runtime;
- Langfuse tracing;
- Prometheus-style `/metrics` endpoint.

The selected local model is:

```text
gemma3:4b
```

Embeddings model:

```text
nomic-embed-text
```

The assistant can analyze real transaction data and answer in the same language as the user.

---

## 11. Recommendation Service

`recsys-service` generates recommendations based on real transaction data from `transaction-service`.

Implemented approaches:

- heuristic recommendations;
- content-based recommendations;
- simple collaborative-style category vector logic.

Endpoint:

```http
GET /recommendations/{user_id}
```

---

## 12. Integration Tests

The project contains integration tests based on `pytest` and `requests`.

Run tests:

```bash
pip install -r requirements-test.txt
pytest tests -v
```

Expected result:

```text
12 passed
```

The tests verify:

- API Gateway and core service health;
- Agent Service health and metrics;
- Frontend and Kafka UI availability;
- registration, login, `/me`, logout;
- JWT blacklist in Redis;
- avatar upload to MinIO;
- transaction creation;
- transaction idempotency;
- gRPC transaction summary;
- savings goal image upload to MinIO;
- gRPC `CreateGoalOperation` flow;
- Kafka Worker processing;
- confirmed and failed operation statuses;
- automatic transaction creation after confirmed goal operation;
- recommendation generation.

Important note: ordinary CRUD calls in tests go directly to services to avoid exhausting the API Gateway rate limiter. Gateway is used where it is architecturally important: gRPC summary and gRPC goal operation flows.

---

## 13. How to Run Locally

### 1. Start Ollama on the host machine

```bash
ollama serve
ollama pull gemma3:4b
ollama pull nomic-embed-text
```

### 2. Start the full system

```bash
docker compose up -d --build
```

### 3. Check containers

```bash
docker compose ps
```

### 4. Open the application

```text
Frontend:      http://localhost:5500
API Gateway:   http://localhost:8088/health
Kafka UI:      http://localhost:8080
Langfuse:      http://localhost:3000
MinIO Console: http://localhost:9001
Qdrant:        http://localhost:6333/dashboard
```

---

## 14. Useful Demo Commands

### Gateway health

```bash
curl http://localhost:8088/health
```

### Kafka UI

```text
http://localhost:8080
```

### PostgreSQL examples

```bash
docker compose exec postgres psql -U kopilkin -d auth_db -c "SELECT id, email, name FROM users LIMIT 5;"
```

```bash
docker compose exec postgres psql -U kopilkin -d transaction_db -c "SELECT id, amount, category, type FROM transactions ORDER BY date DESC LIMIT 10;"
```

```bash
docker compose exec postgres psql -U kopilkin -d savings_db -c "SELECT id, title, current_amount, target_amount, status FROM savings_goals LIMIT 10;"
```

### Worker logs

```bash
docker compose logs --tail=100 worker-service
```

### Kafka topic inspection from container

```bash
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --list
```

---

## 15. Project Structure

```text
Kopilkin/
├── agent-service/          # AI assistant service
├── api-gateway/            # gateway, rate limiter, gRPC clients
├── auth-service/           # users, JWT, avatars
├── transaction-service/    # transactions, summaries, gRPC server
├── savings-service/        # goals, operations, images, gRPC server
├── worker-service/         # Kafka consumer for goal operations
├── recsys-service/         # recommendations
├── frontend/               # static web UI
├── infra/
│   ├── nginx/              # load balancer config
│   └── postgres/           # init databases
├── proto/                  # gRPC proto files
├── tests/                  # integration tests
├── Documentation/          # reports and C4 docs
├── docker-compose.yml
├── requirements-test.txt
└── README.md
```

## 16. Short Summary

**Kopilkin** is a microservice-based personal finance assistant. It uses FastAPI services, PostgreSQL databases, Redis, Kafka, gRPC, MinIO, Nginx load balancing, and a local AI assistant with Ollama, Qdrant and Langfuse. The strongest business flow is savings goal operations: the frontend sends a request to API Gateway, API Gateway calls Savings Service through gRPC, Savings Service publishes a Kafka event, Worker Service processes it asynchronously with Redis locking, updates the goal and creates a related transaction. The project is verified by integration tests with `12 passed`.
