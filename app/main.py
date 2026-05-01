from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import json
import os

load_dotenv()

from app.routers import sync, analytics, oauth, webhooks, checks, payroll

app = FastAPI(
    title="Insalon API",
    description="API для управленческой аналитики салонов на базе YCLIENTS",
    version="1.0.0"
)

# CORS — разрешаем запросы с любого домена
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
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":")
        ).encode("utf-8")

app.router.default_response_class = UTF8JSONResponse

app.include_router(sync.router)
app.include_router(analytics.router)
app.include_router(oauth.router)
app.include_router(webhooks.router)
app.include_router(checks.router)
app.include_router(payroll.router)

# Статические файлы дашборда
if os.path.exists("static"):
    app.mount("/dashboard", StaticFiles(directory="static", html=True), name="static")
if os.path.exists("static/v2"):
    app.mount("/v2", StaticFiles(directory="static/v2", html=True), name="static_v2")
if os.path.exists("static/v3"):
    app.mount("/v3", StaticFiles(directory="static/v3", html=True), name="static_v3")  # АКТУАЛЬНАЯ ВЕРСИЯ


@app.get("/", tags=["Система"])
async def root():
    return {"status": "ok", "project": "Insalon", "version": "1.0.0"}