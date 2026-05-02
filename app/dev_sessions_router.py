"""
FastAPI router for dev_sessions.
Add to main.py:
    from dev_sessions_router import router as dev_sessions_router
    app.include_router(dev_sessions_router)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date
import os
from supabase import create_client

router = APIRouter(prefix="/api/dev-sessions", tags=["dev-sessions"])

def get_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)


class DevSessionCreate(BaseModel):
    date: date
    feature: str
    category: str  # analytics | dev | design
    duration_min: int
    tokens_approx: Optional[int] = 0
    cost_usd: Optional[float] = 0.0
    notes: Optional[str] = None


@router.get("")
async def list_sessions(category: Optional[str] = None):
    sb = get_supabase()
    query = sb.table("dev_sessions").select("*").order("date", desc=True)
    if category:
        query = query.eq("category", category)
    result = query.execute()
    return result.data


@router.post("")
async def create_session(session: DevSessionCreate):
    sb = get_supabase()
    data = session.dict()
    data["date"] = str(data["date"])
    result = sb.table("dev_sessions").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Insert failed")
    return result.data[0]


@router.get("/stats")
async def get_stats():
    sb = get_supabase()
    result = sb.table("dev_sessions").select("*").execute()
    sessions = result.data or []

    stats = {"total_hours": 0, "total_tokens": 0, "total_cost_usd": 0, "by_category": {}}
    for s in sessions:
        cat = s["category"]
        mins = s.get("duration_min", 0) or 0
        tokens = s.get("tokens_approx", 0) or 0
        cost = float(s.get("cost_usd", 0) or 0)
        stats["total_hours"] += mins / 60
        stats["total_tokens"] += tokens
        stats["total_cost_usd"] += cost
        if cat not in stats["by_category"]:
            stats["by_category"][cat] = {"hours": 0, "tokens": 0, "cost_usd": 0}
        stats["by_category"][cat]["hours"] += mins / 60
        stats["by_category"][cat]["tokens"] += tokens
        stats["by_category"][cat]["cost_usd"] += cost

    stats["total_hours"] = round(stats["total_hours"], 2)
    stats["total_cost_usd"] = round(stats["total_cost_usd"], 4)
    for cat in stats["by_category"]:
        stats["by_category"][cat]["hours"] = round(stats["by_category"][cat]["hours"], 2)
        stats["by_category"][cat]["cost_usd"] = round(stats["by_category"][cat]["cost_usd"], 4)

    return stats


@router.delete("/{session_id}")
async def delete_session(session_id: int):
    sb = get_supabase()
    result = sb.table("dev_sessions").delete().eq("id", session_id).execute()
    return {"deleted": session_id}
