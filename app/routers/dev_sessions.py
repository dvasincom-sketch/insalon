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
