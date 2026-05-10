import httpx
from app.agents.analyst_agent import run_analyst
from app.agents.advisor_agent import run_advisor
from app.prompts.system_prompts import ORCHESTRATOR_PROMPT

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
        timeout=60.0
    )

    decision = response.json()["message"]["content"].strip().lower()

    # Safety check — if LLM returned something unexpected, default to analyst
    if decision not in ["analyst", "advisor"]:
        decision = "analyst"

    return decision


def run_orchestrator(user_id: str, user_message: str) -> str:
    # Step 1: decide which agent handles this message
    decision = route(user_message)

    # Step 2: run the right agent
    if decision == "analyst":
        return run_analyst(user_id, user_message, OLLAMA_URL)

    elif decision == "advisor":
        # Advisor needs analyst data first for context
        analyst_result = run_analyst(user_id, user_message, OLLAMA_URL)
        return run_advisor(user_message, analyst_result, OLLAMA_URL)