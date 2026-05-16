# Memory Management System

## Implemented solution

Kopilkin uses **Mem0 + Qdrant + Ollama embeddings** for long-term semantic memory.

- **Mem0** manages memory add/search operations.
- **Qdrant** stores memory vectors in the `kopilkin_memory` collection.
- **Ollama `nomic-embed-text`** is used as the local embedding model.
- Memory is separated by `user_id`, so the agent retrieves only relevant memories for the current user.

## How memory works in the agent flow

1. User sends a message to `/chat`.
2. Orchestrator calls `get_memory(user_id, message)`.
3. Mem0 searches Qdrant for semantically relevant previous memories.
4. Retrieved memories are added to the current prompt as previous context.
5. After the final response, `save_memory(user_id, message, response)` stores the new interaction.

## Why Mem0 was selected

Mem0 was selected because the project needs personalized long-term memory, not only document retrieval. A personal finance assistant should remember repeated user concerns, previous spending patterns, and earlier advice. Mem0 is simple to integrate, supports user-level memory, and works with self-hosted Qdrant.

## Comparison with other memory approaches

| Option | Advantages | Drawbacks | Decision |
|---|---|---|---|
| Classic RAG | Simple retrieval from documents | Not ideal for evolving personal memory; weak temporal/user state | Not selected as main memory |
| Mem0 | Easy user/session memory; good for personalization | Less explainable than graph memory | Selected |
| Zep | Good conversation memory and fact extraction | More setup and backend complexity | Considered |
| Letta / MemGPT | Advanced stateful agents with editable memory blocks | Too complex for this MVP | Considered |
| Graphiti | Temporal knowledge graph and hybrid retrieval | More powerful but heavier to implement | Future improvement |
| LlamaIndex | Strong ingestion/retrieval framework | More document-oriented than personal memory | Considered |
| PageIndex | Reasoning-based document navigation | Best for complex documents, not user spending history | Not selected |

## Why classic RAG is not optimal here

Classic RAG is useful when the agent needs to answer questions from static documents. Kopilkin needs something different: evolving user-specific memory across conversations. The agent must remember previous user preferences and financial concerns. Therefore, a memory layer such as Mem0 is more suitable than a simple vector-based document RAG pipeline.

## Short-term and long-term memory

- **Short-term memory:** current user message, current transaction summary, analyst result passed to advisor.
- **Long-term memory:** previous user-agent interactions stored through Mem0 and Qdrant.

## Known limitations

- Memory quality depends on embedding quality.
- Vector memory can retrieve semantically similar but not always logically relevant entries.
- No temporal knowledge graph is implemented yet.
- Memory deletion and privacy controls should be improved for production.

## Future improvements

- Add Graphiti-like temporal memory graph.
- Add memory summarization.
- Add memory deletion/export for privacy.
- Add evaluation of memory retrieval relevance.
