from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import date
import os
from supabase import create_client

router = APIRouter(prefix="/dev-sessions", tags=["dev-sessions"])

def get_sb():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

class DevSessionCreate(BaseModel):
    date: date
    feature: str
    category: str
    duration_min: int = 0
    tokens_approx: Optional[int] = 0
    cost_usd: Optional[float] = 0.0
    notes: Optional[str] = None

@router.get("")
async def list_sessions(category: Optional[str] = None):
    q = get_sb().table("dev_sessions").select("*").order("date", desc=True)
    if category:
        q = q.eq("category", category)
    return q.execute().data

@router.post("")
async def create_session(s: DevSessionCreate):
    data = s.dict()
    data["date"] = str(data["date"])
    return get_sb().table("dev_sessions").insert(data).execute().data[0]

@router.get("/stats")
async def get_stats():
    rows = get_sb().table("dev_sessions").select("*").execute().data or []
    stats = {"total_hours": 0, "total_tokens": 0, "by_category": {}}
    for r in rows:
        cat  = r["category"]
        mins = r.get("duration_min", 0) or 0
        tok  = r.get("tokens_approx", 0) or 0
        stats["total_hours"]  += mins / 60
        stats["total_tokens"] += tok
        if cat not in stats["by_category"]:
            stats["by_category"][cat] = {"hours": 0, "tokens": 0}
        stats["by_category"][cat]["hours"]  += mins / 60
        stats["by_category"][cat]["tokens"] += tok
    stats["total_hours"] = round(stats["total_hours"], 2)
    for c in stats["by_category"]:
        stats["by_category"][c]["hours"] = round(stats["by_category"][c]["hours"], 2)
    return stats


# ── Backlog ────────────────────────────────────────────────────────────────────

class BacklogItem(BaseModel):
    feature: str
    category: str
    priority: str = 'P1'
    planned_hours: Optional[float] = 0
    planned_tokens: Optional[int] = 0
    planned_date: Optional[date] = None
    notes: Optional[str] = None

class BacklogUpdate(BaseModel):
    planned_hours: Optional[float] = None
    planned_tokens: Optional[int] = None
    planned_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None

@router.get("/backlog")
async def list_backlog(status: Optional[str] = 'open'):
    q = get_sb().table("dev_backlog").select("*").order("priority").order("created_at")
    if status:
        q = q.eq("status", status)
    return q.execute().data

@router.post("/backlog")
async def create_backlog_item(item: BacklogItem):
    data = item.dict()
    if data.get("planned_date"):
        data["planned_date"] = str(data["planned_date"])
    return get_sb().table("dev_backlog").insert(data).execute().data[0]

@router.patch("/backlog/{item_id}")
async def update_backlog_item(item_id: int, upd: BacklogUpdate):
    data = {k: v for k, v in upd.dict().items() if v is not None}
    if "planned_date" in data:
        data["planned_date"] = str(data["planned_date"])
    return get_sb().table("dev_backlog").update(data).eq("id", item_id).execute().data[0]
