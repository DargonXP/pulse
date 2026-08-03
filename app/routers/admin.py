import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.models import (
    AdminLog,
    Business,
    BusinessTypeOption,
    Campaign,
    CampaignTemplate,
    Category,
    Customer,
    Tool,
    User,
    UserTool,
)
from app.schemas import (
    AdminStatsOut,
    AdminUserOut,
    BusinessTypeOptionIn,
    BusinessTypeOptionOut,
    CampaignTemplateIn,
    CampaignTemplateOut,
    CategoryIn,
    CategoryOut,
    ToolIn,
    ToolOut,
    ToolUpdateIn,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _log(db: Session, admin: User, action: str, entity_type: str, entity_id: int | None, details: str = ""):
    db.add(AdminLog(admin_id=admin.id, action=action, entity_type=entity_type, entity_id=entity_id, details=details))


def _tool_out(tool: Tool) -> ToolOut:
    return ToolOut(
        id=tool.id,
        name=tool.name,
        description=tool.description,
        category=tool.category,
        tool_type=tool.tool_type,
        icon=tool.icon,
        steps=json.loads(tool.steps or "[]"),
        example_usage=tool.example_usage,
        is_active=tool.is_active,
        saved=False,
        activated=False,
    )


# ---------- Tools ----------

@router.get("/tools", response_model=list[ToolOut])
def admin_list_tools(db: Session = Depends(get_db)):
    return [_tool_out(t) for t in db.query(Tool).all()]


@router.post("/tools", response_model=ToolOut, status_code=status.HTTP_201_CREATED)
def admin_create_tool(payload: ToolIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Категория не найдена")
    tool = Tool(
        name=payload.name,
        description=payload.description,
        category_id=payload.category_id,
        tool_type=payload.tool_type,
        icon=payload.icon,
        steps=json.dumps(payload.steps, ensure_ascii=False),
        example_usage=payload.example_usage,
        is_active=payload.is_active,
    )
    db.add(tool)
    db.flush()
    _log(db, admin, "create", "tool", tool.id, tool.name)
    db.commit()
    db.refresh(tool)
    return _tool_out(tool)


@router.put("/tools/{tool_id}", response_model=ToolOut)
def admin_update_tool(
    tool_id: int, payload: ToolUpdateIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    tool = db.get(Tool, tool_id)
    if tool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Инструмент не найден")

    data = payload.model_dump(exclude_unset=True)
    if "steps" in data and data["steps"] is not None:
        data["steps"] = json.dumps(data["steps"], ensure_ascii=False)
    for field, value in data.items():
        setattr(tool, field, value)

    _log(db, admin, "update", "tool", tool.id)
    db.commit()
    db.refresh(tool)
    return _tool_out(tool)


@router.delete("/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_tool(tool_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    tool = db.get(Tool, tool_id)
    if tool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Инструмент не найден")
    db.query(UserTool).filter(UserTool.tool_id == tool_id).delete()
    db.delete(tool)
    _log(db, admin, "delete", "tool", tool_id, tool.name)
    db.commit()
    return None


# ---------- Categories ----------

@router.get("/categories", response_model=list[CategoryOut])
def admin_list_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def admin_create_category(payload: CategoryIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if db.query(Category).filter(Category.slug == payload.slug).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Категория с таким slug уже существует")
    category = Category(**payload.model_dump())
    db.add(category)
    db.flush()
    _log(db, admin, "create", "category", category.id, category.name)
    db.commit()
    db.refresh(category)
    return category


@router.put("/categories/{category_id}", response_model=CategoryOut)
def admin_update_category(
    category_id: int, payload: CategoryIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Категория не найдена")
    for field, value in payload.model_dump().items():
        setattr(category, field, value)
    _log(db, admin, "update", "category", category.id)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_category(category_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Категория не найдена")
    if db.query(Tool).filter(Tool.category_id == category_id).count() > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить категорию, к которой привязаны инструменты",
        )
    db.delete(category)
    _log(db, admin, "delete", "category", category_id, category.name)
    db.commit()
    return None


# ---------- Campaign templates ----------

@router.get("/campaign-templates", response_model=list[CampaignTemplateOut])
def admin_list_templates(db: Session = Depends(get_db)):
    return db.query(CampaignTemplate).all()


@router.post("/campaign-templates", response_model=CampaignTemplateOut, status_code=status.HTTP_201_CREATED)
def admin_create_template(
    payload: CampaignTemplateIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    template = CampaignTemplate(**payload.model_dump())
    db.add(template)
    db.flush()
    _log(db, admin, "create", "campaign_template", template.id, template.title_template)
    db.commit()
    db.refresh(template)
    return template


@router.put("/campaign-templates/{template_id}", response_model=CampaignTemplateOut)
def admin_update_template(
    template_id: int,
    payload: CampaignTemplateIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    template = db.get(CampaignTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Шаблон не найден")
    for field, value in payload.model_dump().items():
        setattr(template, field, value)
    _log(db, admin, "update", "campaign_template", template.id)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/campaign-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_template(template_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    template = db.get(CampaignTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Шаблон не найден")
    db.delete(template)
    _log(db, admin, "delete", "campaign_template", template_id, template.title_template)
    db.commit()
    return None


# ---------- Business types ----------

@router.get("/business-types", response_model=list[BusinessTypeOptionOut])
def admin_list_business_types(db: Session = Depends(get_db)):
    return db.query(BusinessTypeOption).all()


@router.post("/business-types", response_model=BusinessTypeOptionOut, status_code=status.HTTP_201_CREATED)
def admin_create_business_type(
    payload: BusinessTypeOptionIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    if db.query(BusinessTypeOption).filter(BusinessTypeOption.key == payload.key).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Такой тип бизнеса уже существует")
    option = BusinessTypeOption(**payload.model_dump())
    db.add(option)
    db.flush()
    _log(db, admin, "create", "business_type", option.id, option.label)
    db.commit()
    db.refresh(option)
    return option


@router.put("/business-types/{option_id}", response_model=BusinessTypeOptionOut)
def admin_update_business_type(
    option_id: int,
    payload: BusinessTypeOptionIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    option = db.get(BusinessTypeOption, option_id)
    if option is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тип бизнеса не найден")
    for field, value in payload.model_dump().items():
        setattr(option, field, value)
    _log(db, admin, "update", "business_type", option.id)
    db.commit()
    db.refresh(option)
    return option


@router.delete("/business-types/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_business_type(option_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    option = db.get(BusinessTypeOption, option_id)
    if option is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тип бизнеса не найден")
    db.delete(option)
    _log(db, admin, "delete", "business_type", option_id, option.label)
    db.commit()
    return None


# ---------- Platform stats & users ----------

@router.get("/users", response_model=list[AdminUserOut])
def admin_list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    result = []
    for u in users:
        result.append(AdminUserOut(
            id=u.id,
            email=u.email,
            business_name=u.business_name,
            is_admin=u.is_admin,
            created_at=u.created_at,
            business_type=u.business.business_type if u.business else None,
        ))
    return result


@router.get("/stats", response_model=AdminStatsOut)
def admin_stats(db: Session = Depends(get_db)):
    total_businesses = db.query(Business).count()
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    active_businesses_30d = db.query(User).filter(User.created_at >= thirty_days_ago).count()

    total_campaigns = db.query(Campaign).count()
    active_campaigns = db.query(Campaign).filter(Campaign.status == "active").count()
    total_customers = db.query(Customer).count()

    tool_counts: dict[str, int] = {}
    for ut in db.query(UserTool).filter(UserTool.status == "activated").all():
        tool_counts[ut.tool.name] = tool_counts.get(ut.tool.name, 0) + 1
    popular_tools = sorted(
        [{"name": name, "activations": count} for name, count in tool_counts.items()],
        key=lambda x: x["activations"],
        reverse=True,
    )[:5]

    # Simple illustrative MRR model: paying businesses * a flat subscription price.
    subscription_price = 15000  # KZT / month, matches the "product worth paying for" pitch
    mrr_estimate = round(total_businesses * subscription_price, 2)

    return AdminStatsOut(
        total_businesses=total_businesses,
        active_businesses_30d=active_businesses_30d,
        total_campaigns=total_campaigns,
        active_campaigns=active_campaigns,
        total_customers=total_customers,
        popular_tools=popular_tools,
        mrr_estimate=mrr_estimate,
        system_health="operational",
    )
