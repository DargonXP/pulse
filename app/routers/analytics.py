from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import Campaign, Customer, User
from app.schemas import AnalyticsOverviewOut, ChannelPerformanceOut

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Weights describing a gently-growing trend across the last 6 months, used to turn a
# single point-in-time revenue total into a believable mock trend line for charts.
_TREND_WEIGHTS = [0.10, 0.13, 0.15, 0.18, 0.20, 0.24]


@router.get("/overview", response_model=AnalyticsOverviewOut)
def analytics_overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    customers = db.query(Customer).filter(Customer.user_id == current_user.id).all()
    campaigns = db.query(Campaign).filter(Campaign.user_id == current_user.id).all()

    total_revenue = round(sum(c.total_spent for c in customers), 2)
    new_customers = sum(1 for c in customers if c.segment == "new")
    repeat_customers = sum(1 for c in customers if c.visits_count > 1)
    active_campaigns = sum(1 for c in campaigns if c.status == "active")
    avg_check = current_user.business.avg_check if current_user.business else 0.0
    if not avg_check and customers:
        total_visits = sum(c.visits_count for c in customers) or 1
        avg_check = round(total_revenue / total_visits, 2)

    today = date.today()
    revenue_trend = []
    for i, weight in enumerate(_TREND_WEIGHTS):
        month_date = today.replace(day=1) - timedelta(days=30 * (len(_TREND_WEIGHTS) - 1 - i))
        revenue_trend.append({
            "month": month_date.strftime("%Y-%m"),
            "revenue": round(total_revenue * weight, 2),
        })

    channel_map: dict[str, dict] = {}
    for c in campaigns:
        bucket = channel_map.setdefault(c.channel, {"campaigns": 0, "sent": 0, "redeemed": 0})
        bucket["campaigns"] += 1
        bucket["sent"] += c.sent_count
        bucket["redeemed"] += c.redeemed_count

    channel_performance = [
        ChannelPerformanceOut(
            channel=channel,
            campaigns=data["campaigns"],
            sent=data["sent"],
            redeemed=data["redeemed"],
            conversion_rate=round((data["redeemed"] / data["sent"]) * 100, 1) if data["sent"] else 0.0,
        )
        for channel, data in channel_map.items()
    ]

    return AnalyticsOverviewOut(
        total_revenue=total_revenue,
        new_customers=new_customers,
        repeat_customers=repeat_customers,
        active_campaigns=active_campaigns,
        avg_check=avg_check,
        revenue_trend=revenue_trend,
        channel_performance=channel_performance,
    )
