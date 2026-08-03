from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import Business, User
from app.routers.recommendations import generate_recommendations_for_user
from app.schemas import BusinessProfileIn, LoginIn, RegisterIn, TokenOut, UserOut, UserUpdateIn
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email уже зарегистрирован")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        business_name=payload.business_name,
    )
    db.add(user)
    db.flush()

    business = Business(
        user_id=user.id,
        business_type=payload.business.business_type,
        size=payload.business.size,
        goal=payload.business.goal,
        avg_check=payload.business.avg_check,
        city=payload.business.city,
    )
    db.add(business)
    db.commit()
    db.refresh(user)

    generate_recommendations_for_user(db, user)

    token = create_access_token(str(user.id))
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")

    token = create_access_token(str(user.id))
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.business_name:
        current_user.business_name = payload.business_name
    db.commit()
    db.refresh(current_user)
    return UserOut.model_validate(current_user)


@router.patch("/business", response_model=UserOut)
def update_business_profile(
    payload: BusinessProfileIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = current_user.business
    if business is None:
        business = Business(user_id=current_user.id)
        db.add(business)

    business.business_type = payload.business_type
    business.size = payload.size
    business.goal = payload.goal
    business.avg_check = payload.avg_check
    business.city = payload.city

    db.commit()
    db.refresh(current_user)
    generate_recommendations_for_user(db, current_user)
    return UserOut.model_validate(current_user)
