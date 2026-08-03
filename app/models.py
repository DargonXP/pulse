from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    business: Mapped["Business"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    customers: Mapped[list["Customer"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    saved_tools: Mapped[list["UserTool"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    business_type: Mapped[str] = mapped_column(String(50), nullable=False)  # coffee_shop, clothing_store, beauty_salon, service_point, other
    size: Mapped[str] = mapped_column(String(20), default="small")  # small, medium
    goal: Mapped[str] = mapped_column(String(30), default="new_customers")  # new_customers, retention, revenue
    avg_check: Mapped[float] = mapped_column(Float, default=0.0)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="business")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    tools: Mapped[list["Tool"]] = relationship(back_populates="category")


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    tool_type: Mapped[str] = mapped_column(String(30), nullable=False)  # marketing, sales, retention, analytics, automation
    icon: Mapped[str] = mapped_column(String(50), default="sparkles")
    steps: Mapped[str] = mapped_column(Text, default="[]")  # JSON-encoded list of onboarding steps
    example_usage: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    category: Mapped["Category"] = relationship(back_populates="tools")
    saved_by: Mapped[list["UserTool"]] = relationship(back_populates="tool", cascade="all, delete-orphan")


class UserTool(Base):
    __tablename__ = "user_tools"
    __table_args__ = (UniqueConstraint("user_id", "tool_id", name="uq_user_tool"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    tool_id: Mapped[int] = mapped_column(ForeignKey("tools.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="saved")  # saved, activated
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="saved_tools")
    tool: Mapped["Tool"] = relationship(back_populates="saved_by")


class CampaignTemplate(Base):
    """Admin-managed marketing template library, matched by business type."""

    __tablename__ = "campaign_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_type: Mapped[str] = mapped_column(String(50), nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(30), nullable=False)  # discount, bonus, coupon, combo
    title_template: Mapped[str] = mapped_column(String(255), nullable=False)
    text_template: Mapped[str] = mapped_column(Text, nullable=False)
    default_discount: Mapped[float] = mapped_column(Float, default=10.0)
    channel: Mapped[str] = mapped_column(String(20), default="sms")  # sms, email, social, qr
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    tool_id: Mapped[int | None] = mapped_column(ForeignKey("tools.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(30), nullable=False)  # discount, bonus, coupon, combo
    text: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String(20), default="sms")
    segment: Mapped[str] = mapped_column(String(30), default="all")  # all, new, regular, vip, at_risk
    discount_value: Mapped[float] = mapped_column(Float, default=10.0)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, active, paused, completed
    predicted_roi: Mapped[float] = mapped_column(Float, default=0.0)
    generated_by_ai: Mapped[bool] = mapped_column(Boolean, default=False)

    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    redeemed_count: Mapped[int] = mapped_column(Integer, default=0)
    qr_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="campaigns")
    tool: Mapped["Tool | None"] = relationship()


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    first_visit: Mapped[date] = mapped_column(Date, nullable=False)
    last_visit: Mapped[date] = mapped_column(Date, nullable=False)
    visits_count: Mapped[int] = mapped_column(Integer, default=1)
    total_spent: Mapped[float] = mapped_column(Float, default=0.0)

    value_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100, AI/heuristic-calculated
    churn_risk_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    segment: Mapped[str] = mapped_column(String(20), default="new")  # new, regular, vip, at_risk, lost

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="customers")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    tool_id: Mapped[int | None] = mapped_column(ForeignKey("tools.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(10), default="medium")  # high, medium, low
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, applied, dismissed
    source: Mapped[str] = mapped_column(String(10), default="rules")  # rules, ai

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="recommendations")
    tool: Mapped["Tool | None"] = relationship()


class AdminLog(Base):
    __tablename__ = "admin_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # create, update, delete
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # tool, category, campaign_template, business_type
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BusinessTypeOption(Base):
    """Admin-manageable list of business types shown in onboarding."""

    __tablename__ = "business_type_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), default="store")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
