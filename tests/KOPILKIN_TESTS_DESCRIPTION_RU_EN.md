# Kopilkin Integration Tests — Description / Описание тестов

**Project:** Kopilkin  
**Test type:** Integration tests  
**Framework:** pytest + requests  
**Expected result:** `12 passed`

---

## RU — Общее описание

Эти тесты проверяют не отдельные функции в изоляции, а работу проекта как полноценной микросервисной системы. Тесты отправляют реальные HTTP-запросы в запущенные Docker-сервисы и проверяют основные бизнес-сценарии проекта Kopilkin.

Важная идея версии v2: обычные CRUD-запросы отправляются напрямую в сервисы, чтобы не забивать rate limiter API Gateway. Через API Gateway тестируются только те сценарии, где он действительно важен: gRPC-вызовы к `transaction-service` и `savings-service`.

Проверяются следующие части проекта:

- API Gateway and Nginx availability
- Core FastAPI microservices
- JWT authentication
- Redis token blacklist after logout
- MinIO avatar upload
- MinIO savings goal image upload
- Transaction creation
- Transaction idempotency
- gRPC `GetUserSummary` flow
- gRPC `CreateGoalOperation` flow
- Kafka event publishing
- Worker Service asynchronous processing
- Goal operation status transitions
- Automatic transaction creation after confirmed goal operation
- Failed withdraw business validation
- Recommendation service
- Agent service health and metrics

---

## EN — General Description

These tests are integration tests. They do not test isolated functions only; instead, they verify the project as a running microservice-based system. The tests send real HTTP requests to Docker services and validate the main business flows of Kopilkin.

The important idea in v2 is that ordinary CRUD requests go directly to services to avoid exhausting the API Gateway rate limiter. The API Gateway is used only for scenarios where it is actually required: gRPC calls to `transaction-service` and `savings-service`.

The tests cover:

- API Gateway and Nginx availability
- Core FastAPI microservices
- JWT authentication
- Redis token blacklist after logout
- MinIO avatar upload
- MinIO savings goal image upload
- Transaction creation
- Transaction idempotency
- gRPC `GetUserSummary` flow
- gRPC `CreateGoalOperation` flow
- Kafka event publishing
- Worker Service asynchronous processing
- Goal operation status transitions
- Automatic transaction creation after confirmed goal operation
- Failed withdraw business validation
- Recommendation service
- Agent service health and metrics

---

# Test Files / Файлы тестов

```text
Kopilkin/
├── tests/
│   ├── conftest.py
│   ├── test_01_health.py
│   ├── test_02_auth_jwt_and_minio.py
│   ├── test_03_transactions_grpc_summary.py
│   ├── test_04_savings_goal_grpc_worker.py
│   └── test_05_recommendations.py
├── pytest.ini
├── requirements-test.txt
└── RUN_TESTS_NOW.md
```

---

# RU — Подробное описание каждого файла и теста

## `conftest.py`

Это общий helper-файл для всех тестов. Сам по себе он не является тестом, но содержит общие настройки, fixtures и utility-функции.

### Что делает `conftest.py`

- Хранит URL всех сервисов:
  - `GATEWAY_URL` — API Gateway через Nginx
  - `AUTH_URL` — auth-service
  - `TRANSACTION_URL` — transaction-service
  - `SAVINGS_URL` — savings-service
  - `AGENT_URL` — agent-service
  - `RECSYS_URL` — recsys-service
  - `FRONTEND_URL` — frontend
  - `KAFKA_UI_URL` — Kafka UI
- Создаёт уникальные email для тестовых пользователей.
- Создаёт общий `requests.Session`.
- Содержит helper `assert_status()` для проверки HTTP-статусов.
- Содержит helper `wait_for()` для ожидания асинхронных операций worker-service.
- Содержит `TINY_PNG_BYTES`, маленькую PNG-картинку для тестирования upload в MinIO.
- Содержит fixture `registered_user`, которая создаёт тестового пользователя и логинит его.
- Содержит helper-функции:
  - `create_transaction()`
  - `create_goal()`
  - `get_goal_by_id()`
  - `get_goal_operation()`
  - `get_user_transactions()`
- Перед запуском тестов очищает только Redis-ключи `rate_limit:*`, чтобы повторные запуски тестов не падали из-за HTTP `429 Rate limit exceeded`.

### Почему CRUD-запросы идут напрямую в сервисы

В проекте API Gateway имеет Redis rate limiter. Если все тесты гонять через gateway, повторный запуск тестов может быстро превысить лимит `60/min`. Поэтому обычные операции вроде регистрации, создания транзакции или создания цели идут напрямую в соответствующие сервисы. А gateway используется там, где он действительно нужен для демонстрации gRPC.

---

## `test_01_health.py`

Этот файл проверяет, что основные сервисы проекта запущены и доступны.

### `test_gateway_health`

Проверяет endpoint:

```text
GET http://localhost:8088/health
```

Ожидаемый результат:

```json
{
  "service": "api-gateway",
  "status": "running"
}
```

Что доказывает:

- API Gateway работает.
- Nginx-balancer доступен на `localhost:8088`.
- Базовая маршрутизация проекта работает.

---

### `test_core_services_are_running`

Проверяет root endpoints основных микросервисов:

```text
GET auth-service /
GET transaction-service /
GET savings-service /
GET recsys-service /
```

Что доказывает:

- `auth-service` запущен.
- `transaction-service` запущен.
- `savings-service` запущен.
- `recsys-service` запущен.
- Основные FastAPI-сервисы проекта доступны.

---

### `test_agent_health_and_metrics_are_available`

Проверяет:

```text
GET agent-service /health
GET agent-service /metrics
```

Что доказывает:

- AI service живой.
- Agent service отдаёт health-check.
- Agent service отдаёт Prometheus-style metrics.
- В `/metrics` есть метрика `kopilkin_agent_chat_requests_total`.

Важно: сам AI chat здесь не тестируется специально, потому что он зависит от Ollama/local LLM и может долго отвечать. Для защиты достаточно показать, что сервис живой и метрики доступны.

---

### `test_frontend_and_kafka_ui_are_reachable`

Проверяет:

```text
GET frontend
GET Kafka UI
```

Что доказывает:

- Frontend доступен.
- Kafka UI доступен.
- Kafka monitoring interface поднят.

Особенность: Kafka UI иногда возвращает `406 Not Acceptable` на root page из-за content negotiation. Для этого теста это считается нормальным, потому что статус `406` всё равно доказывает, что Kafka UI отвечает и сервис живой.

---

## `test_02_auth_jwt_and_minio.py`

Этот файл проверяет authentication flow, JWT, Redis blacklist и загрузку аватара в MinIO.

### `test_register_login_me_logout_blacklist_flow`

Шаги теста:

1. Создаёт нового пользователя через `auth-service /register`.
2. Проверяет, что в ответе есть email пользователя.
3. Проверяет, что в ответе нет `password` и `password_hash`.
4. Логинит пользователя через `/login`.
5. Получает JWT `access_token`.
6. Проверяет `/me` с Bearer token.
7. Выполняет `/logout`.
8. Снова пробует вызвать `/me` с тем же токеном.
9. Ожидает HTTP `401`.

Что доказывает:

- Регистрация работает.
- Пароль не возвращается клиенту.
- Логин работает.
- JWT token создаётся.
- Protected endpoint `/me` работает.
- Logout добавляет token в Redis blacklist.
- После logout старый token больше не работает.

---

### `test_avatar_upload_uses_minio_and_updates_profile`

Шаги теста:

1. Создаёт и логинит тестового пользователя.
2. Загружает маленький PNG-файл в endpoint `/me/avatar`.
3. Проверяет, что ответ содержит `avatar_url`.
4. Проверяет, что в URL есть `kopilkin-files` и `avatars`.

Что доказывает:

- Avatar upload работает.
- Auth service интегрирован с MinIO.
- В базе хранится ссылка на файл, а сам файл хранится в MinIO.

---

## `test_03_transactions_grpc_summary.py`

Этот файл проверяет transaction-service и gRPC flow между API Gateway и transaction-service.

### `test_transaction_creation_and_grpc_summary`

Шаги теста:

1. Создаёт тестового пользователя.
2. Создаёт income transaction.
3. Создаёт две expense transactions.
4. Получает список transactions пользователя.
5. Проверяет, что транзакции реально созданы.
6. Вызывает через API Gateway:

```text
GET /transactions/{user_id}/summary
```

7. Проверяет, что summary содержит:

```json
"transport": "grpc"
```

8. Проверяет суммы:

- total income больше или равен 1000
- total expense больше или равен 400
- balance больше или равен 600

Что доказывает:

- Transaction creation работает.
- Transaction-service сохраняет данные.
- API Gateway вызывает transaction-service через gRPC.
- gRPC `GetUserSummary` flow работает.
- Summary возвращает правильные финансовые значения.

---

### `test_transaction_create_is_idempotent_when_id_is_reused`

Шаги теста:

1. Создаёт transaction с заранее заданным `id`.
2. Повторно отправляет create request с тем же `id`.
3. Проверяет, что оба ответа содержат один и тот же transaction id.
4. Получает список transactions пользователя.
5. Проверяет, что transaction с этим id существует только один раз.

Что доказывает:

- Idempotency работает.
- Повторный запрос с тем же id не создаёт дубль.
- Это особенно важно для worker-service, потому что worker создаёт linked transaction с id вида:

```text
tx-goal-operation-{operation_id}
```

Если worker случайно повторно обработает Kafka event, дубликат transaction не должен появиться.

---

## `test_04_savings_goal_grpc_worker.py`

Это самый важный файл тестов, потому что он проверяет главный бизнес-flow проекта: savings goal operation через gRPC, Kafka и worker-service.

### `test_goal_image_upload_uses_minio`

Шаги теста:

1. Создаёт тестового пользователя.
2. Создаёт savings goal.
3. Загружает PNG-картинку для goal.
4. Проверяет, что response содержит `image_url`.
5. Проверяет, что URL содержит `kopilkin-files` и `goals`.

Что доказывает:

- Savings goal creation работает.
- Goal image upload работает.
- Savings-service интегрирован с MinIO.
- Картинки целей хранятся в MinIO.

---

### `test_create_goal_operation_via_grpc_then_worker_confirms_and_creates_transaction`

Это главный integration test проекта.

Шаги теста:

1. Создаёт тестового пользователя.
2. Создаёт savings goal.
3. Отправляет deposit operation через API Gateway:

```text
POST /grpc/goals/{goal_id}/operations
```

Payload:

```json
{
  "user_id": "...",
  "operation_type": "DEPOSIT",
  "amount": 500
}
```

4. Проверяет, что response содержит:

```json
"transport": "grpc"
```

5. Проверяет, что operation создана со статусом:

```text
PENDING
```

6. Ждёт, пока worker-service обработает Kafka event.
7. Проверяет, что operation стала:

```text
CONFIRMED
```

8. Проверяет, что `current_amount` цели увеличился минимум на 500.
9. Проверяет, что worker создал связанную transaction с id:

```text
tx-goal-operation-{operation_id}
```

10. Проверяет, что transaction имеет:

```text
type = expense
category = Savings Goal
amount = 500
```

Что доказывает:

- API Gateway endpoint работает.
- API Gateway вызывает Savings Service через gRPC.
- Savings Service создаёт GoalOperation.
- Savings Service публикует Kafka event.
- Worker Service читает Kafka topic.
- Worker Service асинхронно меняет статус `PENDING → CONFIRMED`.
- Worker обновляет `current_amount` у goal.
- Worker создаёт связанную transaction в transaction-service.
- Вся цепочка microservices работает вместе.

Главная цепочка:

```text
Frontend / Client
→ REST API Gateway
→ gRPC Savings Service
→ Kafka event
→ Worker Service
→ Savings DB update
→ Transaction Service
```

---

### `test_worker_marks_withdraw_as_failed_when_amount_is_too_high`

Шаги теста:

1. Создаёт пользователя.
2. Создаёт savings goal с `current_amount = 0`.
3. Отправляет operation:

```text
WITHDRAW 9999
```

4. Ждёт, пока worker обработает event.
5. Проверяет, что operation стала:

```text
FAILED
```

6. Проверяет, что `failure_reason` содержит текст `Not enough`.
7. Проверяет, что `current_amount` остался `0`.
8. Проверяет, что linked transaction не была создана.

Что доказывает:

- Worker-service умеет обрабатывать ошибочные бизнес-сценарии.
- Нельзя снять больше денег, чем накоплено.
- Status transition `PENDING → FAILED` работает.
- При failed operation transaction не создаётся.
- Данные goal не повреждаются.

---

## `test_05_recommendations.py`

Этот файл проверяет recommendation service.

### `test_recommendations_are_generated_from_real_transactions`

Шаги теста:

1. Создаёт тестового пользователя.
2. Создаёт income transaction.
3. Создаёт expense transaction.
4. Вызывает:

```text
GET /recommendations/{user_id}
```

5. Проверяет, что response содержит список recommendations.
6. Проверяет, что хотя бы одна recommendation содержит поле `approach`.

Что доказывает:

- Recsys-service работает.
- Recommendations создаются на основе реальных transactions пользователя.
- Recommendation endpoint возвращает корректную структуру ответа.

---

# EN — Detailed Description of Each File and Test

## `conftest.py`

This is a shared helper file for all tests. It is not a test file itself, but it provides common settings, fixtures and utility functions.

### What `conftest.py` does

- Stores URLs for all services:
  - `GATEWAY_URL` — API Gateway through Nginx
  - `AUTH_URL` — auth-service
  - `TRANSACTION_URL` — transaction-service
  - `SAVINGS_URL` — savings-service
  - `AGENT_URL` — agent-service
  - `RECSYS_URL` — recsys-service
  - `FRONTEND_URL` — frontend
  - `KAFKA_UI_URL` — Kafka UI
- Generates unique emails for test users.
- Creates a shared `requests.Session`.
- Provides `assert_status()` for HTTP status checks.
- Provides `wait_for()` for asynchronous worker-service processing.
- Provides `TINY_PNG_BYTES`, a tiny PNG image used for MinIO upload tests.
- Provides the `registered_user` fixture, which creates and logs in a test user.
- Provides helper functions:
  - `create_transaction()`
  - `create_goal()`
  - `get_goal_by_id()`
  - `get_goal_operation()`
  - `get_user_transactions()`
- Before the test session, it clears only Redis keys matching `rate_limit:*`, so repeated test runs do not fail with HTTP `429 Rate limit exceeded`.

### Why CRUD requests go directly to services

The project has a Redis-based rate limiter in the API Gateway. If all tests go through the gateway, repeated test runs may quickly exceed the `60/min` limit. For that reason, ordinary operations such as registration, transaction creation and goal creation go directly to the corresponding services. The API Gateway is still used where it matters most: to prove gRPC flows.

---

## `test_01_health.py`

This file verifies that the main services are running and reachable.

### `test_gateway_health`

Checks:

```text
GET http://localhost:8088/health
```

Expected result:

```json
{
  "service": "api-gateway",
  "status": "running"
}
```

Proves:

- API Gateway is running.
- Nginx balancer is reachable on `localhost:8088`.
- Basic routing works.

---

### `test_core_services_are_running`

Checks root endpoints of the main microservices:

```text
GET auth-service /
GET transaction-service /
GET savings-service /
GET recsys-service /
```

Proves:

- `auth-service` is running.
- `transaction-service` is running.
- `savings-service` is running.
- `recsys-service` is running.
- The core FastAPI services are reachable.

---

### `test_agent_health_and_metrics_are_available`

Checks:

```text
GET agent-service /health
GET agent-service /metrics
```

Proves:

- The AI agent service is alive.
- Health-check is available.
- Prometheus-style metrics are available.
- `/metrics` contains `kopilkin_agent_chat_requests_total`.

The test intentionally does not call the full AI chat endpoint because it depends on Ollama/local LLM and can be slow on a laptop. For project defense, health and metrics are enough to demonstrate the service.

---

### `test_frontend_and_kafka_ui_are_reachable`

Checks:

```text
GET frontend
GET Kafka UI
```

Proves:

- The frontend is reachable.
- Kafka UI is reachable.
- Kafka monitoring interface is running.

Kafka UI may return `406 Not Acceptable` for the root page because of content negotiation. In this test, `406` is accepted as a valid reachable response because it still proves the Kafka UI service is alive and responding.

---

## `test_02_auth_jwt_and_minio.py`

This file verifies authentication, JWT, Redis token blacklist and MinIO avatar upload.

### `test_register_login_me_logout_blacklist_flow`

Test steps:

1. Creates a new user through `auth-service /register`.
2. Checks that the response contains the user email.
3. Checks that the response does not expose `password` or `password_hash`.
4. Logs in through `/login`.
5. Receives a JWT `access_token`.
6. Calls `/me` with Bearer token.
7. Calls `/logout`.
8. Calls `/me` again with the same token.
9. Expects HTTP `401`.

Proves:

- Registration works.
- Password is not exposed to the client.
- Login works.
- JWT token is generated.
- Protected endpoint `/me` works.
- Logout adds the token to Redis blacklist.
- The old token no longer works after logout.

---

### `test_avatar_upload_uses_minio_and_updates_profile`

Test steps:

1. Creates and logs in a test user.
2. Uploads a tiny PNG file to `/me/avatar`.
3. Checks that the response contains `avatar_url`.
4. Checks that the URL contains `kopilkin-files` and `avatars`.

Proves:

- Avatar upload works.
- Auth service is integrated with MinIO.
- The database stores the file URL, while the actual file is stored in MinIO.

---

## `test_03_transactions_grpc_summary.py`

This file verifies transaction-service and the gRPC flow between API Gateway and transaction-service.

### `test_transaction_creation_and_grpc_summary`

Test steps:

1. Creates a test user.
2. Creates one income transaction.
3. Creates two expense transactions.
4. Gets the user's transaction list.
5. Checks that the transactions were created.
6. Calls through API Gateway:

```text
GET /transactions/{user_id}/summary
```

7. Checks that the summary contains:

```json
"transport": "grpc"
```

8. Checks financial totals:

- total income is at least 1000
- total expense is at least 400
- balance is at least 600

Proves:

- Transaction creation works.
- Transaction-service stores data.
- API Gateway calls transaction-service through gRPC.
- gRPC `GetUserSummary` flow works.
- Summary returns correct financial values.

---

### `test_transaction_create_is_idempotent_when_id_is_reused`

Test steps:

1. Creates a transaction with a predefined `id`.
2. Sends another create request with the same `id`.
3. Checks that both responses contain the same transaction id.
4. Gets the user's transaction list.
5. Checks that only one transaction with this id exists.

Proves:

- Idempotency works.
- Duplicate requests with the same id do not create duplicated transactions.
- This is important for worker-service, because worker creates linked transaction ids like:

```text
tx-goal-operation-{operation_id}
```

If the worker accidentally processes the same Kafka event again, it must not create a duplicate transaction.

---

## `test_04_savings_goal_grpc_worker.py`

This is the most important test file because it verifies the main business flow of the project: savings goal operation through gRPC, Kafka and worker-service.

### `test_goal_image_upload_uses_minio`

Test steps:

1. Creates a test user.
2. Creates a savings goal.
3. Uploads a PNG image for the goal.
4. Checks that the response contains `image_url`.
5. Checks that the URL contains `kopilkin-files` and `goals`.

Proves:

- Savings goal creation works.
- Goal image upload works.
- Savings-service is integrated with MinIO.
- Savings goal images are stored in MinIO.

---

### `test_create_goal_operation_via_grpc_then_worker_confirms_and_creates_transaction`

This is the main integration test of the project.

Test steps:

1. Creates a test user.
2. Creates a savings goal.
3. Sends a deposit operation through API Gateway:

```text
POST /grpc/goals/{goal_id}/operations
```

Payload:

```json
{
  "user_id": "...",
  "operation_type": "DEPOSIT",
  "amount": 500
}
```

4. Checks that the response contains:

```json
"transport": "grpc"
```

5. Checks that the operation is created with status:

```text
PENDING
```

6. Waits until worker-service processes the Kafka event.
7. Checks that the operation becomes:

```text
CONFIRMED
```

8. Checks that goal `current_amount` increases by at least 500.
9. Checks that worker created a linked transaction with id:

```text
tx-goal-operation-{operation_id}
```

10. Checks that the transaction has:

```text
type = expense
category = Savings Goal
amount = 500
```

Proves:

- API Gateway endpoint works.
- API Gateway calls Savings Service through gRPC.
- Savings Service creates GoalOperation.
- Savings Service publishes Kafka event.
- Worker Service consumes the Kafka topic.
- Worker Service asynchronously changes status `PENDING → CONFIRMED`.
- Worker updates goal `current_amount`.
- Worker creates a linked transaction in transaction-service.
- The whole microservice chain works together.

Main chain:

```text
Frontend / Client
→ REST API Gateway
→ gRPC Savings Service
→ Kafka event
→ Worker Service
→ Savings DB update
→ Transaction Service
```

---

### `test_worker_marks_withdraw_as_failed_when_amount_is_too_high`

Test steps:

1. Creates a user.
2. Creates a savings goal with `current_amount = 0`.
3. Sends operation:

```text
WITHDRAW 9999
```

4. Waits until worker processes the event.
5. Checks that the operation becomes:

```text
FAILED
```

6. Checks that `failure_reason` contains `Not enough`.
7. Checks that `current_amount` remains `0`.
8. Checks that linked transaction was not created.

Proves:

- Worker-service handles invalid business scenarios.
- A user cannot withdraw more money than currently saved.
- Status transition `PENDING → FAILED` works.
- No transaction is created for a failed operation.
- Goal data remains consistent.

---

## `test_05_recommendations.py`

This file verifies the recommendation service.

### `test_recommendations_are_generated_from_real_transactions`

Test steps:

1. Creates a test user.
2. Creates one income transaction.
3. Creates one expense transaction.
4. Calls:

```text
GET /recommendations/{user_id}
```

5. Checks that the response contains a list of recommendations.
6. Checks that at least one recommendation contains the `approach` field.

Proves:

- Recsys-service works.
- Recommendations are generated from real user transactions.
- Recommendation endpoint returns a valid response structure.

---

# How to Run / Как запускать

## RU

Сначала проект должен быть поднят:

```bash
docker compose up -d --build
```

Установить зависимости для тестов:

```bash
pip install -r requirements-test.txt
```

Запустить все тесты:

```bash
pytest tests -v
```

Ожидаемый результат:

```text
12 passed
```

## EN

First, the project must be running:

```bash
docker compose up -d --build
```

Install test dependencies:

```bash
pip install -r requirements-test.txt
```

Run all tests:

```bash
pytest tests -v
```

Expected result:

```text
12 passed
```

---
