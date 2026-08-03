from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import BusinessTypeOption, Category
from app.schemas import BusinessTypeOptionOut, CategoryOut

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()


@router.get("/business-types", response_model=list[BusinessTypeOptionOut])
def list_business_types(db: Session = Depends(get_db)):
    return db.query(BusinessTypeOption).filter(BusinessTypeOption.is_active.is_(True)).all()
