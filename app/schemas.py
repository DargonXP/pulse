from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth / Business ----------

class BusinessProfileIn(BaseModel):
    business_type: str = Field(examples=["coffee_shop"])
    size: str = Field(default="small", examples=["small", "medium"])
    goal: str = Field(default="new_customers", examples=["new_customers", "retention", "revenue"])
    avg_check: float = 0.0
    city: str | None = None


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    business_name: str
    business: BusinessProfileIn


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserUpdateIn(BaseModel):
    business_name: str | None = None


class BusinessProfileOut(BusinessProfileIn):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: int
    email: EmailStr
    business_name: str
    is_admin: bool
    created_at: datetime
    business: BusinessProfileOut | None = None

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Catalog ----------

class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None

    model_config = {"from_attributes": True}


class CategoryIn(BaseModel):
    name: str
    slug: str
    description: str | None = None


class ToolOut(BaseModel):
    id: int
    name: str
    description: str
    category: CategoryOut
    tool_type: str
    icon: str
    steps: list[str] = []
    example_usage: str
    is_active: bool
    saved: bool = False
    activated: bool = False

    model_config = {"from_attributes": True}


class ToolIn(BaseModel):
    name: str
    description: str
    category_id: int
    tool_type: str
    icon: str = "sparkles"
    steps: list[str] = []
    example_usage: str = ""
    is_active: bool = True


class ToolUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None
    category_id: int | None = None
    tool_type: str | None = None
    icon: str | None = None
    steps: list[str] | None = None
    example_usage: str | None = None
    is_active: bool | None = None


# ---------- Campaigns ----------

class CampaignCreateIn(BaseModel):
    campaign_type: str = Field(examples=["discount", "bonus", "coupon", "combo"])
    channel: str = Field(default="sms", examples=["sms", "email", "social", "qr"])
    segment: str = Field(default="all", examples=["all", "new", "regular", "vip", "at_risk"])
    discount_value: float = 10.0
    tool_id: int | None = None
    use_ai: bool = True
    custom_prompt: str | None = None


class CampaignStatusIn(BaseModel):
    status: str = Field(examples=["draft", "active", "paused", "completed"])


class CampaignOut(BaseModel):
    id: int
    title: str
    campaign_type: str
    text: str
    channel: str
    segment: str
    discount_value: float
    status: str
    predicted_roi: float
    generated_by_ai: bool
    sent_count: int
    redeemed_count: int
    qr_token: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Customers ----------

class CustomerIn(BaseModel):
    name: str
    phone: str | None = None
    email: EmailStr | None = None
    first_visit: date
    last_visit: date
    visits_count: int = 1
    total_spent: float = 0.0


class CustomerOut(BaseModel):
    id: int
    name: str
    phone: str | None = None
    email: str | None = None
    first_visit: date
    last_visit: date
    visits_count: int
    total_spent: float
    value_score: float
    churn_risk_score: float
    segment: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SegmentSummaryOut(BaseModel):
    segment: str
    count: int
    total_spent: float
    avg_value_score: float


# ---------- Recommendations ----------

class RecommendationOut(BaseModel):
    id: int
    tool_id: int | None
    title: str
    description: str
    reason: str
    priority: str
    status: str
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Analytics / Dashboard ----------

class ChannelPerformanceOut(BaseModel):
    channel: str
    campaigns: int
    sent: int
    redeemed: int
    conversion_rate: float


class AnalyticsOverviewOut(BaseModel):
    total_revenue: float
    new_customers: int
    repeat_customers: int
    active_campaigns: int
    avg_check: float
    revenue_trend: list[dict]
    channel_performance: list[ChannelPerformanceOut]


class DashboardOut(BaseModel):
    business_name: str
    business: BusinessProfileOut | None
    active_tools_count: int
    active_campaigns_count: int
    total_customers: int
    total_revenue: float
    top_recommendations: list[RecommendationOut]
    recent_campaigns: list[CampaignOut]
    recent_activity: list[dict]


# ---------- Admin ----------

class CampaignTemplateOut(BaseModel):
    id: int
    business_type: str
    campaign_type: str
    title_template: str
    text_template: str
    default_discount: float
    channel: str
    is_active: bool

    model_config = {"from_attributes": True}


class CampaignTemplateIn(BaseModel):
    business_type: str
    campaign_type: str
    title_template: str
    text_template: str
    default_discount: float = 10.0
    channel: str = "sms"
    is_active: bool = True


class BusinessTypeOptionOut(BaseModel):
    id: int
    key: str
    label: str
    icon: str
    is_active: bool

    model_config = {"from_attributes": True}


class BusinessTypeOptionIn(BaseModel):
    key: str
    label: str
    icon: str = "store"
    is_active: bool = True


class AdminStatsOut(BaseModel):
    total_businesses: int
    active_businesses_30d: int
    total_campaigns: int
    active_campaigns: int
    total_customers: int
    popular_tools: list[dict]
    mrr_estimate: float
    system_health: str


class AdminUserOut(BaseModel):
    id: int
    email: EmailStr
    business_name: str
    is_admin: bool
    created_at: datetime
    business_type: str | None = None

    model_config = {"from_attributes": True}
