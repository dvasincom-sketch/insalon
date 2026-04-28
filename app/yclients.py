import httpx
import os
from dotenv import load_dotenv

load_dotenv()

PARTNER_TOKEN = os.getenv("YCLIENTS_PARTNER_TOKEN", "").strip()
BASE_URL = "https://api.yclients.com/api/v1"

def get_auth_headers(user_token: str = None) -> dict:
    partner = PARTNER_TOKEN.encode("ascii", errors="ignore").decode("ascii")
    
    if user_token:
        user = user_token.encode("ascii", errors="ignore").decode("ascii")
        auth = f"Bearer {partner}, User {user}"
    else:
        auth = f"Bearer {partner}"
    
    return {
        "Accept": "application/vnd.api.v2+json",
        "Content-Type": "application/json",
        "Authorization": auth,
    }

async def get_user_token(login: str, password: str) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/auth",
            headers=get_auth_headers(),
            json={"login": login, "password": password}
        )
        data = response.json()
        if data.get("success"):
            return data["data"]["user_token"]
        raise Exception(f"Auth failed: {data}")

async def get_records(company_id: int, user_token: str, start_date: str, end_date: str, page: int = 1):
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/records/{company_id}",
            headers=get_auth_headers(user_token),
            params={
                "start_date": start_date,
                "end_date": end_date,
                "page": page,
                "count": 100
            }
        )
        return response.json()

async def get_clients(company_id: int, user_token: str, page: int = 1):
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/clients/{company_id}",
            headers=get_auth_headers(user_token),
            params={"page": page, "count": 200}
        )
        return response.json()