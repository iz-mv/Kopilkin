# Tests overview

The tests are integration tests for the running Docker Compose system.

## Important note about API Gateway rate limit

API Gateway has a Redis-based rate limiter. Re-running tests many times quickly can return HTTP 429. The test suite now uses direct service ports for normal CRUD calls and uses API Gateway only where it is important to prove gRPC/gateway functionality.

## Files

- `test_01_health.py` checks gateway, core service health, agent metrics, frontend and Kafka UI reachability.
- `test_02_auth_jwt_and_minio.py` checks register/login/JWT/logout blacklist and avatar upload to MinIO.
- `test_03_transactions_grpc_summary.py` checks transaction creation, idempotency, and gRPC summary through API Gateway.
- `test_04_savings_goal_grpc_worker.py` checks goal image upload, CreateGoalOperation through gRPC, Kafka worker processing, confirmed/failed statuses, and linked transaction creation.
- `test_05_recommendations.py` checks recommendation generation from real transaction data.
