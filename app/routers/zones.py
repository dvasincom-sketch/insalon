# app/routers/zones.py
# Прокси к 2GIS Catalog API + Supabase-кэш
# Подключить в app/main.py:
#   from app.routers import zones
#   app.include_router(zones.router)

import os
import asyncio
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client

# Без prefix — добавляем полный путь прямо в декораторах
# чтобы не конфликтовать с lovi.router у которого тоже /api/lovi
router = APIRouter(tags=["zones"])

DGIS_KEY  = os.getenv("DGIS_API_KEY")
DGIS_BASE = "https://catalog.api.2gis.com/3.0/items"


def get_supabase():
    """Lazy client — создаётся при вызове, не при импорте модуля."""
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY"),
    )


# ─── Схемы ──────────────────────────────────────────────────────────────────

class ZoneInput(BaseModel):
    id: str
    lat: float
    lon: float
    radius: int = 600


class RefreshRequest(BaseModel):
    zones: list[ZoneInput]


# ─── 2GIS запрос ────────────────────────────────────────────────────────────

async def fetch_2gis(lat: float, lon: float, radius: int, q: str = "массаж") -> list[dict]:
    params = {
        "q": q,
        "point": f"{lon},{lat}",
        "radius": radius,
        "type": "branch",
        "fields": "items.point,items.address_name,items.reviews,items.rubrics,items.id",
        "page_size": 50,
        "key": DGIS_KEY,
        "locale": "ru_RU",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(DGIS_BASE, params=params)
        r.raise_for_status()
        data = r.json()

    raw = data.get("result", {}).get("items") or data.get("items") or []

    items = []
    for it in raw:
        reviews = it.get("reviews") or {}
        rating_raw = reviews.get("rating_frequency")
        items.append({
            "dgis_id":       it.get("id"),
            "name":          it.get("name", ""),
            "address":       it.get("address_name") or (it.get("address") or {}).get("name", ""),
            "rating":        f"{float(rating_raw):.1f}" if rating_raw else None,
            "reviews_count": reviews.get("general_review_count_with_stars"),
            "lat":           (it.get("point") or {}).get("lat"),
            "lon":           (it.get("point") or {}).get("lon"),
            "rubrics":       [r["name"] for r in (it.get("rubrics") or [])[:3]],
        })
    return items


# ─── Дедупликация ────────────────────────────────────────────────────────────

def deduplicate(zone_items_map: dict) -> dict:
    """Один объект 2GIS попадает только в одну зону — первую по порядку."""
    seen: set = set()
    result: dict = {}
    for zone_id, items in zone_items_map.items():
        filtered = []
        for item in items:
            if item.get("dgis_id"):
                key = f"id:{item['dgis_id']}"
            else:
                key = f"na:{item['name'].lower()}|{item['address'][:20].lower()}"
            if key in seen:
                continue
            seen.add(key)
            filtered.append(item)
        result[zone_id] = filtered
    return result


# ─── GET /api/lovi/zones/search?zone_id=... ──────────────────────────────────

@router.get("/api/lovi/zones/search")
async def zones_search(zone_id: str):
    """Читает данные зоны из Supabase-кэша. Если нет — cache_miss: true."""
    try:
        result = (
            get_supabase()
            .table("zone_2gis_cache")
            .select("items, fetched_at")
            .eq("zone_id", zone_id)
            .maybe_single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not result.data:
        return {
            "zone_id":    zone_id,
            "count":      0,
            "items":      [],
            "fetched_at": None,
            "cache_miss": True,
        }

    items = result.data["items"]
    return {
        "zone_id":    zone_id,
        "count":      len(items),
        "items":      items,
        "fetched_at": result.data["fetched_at"],
        "cache_miss": False,
    }


# ─── POST /api/lovi/zones/refresh ────────────────────────────────────────────

@router.post("/api/lovi/zones/refresh")
async def zones_refresh(body: RefreshRequest):
    """
    Запрашивает 2GIS для всех переданных зон параллельно,
    дедуплицирует объекты, сохраняет в Supabase.
    Вызывается вручную с фронта кнопкой «Обновить данные».
    """
    if not DGIS_KEY:
        raise HTTPException(status_code=500, detail="DGIS_API_KEY не задан в окружении")

    async def fetch_safe(zone: ZoneInput):
        try:
            items = await fetch_2gis(zone.lat, zone.lon, zone.radius)
            return zone.id, items, None
        except Exception as e:
            return zone.id, [], str(e)

    results = await asyncio.gather(*[fetch_safe(z) for z in body.zones])

    zone_items_map = {zone_id: items for zone_id, items, _ in results}
    errors = [{"zone_id": z, "error": e} for z, _, e in results if e]

    deduped = deduplicate(zone_items_map)

    fetched_at = datetime.now(timezone.utc).isoformat()
    rows = [
        {"zone_id": zone_id, "items": items, "fetched_at": fetched_at}
        for zone_id, items in deduped.items()
    ]

    try:
        get_supabase().table("zone_2gis_cache").upsert(rows, on_conflict="zone_id").execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase error: {e}")

    return {
        "ok":         True,
        "fetched_at": fetched_at,
        "zones":      [{"zone_id": k, "count": len(v)} for k, v in deduped.items()],
        "errors":     errors or None,
    }