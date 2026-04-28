import os
import httpx
from dotenv import load_dotenv

load_dotenv()

PARTNER_TOKEN = os.getenv("YCLIENTS_PARTNER_TOKEN", "").strip()
BASE_URL = "https://api.yclients.com/api/v1"

def get_connect_url() -> str:
    """Ссылка для подключения салона"""
    return "https://yclients.com/e/mp_41238_check/"

async def exchange_token(user_token: str) -> dict:
    """Получить информацию о пользователе по его токену"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/user",
            headers={
                "Accept": "application/vnd.api.v2+json",
                "Authorization": f"Bearer {PARTNER_TOKEN}, User {user_token}"
            }
        )
        return response.json()

async def get_user_companies(user_token: str) -> dict:
    """Получить список филиалов пользователя"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/companies",
            headers={
                "Accept": "application/vnd.api.v2+json",
                "Authorization": f"Bearer {PARTNER_TOKEN}, User {user_token}"
            },
            params={"my": 1}
        )
        return response.json()