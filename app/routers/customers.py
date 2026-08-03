from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import Customer, User
from app.schemas import CustomerIn, CustomerOut, SegmentSummaryOut
from app.scoring import compute_customer_scores

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerOut])
def list_customers(
    segment: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Customer).filter(Customer.user_id == current_user.id)
    if segment:
        query = query.filter(Customer.segment == segment)
    return query.order_by(Customer.last_visit.desc()).all()


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    value_score, churn_risk, segment = compute_customer_scores(
        payload.visits_count, payload.total_spent, payload.first_visit, payload.last_visit
    )
    customer = Customer(
        user_id=current_user.id,
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        first_visit=payload.first_visit,
        last_visit=payload.last_visit,
        visits_count=payload.visits_count,
        total_spent=payload.total_spent,
        value_score=value_score,
        churn_risk_score=churn_risk,
        segment=segment,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/segments/summary", response_model=list[SegmentSummaryOut])
def segments_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    customers = db.query(Customer).filter(Customer.user_id == current_user.id).all()
    buckets: dict[str, list[Customer]] = {}
    for c in customers:
        buckets.setdefault(c.segment, []).append(c)

    summary = []
    for segment, items in buckets.items():
        summary.append(SegmentSummaryOut(
            segment=segment,
            count=len(items),
            total_spent=round(sum(c.total_spent for c in items), 2),
            avg_value_score=round(sum(c.value_score for c in items) / len(items), 1) if items else 0.0,
        ))
    return summary


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    customer = db.get(Customer, customer_id)
    if customer is None or customer.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Клиент не найден")
    return customer
