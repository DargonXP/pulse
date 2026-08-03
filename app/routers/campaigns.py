import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.ai import generate_campaign_copy
from app.deps import get_current_user, get_db
from app.models import Campaign, User
from app.schemas import CampaignCreateIn, CampaignOut, CampaignStatusIn

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

VALID_STATUSES = {"draft", "active", "paused", "completed"}


def _get_owned_campaign(db: Session, campaign_id: int, user: User) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None or (campaign.user_id != user.id and not user.is_admin):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Акция не найдена")
    return campaign


@router.get("", response_model=list[CampaignOut])
def list_campaigns(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Campaign).filter(Campaign.user_id == current_user.id)
    if status_filter:
        query = query.filter(Campaign.status == status_filter)
    return query.order_by(Campaign.created_at.desc()).all()


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: CampaignCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = current_user.business
    business_type = business.business_type if business else "other"
    goal = business.goal if business else "new_customers"

    if payload.use_ai:
        generated = generate_campaign_copy(
            business_type=business_type,
            campaign_type=payload.campaign_type,
            discount_value=payload.discount_value,
            channel=payload.channel,
            goal=goal,
            business_name=current_user.business_name,
            custom_prompt=payload.custom_prompt,
        )
    else:
        generated = {
            "title": payload.custom_prompt or f"Акция для {current_user.business_name}",
            "text": payload.custom_prompt or "Специальное предложение для наших клиентов.",
            "predicted_roi": 2.0,
            "generated_by_ai": False,
        }

    campaign = Campaign(
        user_id=current_user.id,
        tool_id=payload.tool_id,
        title=generated["title"],
        campaign_type=payload.campaign_type,
        text=generated["text"],
        channel=payload.channel,
        segment=payload.segment,
        discount_value=payload.discount_value,
        status="draft",
        predicted_roi=generated["predicted_roi"],
        generated_by_ai=generated["generated_by_ai"],
        qr_token=uuid.uuid4().hex,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _get_owned_campaign(db, campaign_id, current_user)


@router.patch("/{campaign_id}/status", response_model=CampaignOut)
def update_campaign_status(
    campaign_id: int,
    payload: CampaignStatusIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимый статус")
    campaign = _get_owned_campaign(db, campaign_id, current_user)
    campaign.status = payload.status
    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/simulate-redemption", response_model=CampaignOut)
def simulate_redemption(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Demo helper: simulates one more send + a chance of redemption, to show growth in analytics."""
    campaign = _get_owned_campaign(db, campaign_id, current_user)
    campaign.sent_count += 1
    campaign.redeemed_count += 1
    db.commit()
    db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    campaign = _get_owned_campaign(db, campaign_id, current_user)
    db.delete(campaign)
    db.commit()
    return None


@router.get("/{campaign_id}/qr.png")
def get_campaign_qr(campaign_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    campaign = _get_owned_campaign(db, campaign_id, current_user)
    try:
        import qrcode
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="QR-библиотека не установлена") from exc

    img = qrcode.make(f"UPWISE-CAMPAIGN:{campaign.qr_token}")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")
