# Isolation Strategy

## Implemented isolation

The agent system is deployed using Docker Compose.

Containerized components:

- `agent-service` - FastAPI service with the multi-agent logic.
- `qdrant` - vector database for long-term memory.
- `langfuse` - LLM/agent observability UI.
- `langfuse-db` - PostgreSQL database for Langfuse.

Ollama is kept on the host machine and is accessed from Docker through `host.docker.internal:11434`.

## Why Docker was selected

Docker was selected because it is lightweight, reproducible, easy to run locally, and suitable for student hardware. It provides process and dependency isolation without the overhead of a full virtual machine.

## Considered options

| Option | Advantages | Drawbacks | Decision |
|---|---|---|---|
| No isolation | Simple to run | Dependency conflicts, unsafe, not reproducible | Rejected |
| Python virtual environment | Lightweight | Isolates only Python dependencies, not databases/services | Not enough |
| Docker containers | Reproducible, isolated services, easy local deployment | Still shares host kernel; GPU/LLM access can be tricky | Selected |
| Full VM | Strong isolation | Heavy for student laptop, slower setup | Not selected |
| Kubernetes | Production-grade orchestration | Too complex for this task and local demo | Future option |
| Sandbox runtime | Stronger execution isolation | More complex; unnecessary because the agent does not execute arbitrary user code | Not selected |

## Hybrid decision

The final setup is a hybrid local/container architecture. The agent runtime, Qdrant, and Langfuse are containerized. Ollama remains on the host because it already manages local model files and hardware resources. This is practical for a student laptop while still isolating the main services.

## Security limitations

- Docker is not a complete security boundary.
- Secrets should be moved from `docker-compose.yml` into `.env` or a secret manager.
- In production, CORS should not allow all origins.
- API authentication should be enforced between services.
