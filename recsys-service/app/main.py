import os
from collections import defaultdict

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.events import publish_event


TRANSACTION_SERVICE_URL = os.getenv(
    "TRANSACTION_SERVICE_URL",
    "http://localhost:8002"
)

app = FastAPI(title="Kopilkin RecSys Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "recsys-service",
        "status": "running"
    }


@app.get("/recommendations/{user_id}")
async def get_recommendations(user_id: str):
    publish_event(
        topic="recommendation.requested",
        key=user_id,
        event={
            "event_type": "recommendation.requested",
            "user_id": user_id,
        },
    )
    transactions = await fetch_user_transactions(user_id)

    if not transactions:
        return {
            "user_id": user_id,
            "recommendations": [
                {
                    "type": "cold_start",
                    "title": "Start tracking your first expenses",
                    "description": "Add a few transactions so Kopilkin can generate personalized financial recommendations.",
                    "approach": "heuristic"
                },
                {
                    "type": "cold_start",
                    "title": "Create your first savings goal",
                    "description": "A savings goal helps the system understand what you are planning for.",
                    "approach": "heuristic"
                }
            ]
        }

    recommendations = []

    recommendations.extend(generate_heuristic_recommendations(transactions))
    recommendations.extend(generate_content_based_recommendations(transactions))
    recommendations.extend(generate_collaborative_recommendations(transactions))

    publish_event(
        topic="recommendation.generated",
        key=user_id,
        event={
            "event_type": "recommendation.generated",
            "user_id": user_id,
            "recommendations_count": len(recommendations),
            "approaches": list(set(
                recommendation.get("approach", "unknown")
                for recommendation in recommendations
            )),
        },
    )

    return {
        "user_id": user_id,
        "recommendations": recommendations
    }


async def fetch_user_transactions(user_id: str):
    url = f"{TRANSACTION_SERVICE_URL}/transactions/{user_id}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not fetch transactions: {error}"
        )


def generate_heuristic_recommendations(transactions):
    total_income = sum(t["amount"] for t in transactions if t["type"] == "income")
    total_expense = sum(t["amount"] for t in transactions if t["type"] == "expense")

    recommendations = []

    if total_income > 0:
        saving_target = round(total_income * 0.1)
        recommendations.append({
            "type": "saving_rule",
            "title": "Save 10% of your income",
            "description": f"Based on your income, try saving around {saving_target} ₽ this month.",
            "approach": "heuristic"
        })

    if total_expense > total_income and total_income > 0:
        recommendations.append({
            "type": "overspending_alert",
            "title": "Your expenses are higher than your income",
            "description": "Consider reducing non-essential spending categories or setting a weekly budget.",
            "approach": "heuristic"
        })

    return recommendations


def generate_content_based_recommendations(transactions):
    category_totals = defaultdict(float)

    for transaction in transactions:
        if transaction["type"] == "expense":
            category_totals[transaction["category"]] += transaction["amount"]

    if not category_totals:
        return []

    top_category = max(category_totals, key=category_totals.get)
    top_amount = category_totals[top_category]

    category_advice = {
        "Restaurants": "Try cooking at home a few days per week to reduce restaurant expenses.",
        "Groceries": "Plan grocery shopping with a list to avoid impulse purchases.",
        "Shopping": "Set a monthly shopping limit and wait 24 hours before buying non-essential items.",
        "Transport": "Compare taxi, public transport, and walking options for short routes.",
        "Travel": "Create a separate travel savings goal and move small amounts regularly.",
        "Entertainment": "Choose a fixed entertainment budget for each week.",
        "Bills": "Review subscriptions and cancel services you do not use.",
        "Health": "Keep health spending planned, but compare pharmacy prices when possible.",
        "Education": "Education expenses are useful, but track subscriptions and unused courses.",
        "Other": "Review uncategorized expenses and move them into clear categories."
    }

    return [
        {
            "type": "category_based",
            "title": f"Your biggest spending category is {top_category}",
            "description": f"You spent {round(top_amount, 2)} ₽ on {top_category}. {category_advice.get(top_category, 'Consider setting a limit for this category.')}",
            "approach": "content_based"
        }
    ]


def generate_collaborative_recommendations(transactions):
    user_vector = build_category_vector(transactions)

    synthetic_users = [
        {
            "name": "student_saver",
            "vector": {"Restaurants": 0.2, "Transport": 0.2, "Education": 0.4, "Groceries": 0.2},
            "recommendation": "Students with similar spending often benefit from weekly food and transport limits."
        },
        {
            "name": "traveler",
            "vector": {"Travel": 0.5, "Restaurants": 0.2, "Shopping": 0.2, "Transport": 0.1},
            "recommendation": "Users with travel-heavy spending usually create a travel fund and save before trips."
        },
        {
            "name": "shopper",
            "vector": {"Shopping": 0.5, "Restaurants": 0.2, "Entertainment": 0.2, "Groceries": 0.1},
            "recommendation": "Users with similar shopping behavior often reduce spending by setting category limits."
        },
        {
            "name": "home_budget_user",
            "vector": {"Groceries": 0.4, "Bills": 0.3, "Health": 0.1, "Transport": 0.2},
            "recommendation": "Users with home-budget patterns usually benefit from monthly fixed expense planning."
        }
    ]

    best_user = None
    best_score = -1

    for synthetic_user in synthetic_users:
        score = cosine_similarity(user_vector, synthetic_user["vector"])
        if score > best_score:
            best_score = score
            best_user = synthetic_user

    if not best_user:
        return []

    return [
        {
            "type": "similar_users",
            "title": f"Recommendation based on similar users: {best_user['name']}",
            "description": best_user["recommendation"],
            "approach": "collaborative_filtering",
            "similarity_score": round(best_score, 3)
        }
    ]


def build_category_vector(transactions):
    category_totals = defaultdict(float)
    total_expense = 0

    for transaction in transactions:
        if transaction["type"] == "expense":
            category = transaction["category"]
            amount = transaction["amount"]

            category_totals[category] += amount
            total_expense += amount

    if total_expense == 0:
        return {}

    return {
        category: amount / total_expense
        for category, amount in category_totals.items()
    }


def cosine_similarity(vector_a, vector_b):
    all_keys = set(vector_a.keys()) | set(vector_b.keys())

    if not all_keys:
        return 0

    dot_product = sum(vector_a.get(key, 0) * vector_b.get(key, 0) for key in all_keys)

    magnitude_a = sum(value ** 2 for value in vector_a.values()) ** 0.5
    magnitude_b = sum(value ** 2 for value in vector_b.values()) ** 0.5

    if magnitude_a == 0 or magnitude_b == 0:
        return 0

    return dot_product / (magnitude_a * magnitude_b)