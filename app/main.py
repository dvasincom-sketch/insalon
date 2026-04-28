from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import json

load_dotenv()

from app.routers import sync, analytics, oauth, webhooks

app = FastAPI(
    title="Insalon API",
    description="API для управленческой аналитики салонов красоты на базе YCLIENTS",
    version="1.0.0"
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


@app.get("/", tags=["Система"])
async def root():
    return {"status": "ok", "project": "Insalon", "version": "1.0.0"}