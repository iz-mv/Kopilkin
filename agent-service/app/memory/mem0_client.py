from mem0 import Memory


config = {
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "gemma3:4b",
            "ollama_base_url": "http://localhost:11434",
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text",
            "ollama_base_url": "http://localhost:11434",
        },
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "kopilkin_memory",
            "host": "localhost",
            "port": 6333,
            "embedding_model_dims": 768,
        },
    },
}


memory = Memory.from_config(config)


def save_memory(user_id: str, message: str, response: str):
    """
    Saves user message and assistant response into mem0.
    If memory fails, it prints the error but does not crash the agent-service.
    """
    try:
        memory.add(
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": response},
            ],
            user_id=user_id,
        )

    except Exception as e:
        print("MEMORY SAVE ERROR:", e)


def get_memory(user_id: str, query: str) -> str:
    """
    Searches previous memories for this user.
    If Qdrant/mem0 fails, it returns empty context instead of crashing /chat.
    """
    try:
        results = memory.search(
            query=query,
            filters={"user_id": user_id},
            limit=5,
        )

        if not results:
            return ""

        # mem0 usually returns {"results": [...]}
        if isinstance(results, dict):
            memories = results.get("results", [])
        else:
            memories = results

        if not memories:
            return ""

        memory_lines = []

        for item in memories:
            if isinstance(item, dict):
                memory_text = (
                    item.get("memory")
                    or item.get("text")
                    or item.get("content")
                    or ""
                )

                if memory_text:
                    memory_lines.append(f"- {memory_text}")

        if not memory_lines:
            return ""

        memories_text = "\n".join(memory_lines)

        return f"Previous context about this user:\n{memories_text}"

    except Exception as e:
        print("MEMORY SEARCH ERROR:", e)
        return ""