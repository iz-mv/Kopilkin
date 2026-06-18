import os
from collections import defaultdict
from datetime import datetime, date, timedelta
from typing import Any, Optional

import httpx
from langfuse.decorators import observe

from app.prompts.system_prompts import ANALYST_PROMPT

TRANSACTION_SERVICE_URL = os.getenv("TRANSACTION_SERVICE_URL", "http://localhost:8002")


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None

    # Frontend normally sends YYYY-MM-DD. This also accepts full ISO strings.
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except Exception:
        pass

    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(value), fmt).date()
        except Exception:
            continue

    return None


def _previous_month_range(today: Optional[date] = None) -> tuple[date, date, str]:
    today = today or datetime.utcnow().date()
    first_day_this_month = today.replace(day=1)
    last_day_previous_month = first_day_this_month - timedelta(days=1)
    first_day_previous_month = last_day_previous_month.replace(day=1)
    label = first_day_previous_month.strftime("%B %Y")
    return first_day_previous_month, last_day_previous_month, label


@observe(name="transaction_service_summary_call")
def get_user_summary(user_id: str) -> dict[str, Any]:
    """Gets real financial summary from transaction-service."""
    try:
        response = httpx.get(
            f"{TRANSACTION_SERVICE_URL}/transactions/{user_id}/summary",
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except Exception as error:
        print("TRANSACTION SUMMARY ERROR:", error)
        return {}


@observe(name="transaction_service_transactions_call")
def get_user_transactions(user_id: str) -> list[dict[str, Any]]:
    """Gets real transaction rows from transaction-service."""
    try:
        response = httpx.get(
            f"{TRANSACTION_SERVICE_URL}/transactions/{user_id}",
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    except Exception as error:
        print("TRANSACTION LIST ERROR:", error)
        return []


def _build_financial_context(summary: dict[str, Any], transactions: list[dict[str, Any]]) -> str:
    prev_start, prev_end, prev_label = _previous_month_range()

    all_expense_by_category: dict[str, float] = defaultdict(float)
    all_income_by_category: dict[str, float] = defaultdict(float)

    prev_expense_by_category: dict[str, float] = defaultdict(float)
    prev_income_by_category: dict[str, float] = defaultdict(float)
    prev_transactions: list[dict[str, Any]] = []

    for tx in transactions:
        tx_type = str(tx.get("type") or "").lower()
        category = tx.get("category") or "Other"
        amount = float(tx.get("amount") or 0)
        tx_date = _parse_date(tx.get("date"))

        if tx_type == "expense":
            all_expense_by_category[category] += amount
        elif tx_type == "income":
            all_income_by_category[category] += amount

        if tx_date and prev_start <= tx_date <= prev_end:
            prev_transactions.append(tx)
            if tx_type == "expense":
                prev_expense_by_category[category] += amount
            elif tx_type == "income":
                prev_income_by_category[category] += amount

    prev_total_expense = sum(prev_expense_by_category.values())
    prev_total_income = sum(prev_income_by_category.values())
    prev_balance = prev_total_income - prev_total_expense

    top_prev_category = None
    if prev_expense_by_category:
        top_prev_category = max(prev_expense_by_category.items(), key=lambda item: item[1])

    recent_prev_lines = []
    for tx in sorted(prev_transactions, key=lambda item: item.get("date") or "", reverse=True)[:30]:
        recent_prev_lines.append(
            f"- {tx.get('date')}: {tx.get('type')} | {tx.get('category')} | "
            f"{tx.get('amount')} RUB | {tx.get('description') or ''}"
        )

    return f"""
User financial data from transaction-service:

ALL-TIME SUMMARY:
- Total income: {summary.get('total_income', 0)} RUB
- Total expenses: {summary.get('total_expense', 0)} RUB
- Balance: {summary.get('balance', 0)} RUB
- Transactions count: {summary.get('transactions_count', len(transactions))}
- All-time expenses by category: {dict(all_expense_by_category)}
- All-time income by category: {dict(all_income_by_category)}

PREVIOUS FULL CALENDAR MONTH SUMMARY:
- Period: {prev_label} ({prev_start.isoformat()} to {prev_end.isoformat()})
- Previous month income: {prev_total_income} RUB
- Previous month expenses: {prev_total_expense} RUB
- Previous month balance: {prev_balance} RUB
- Previous month transaction count: {len(prev_transactions)}
- Previous month expenses by category: {dict(prev_expense_by_category)}
- Previous month income by category: {dict(prev_income_by_category)}
- Biggest previous month expense category: {top_prev_category if top_prev_category else 'No expense data'}

PREVIOUS MONTH TRANSACTIONS SAMPLE:
{chr(10).join(recent_prev_lines) if recent_prev_lines else 'No dated transactions found for the previous full calendar month.'}
"""


@observe(name="analyst_agent")
def run_analyst(user_id: str, user_message: str, ollama_url: str) -> str:
    """
    Analyst agent — fetches real transaction data and analyzes it.
    It now sends both summary and category/monthly breakdowns to the LLM.
    """

    summary = get_user_summary(user_id)
    transactions = get_user_transactions(user_id)

    if summary or transactions:
        data_context = _build_financial_context(summary, transactions)
    else:
        data_context = "No transaction data found for this user."

    payload = {
        "model": "gemma3:4b",
        "messages": [
            {"role": "system", "content": ANALYST_PROMPT},
            {"role": "user", "content": f"{data_context}\n\nUser question: {user_message}"},
        ],
        "stream": False,
    }

    response = httpx.post(
        f"{ollama_url}/api/chat",
        json=payload,
        timeout=300.0,
    )
    response.raise_for_status()

    return response.json()["message"]["content"]
