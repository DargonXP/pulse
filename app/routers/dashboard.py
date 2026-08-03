from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import Campaign, Customer, Recommendation, User, UserTool
from app.schemas import BusinessProfileOut, CampaignOut, DashboardOut, RecommendationOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@router.get("", response_model=DashboardOut)
def get_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    active_tools_count = db.query(UserTool).filter(
        UserTool.user_id == current_user.id, UserTool.status == "activated"
    ).count()
    active_campaigns_count = db.query(Campaign).filter(
        Campaign.user_id == current_user.id, Campaign.status == "active"
    ).count()
    total_customers = db.query(Customer).filter(Customer.user_id == current_user.id).count()
    customers = db.query(Customer).filter(Customer.user_id == current_user.id).all()
    total_revenue = round(sum(c.total_spent for c in customers), 2)

    pending_recs = db.query(Recommendation).filter(
        Recommendation.user_id == current_user.id, Recommendation.status == "pending"
    ).all()
    pending_recs.sort(key=lambda r: (_PRIORITY_ORDER.get(r.priority, 3), r.created_at))
    top_recommendations = pending_recs[:3]

    recent_campaigns = db.query(Campaign).filter(
        Campaign.user_id == current_user.id
    ).order_by(Campaign.created_at.desc()).limit(5).all()

    activity_pool = []
    for c in db.query(Campaign).filter(Campaign.user_id == current_user.id).all():
        activity_pool.append({
            "type": "campaign_created",
            "title": f"Создана акция «{c.title}»",
            "timestamp": c.created_at.isoformat(),
        })
    for r in db.query(Recommendation).filter(
        Recommendation.user_id == current_user.id, Recommendation.status == "applied"
    ).all():
        activity_pool.append({
            "type": "recommendation_applied",
            "title": f"Применена рекомендация: {r.title}",
            "timestamp": r.created_at.isoformat(),
        })
    for ut in db.query(UserTool).filter(
        UserTool.user_id == current_user.id, UserTool.status == "activated"
    ).all():
        activity_pool.append({
            "type": "tool_activated",
            "title": f"Активирован инструмент: {ut.tool.name}",
            "timestamp": (ut.activated_at or ut.created_at).isoformat(),
        })

    activity_pool.sort(key=lambda a: a["timestamp"], reverse=True)

    return DashboardOut(
        business_name=current_user.business_name,
        business=BusinessProfileOut.model_validate(current_user.business) if current_user.business else None,
        active_tools_count=active_tools_count,
        active_campaigns_count=active_campaigns_count,
        total_customers=total_customers,
        total_revenue=total_revenue,
        top_recommendations=[RecommendationOut.model_validate(r) for r in top_recommendations],
        recent_campaigns=[CampaignOut.model_validate(c) for c in recent_campaigns],
        recent_activity=activity_pool[:10],
    )
