from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import json
import os

load_dotenv()

# Корень репозитория (родитель каталога app/) — чтобы пути к статике не зависели
# от рабочего каталога, из которого платформа (Timeweb) запускает процесс.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="Insalon API",
    description="API для управленческой аналитики салонов на базе YCLIENTS",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"
    def render(self, content) -> bytes:
        return json.dumps(content, ensure_ascii=False, allow_nan=False, indent=None, separators=(",", ":")).encode("utf-8")

app.router.default_response_class = UTF8JSONResponse

from app.routers import sync, analytics, oauth, webhooks, checks, payroll, booking, payments, dev_sessions, lovi, auth, obligations
app.include_router(sync.router)
app.include_router(analytics.router)
app.include_router(oauth.router)
app.include_router(webhooks.router)
app.include_router(checks.router)
app.include_router(payroll.router)
app.include_router(booking.router)
app.include_router(payments.router)
app.include_router(dev_sessions.router)
app.include_router(lovi.router)
app.include_router(auth.router)
app.include_router(obligations.router)


def _p(*parts):
    return os.path.join(BASE_DIR, *parts)

# Статические дашборды: v3 — рабочий дашборд салона, v2 — legacy.
# Пути от корня репозитория, а не от CWD (иначе на Timeweb маунты не создавались).
if os.path.isdir(_p("static")):
    app.mount("/dashboard", StaticFiles(directory=_p("static"), html=True), name="static")
if os.path.isdir(_p("static", "v2")):
    app.mount("/v2", StaticFiles(directory=_p("static", "v2"), html=True), name="static_v2")
if os.path.isdir(_p("static", "v3")):
    app.mount("/v3", StaticFiles(directory=_p("static", "v3"), html=True), name="static_v3")
if os.path.isdir(_p("static", "booking", "dist")):
    app.mount("/booking/assets", StaticFiles(directory=_p("static", "booking", "dist", "assets")), name="booking_assets")
    app.mount("/booking", StaticFiles(directory=_p("static", "booking", "dist"), html=True), name="booking")


@app.get("/healthz", tags=["Система"])
async def healthz():
    return {"status": "ok", "project": "Insalon", "version": "1.0.0"}


# Раздача React-фронта (single-app). WEB_DIR задаётся Dockerfile'ом; дефолт — от корня репо.
WEB_DIR = os.getenv("WEB_DIR") or _p("web")

if os.path.isdir(WEB_DIR):
    _assets_dir = os.path.join(WEB_DIR, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="web_assets")
    _NON_SPA = {"api", "sync", "analytics", "payments", "payroll", "checks",
                "obligations", "dev-sessions", "webhook", "dashboard", "v2", "v3",
                "booking", "docs", "redoc", "openapi.json", "assets", "healthz"}

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        head = full_path.split("/", 1)[0]
        if head in _NON_SPA:
            raise HTTPException(status_code=404)
        candidate = os.path.join(WEB_DIR, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        index = os.path.join(WEB_DIR, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        raise HTTPException(status_code=404)
else:
    @app.get("/", tags=["Система"])
    async def root():
        return {"status": "ok", "project": "Insalon", "version": "1.0.0"}
