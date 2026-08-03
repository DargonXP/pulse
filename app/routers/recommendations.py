from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai import recommend_tools_for_business
from app.deps import get_current_user, get_db
from app.models import Recommendation, Tool, User, UserTool
from app.schemas import RecommendationOut

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def generate_recommendations_for_user(db: Session, user: User) -> list[Recommendation]:
    """(Re)generates pending AI/rule-based recommendations for a user's business profile.

    Used both by the onboarding flow (right after registration) and the
    on-demand "Обновить рекомендации" action in the AI Assistant page.
    """
    business = user.business
    business_type = business.business_type if business else "other"
    size = business.size if business else "small"
    goal = business.goal if business else "new_customers"

    available_tools = [
        {"id": t.id, "name": t.name, "tool_type": t.tool_type, "description": t.description}
        for t in db.query(Tool).filter(Tool.is_active.is_(True)).all()
    ]

    suggestions = recommend_tools_for_business(business_type, size, goal, available_tools)

    db.query(Recommendation).filter(
        Recommendation.user_id == user.id, Recommendation.status == "pending"
    ).delete()

    created = []
    for item in suggestions:
        rec = Recommendation(
            user_id=user.id,
            tool_id=item.get("tool_id"),
            title=item["title"],
            description=item["description"],
            reason=item["reason"],
            priority=item["priority"],
            source=item["source"],
            status="pending",
        )
        db.add(rec)
        created.append(rec)

    db.commit()
    for rec in created:
        db.refresh(rec)
    return created


@router.get("", response_model=list[RecommendationOut])
def list_recommendations(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Recommendation).filter(Recommendation.user_id == current_user.id)
    if status_filter:
        query = query.filter(Recommendation.status == status_filter)
    return query.order_by(Recommendation.created_at.desc()).all()


@router.post("/generate", response_model=list[RecommendationOut])
def regenerate_recommendations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return generate_recommendations_for_user(db, current_user)


@router.post("/{recommendation_id}/apply", response_model=RecommendationOut)
def apply_recommendation(
    recommendation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    rec = db.get(Recommendation, recommendation_id)
    if rec is None or rec.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Рекомендация не найдена")

    rec.status = "applied"
    if rec.tool_id:
        link = db.query(UserTool).filter(
            UserTool.user_id == current_user.id, UserTool.tool_id == rec.tool_id
        ).first()
        if link is None:
            link = UserTool(user_id=current_user.id, tool_id=rec.tool_id)
            db.add(link)
        link.status = "activated"

    db.commit()
    db.refresh(rec)
    return rec


@router.post("/{recommendation_id}/dismiss", response_model=RecommendationOut)
def dismiss_recommendation(
    recommendation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    rec = db.get(Recommendation, recommendation_id)
    if rec is None or rec.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Рекомендация не найдена")
    rec.status = "dismissed"
    db.commit()
    db.refresh(rec)
    return rec
