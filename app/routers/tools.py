import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import Category, Tool, User, UserTool
from app.schemas import ToolOut

router = APIRouter(prefix="/tools", tags=["tools"])


def _to_tool_out(tool: Tool, user_tool_status: dict[int, str]) -> ToolOut:
    status_for_tool = user_tool_status.get(tool.id)
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
        saved=status_for_tool in ("saved", "activated"),
        activated=status_for_tool == "activated",
    )


def _user_tool_status_map(db: Session, user_id: int) -> dict[int, str]:
    rows = db.query(UserTool).filter(UserTool.user_id == user_id).all()
    return {row.tool_id: row.status for row in rows}


@router.get("", response_model=list[ToolOut])
def list_tools(
    category: str | None = None,
    tool_type: str | None = None,
    favorites_only: bool = False,
    activated_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Tool).filter(Tool.is_active.is_(True))
    if category:
        query = query.join(Category).filter(Category.slug == category)
    if tool_type:
        query = query.filter(Tool.tool_type == tool_type)

    tools = query.all()
    status_map = _user_tool_status_map(db, current_user.id)

    if favorites_only:
        tools = [t for t in tools if status_map.get(t.id) in ("saved", "activated")]
    if activated_only:
        tools = [t for t in tools if status_map.get(t.id) == "activated"]

    return [_to_tool_out(t, status_map) for t in tools]


@router.get("/{tool_id}", response_model=ToolOut)
def get_tool(tool_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tool = db.get(Tool, tool_id)
    if tool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Инструмент не найден")
    status_map = _user_tool_status_map(db, current_user.id)
    return _to_tool_out(tool, status_map)


@router.post("/{tool_id}/favorite", response_model=ToolOut)
def toggle_favorite(tool_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tool = db.get(Tool, tool_id)
    if tool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Инструмент не найден")

    link = db.query(UserTool).filter(UserTool.user_id == current_user.id, UserTool.tool_id == tool_id).first()
    if link is None:
        db.add(UserTool(user_id=current_user.id, tool_id=tool_id, status="saved"))
    elif link.status == "saved":
        db.delete(link)
    # if activated, favoriting toggle does not downgrade an activated tool

    db.commit()
    status_map = _user_tool_status_map(db, current_user.id)
    return _to_tool_out(tool, status_map)


@router.post("/{tool_id}/activate", response_model=ToolOut)
def activate_tool(tool_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tool = db.get(Tool, tool_id)
    if tool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Инструмент не найден")

    link = db.query(UserTool).filter(UserTool.user_id == current_user.id, UserTool.tool_id == tool_id).first()
    if link is None:
        link = UserTool(user_id=current_user.id, tool_id=tool_id)
        db.add(link)
    link.status = "activated"
    link.activated_at = datetime.now(timezone.utc)

    db.commit()
    status_map = _user_tool_status_map(db, current_user.id)
    return _to_tool_out(tool, status_map)
