import os
from mem0 import Memory


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))


config = {
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "gemma3:4b",
            "ollama_base_url": OLLAMA_URL,
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text",
            "ollama_base_url": OLLAMA_URL,
        },
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "kopilkin_memory",
            "host": QDRANT_HOST,
            "port": QDRANT_PORT,
            "embedding_model_dims": 768,
        },
    },
}


memory = Memory.from_config(config)


def save_memory(user_id: str, message: str, response: str):
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
    try:
        results = memory.search(
            query=query,
            filters={"user_id": user_id},
            limit=5,
        )

        if not results:
            return ""

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

        return "Previous context about this user:\n" + "\n".join(memory_lines)

    except Exception as e:
        print("MEMORY SEARCH ERROR:", e)
        return ""