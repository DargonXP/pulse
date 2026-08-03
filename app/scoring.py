"""Deterministic heuristic scoring for CRM customers.

Kept rule-based (not an LLM call) since this runs on every list/create and
must be fast, explainable, and free. The case explicitly allows mock/simple
data-driven scoring ("AI-оценка клиентов") — this is that scoring layer.
"""

from datetime import date


def compute_customer_scores(
    visits_count: int,
    total_spent: float,
    first_visit: date,
    last_visit: date,
    today: date | None = None,
) -> tuple[float, float, str]:
    today = today or date.today()
    recency_days = max(0, (today - last_visit).days)
    tenure_days = max(1, (last_visit - first_visit).days) if last_visit > first_visit else 1

    frequency_component = min(60.0, visits_count * 6.0)
    monetary_component = min(40.0, (total_spent / 5000.0) * 40.0)
    value_score = round(min(100.0, frequency_component + monetary_component), 1)

    recency_penalty = min(100.0, recency_days * 1.5)
    loyalty_discount = min(30.0, visits_count * 2.0)
    churn_risk_score = round(max(0.0, min(100.0, recency_penalty - loyalty_discount)), 1)

    if visits_count <= 1:
        segment = "new"
    elif recency_days > 120:
        segment = "lost"
    elif churn_risk_score >= 55:
        segment = "at_risk"
    elif value_score >= 65:
        segment = "vip"
    else:
        segment = "regular"

    return value_score, churn_risk_score, segment
