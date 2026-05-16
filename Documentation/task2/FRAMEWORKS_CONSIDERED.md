# Frameworks Considered

## LLM engines

| Engine | Description | Decision |
|---|---|---|
| Ollama | Simple local model runner with easy CLI and API | Selected |
| llama.cpp | Very lightweight local inference | Considered, but Ollama is easier for model management |
| vLLM | High-performance serving for larger models | Too heavy for local student hardware |

## Agent frameworks

| Framework | Advantages | Drawbacks | Decision |
|---|---|---|---|
| LangChain | Popular, many integrations | Can be too abstract for a small system | Considered |
| LangGraph | Good for explicit graph-based agent flows | More setup needed | Future improvement |
| CrewAI | Simple role-based multi-agent systems | Less control over low-level service integration | Considered |
| AutoGen | Strong multi-agent conversation framework | More complex than needed | Considered |
| Haystack | Strong for RAG pipelines | More document search oriented | Considered |
| Custom FastAPI architecture | Full control, easy to explain, fits microservices | More manual code | Selected |

## Why custom architecture was selected

The goal was to build a small but understandable multi-agent system integrated with existing Kopilkin microservices. A custom FastAPI implementation makes the architecture transparent: orchestrator, router, analyst, advisor, memory, and observability are visible in code and easy to defend orally.
