import httpx
from app.prompts.system_prompts import ANALYST_PROMPT


def get_user_transactions(user_id: str) -> dict:
    """Gets real transaction data from transaction-service"""
    try:
        response = httpx.get(
            f"http://localhost:8002/transactions/{user_id}/summary"
        )
        return response.json()
    except Exception:
        return {}


def run_analyst(user_id: str, user_message: str, ollama_url: str) -> str:
    """
    Analyst agent — fetches real data and analyzes it.
    Sends data + user question to LLM and returns analysis.
    """

    # Step 1: get real data from transaction-service
    summary = get_user_transactions(user_id)

    # Step 2: build context with real numbers
    if summary:
        data_context = f"""
User financial data:
- Total income: {summary.get('total_income', 0)} RUB
- Total expenses: {summary.get('total_expense', 0)} RUB
- By category: {summary.get('by_category', {})}
"""
    else:
        data_context = "No transaction data found for this user."

    # Step 3: send to LLM
    payload = {
        "model": "gemma3:4b",
        "messages": [
            {"role": "system", "content": ANALYST_PROMPT},
            {"role": "user", "content": f"{data_context}\n\nUser question: {user_message}"}
        ],
        "stream": False
    }

    response = httpx.post(
        f"{ollama_url}/api/chat",
        json=payload,
        timeout=300.0
    )

    return response.json()["message"]["content"]