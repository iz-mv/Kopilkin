import httpx
from langfuse.decorators import observe

from app.prompts.system_prompts import ADVISOR_PROMPT


@observe(name="advisor_agent")
def run_advisor(user_message: str, analyst_result: str, ollama_url: str) -> str:
    # Advisor agent takes analyst result and gives practical advice
    # analyst_result is the output from analyst_agent, passed here as context

    # Build context combining analyst findings with user question
    context = f"""
Analyst findings:
{analyst_result}

User question: {user_message}
"""

    payload = {
        "model": "gemma3:4b",
        "messages": [
            {"role": "system", "content": ADVISOR_PROMPT},
            {"role": "user", "content": context}
        ],
        "stream": False
    }

    response = httpx.post(
        f"{ollama_url}/api/chat",
        json=payload,
        timeout=300.0
    )

    return response.json()["message"]["content"]