import httpx
from app.agents.analyst_agent import run_analyst
from app.agents.advisor_agent import run_advisor
from app.prompts.system_prompts import ORCHESTRATOR_PROMPT
from app.memory.mem0_client import save_memory, get_memory

OLLAMA_URL = "http://localhost:11434"


def route(user_message: str) -> str:
    # Sends user message to LLM and gets routing decision: analyst or advisor
    payload = {
        "model": "gemma3:4b",
        "messages": [
            {"role": "system", "content": ORCHESTRATOR_PROMPT},
            {"role": "user", "content": user_message}
        ],
        "stream": False
    }

    response = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json=payload,
        timeout=300.0
    )

    decision = response.json()["message"]["content"].strip().lower()

    # Safety check — if LLM returned something unexpected, default to analyst
    if decision not in ["analyst", "advisor"]:
        decision = "analyst"

    return decision


def run_orchestrator(user_id: str, user_message: str) -> str:
    # Step 1: get relevant memories for this user
    memory_context = get_memory(user_id, user_message)

    # Step 2: add memory context to user message if exists
    if memory_context:
        enriched_message = f"{memory_context}\n\nCurrent question: {user_message}"
    else:
        enriched_message = user_message

    # Step 3: decide which agent handles this message
    decision = route(enriched_message)

    # Step 4: run the right agent
    if decision == "analyst":
        response = run_analyst(user_id, enriched_message, OLLAMA_URL)
    elif decision == "advisor":
        analyst_result = run_analyst(user_id, enriched_message, OLLAMA_URL)
        response = run_advisor(enriched_message, analyst_result, OLLAMA_URL)

    # Step 5: save this conversation to memory
    save_memory(user_id, user_message, response)

    return response