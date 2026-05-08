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
async def get_staff(company_id: int, user_token: str):
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        response = await client.get(
            f"{BASE_URL}/company/{company_id}/staff",
            headers=get_auth_headers(user_token)
        )
        return response.json()

async def get_services(company_id: int, user_token: str):
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        response = await client.get(
            f"{BASE_URL}/services/{company_id}",
            headers=get_auth_headers(user_token)
        )
        return response.json()

async def get_transactions(company_id: int, user_token: str, start_date: str, end_date: str, page: int = 1):
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        response = await client.get(
            f"{BASE_URL}/transactions/{company_id}",
            headers=get_auth_headers(user_token),
            params={
                "start_date": start_date,
                "end_date": end_date,
                "page": page,
                "count": 100
            }
        )
        return response.json()

async def get_service_categories(company_id: int, user_token: str):
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        response = await client.get(
            f"{BASE_URL}/service_categories/{company_id}",
            headers=get_auth_headers(user_token)
        )
        return response.json()

def create_client_sync(company_id: int, user_token: str, name: str, phone: str, email: str = ""):
    with httpx.Client(timeout=30.0, verify=False) as client:
        response = client.post(
            f"{BASE_URL}/clients/{company_id}",
            headers=get_auth_headers(user_token),
            json={"name": name, "phone": phone, "email": email}
        )
        result = response.json()
        print(f"[YCLIENTS] create_client response: {result}")
        return result

def create_record_sync(company_id: int, user_token: str, data: dict):
    with httpx.Client(timeout=5.0, verify=False) as client:
        response = client.post(
            f"{BASE_URL}/records/{company_id}",
            headers=get_auth_headers(user_token),
            json=data
        )
        return response.json()

async def create_client(company_id: int, user_token: str, name: str, phone: str, email: str = ""):
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, create_client_sync, company_id, user_token, name, phone, email)

async def create_record(company_id: int, user_token: str, data: dict):
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, create_record_sync, company_id, user_token, data)

def find_client_by_phone_sync(company_id: int, user_token: str, phone: str):
    with httpx.Client(timeout=30.0, verify=False) as client:
        response = client.get(
            f"{BASE_URL}/clients/{company_id}",
            headers=get_auth_headers(user_token),
            params={"fields": "id,name,phone", "phone": phone, "count": 50}
        )
        data = response.json()
        print(f"[YCLIENTS] find_client_by_phone phone={phone} result={data.get('meta')}")
        clients = data.get("data", [])
        if clients:
            return clients[0]
        return None

async def find_client_by_phone(company_id: int, user_token: str, phone: str):
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, find_client_by_phone_sync, company_id, user_token, phone)

def get_book_times_sync(company_id: int, user_token: str, date: str, service_id: int, staff_id: int = 0):
    with httpx.Client(timeout=15.0, verify=False) as client:
        response = client.get(
            f"{BASE_URL}/book_times/{company_id}/{staff_id}/{date}",
            headers=get_auth_headers(user_token),
            params={"service_ids[]": service_id}
        )
        return response.json()

async def get_book_times(company_id: int, user_token: str, date: str, service_id: int, staff_id: int = 0):
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_book_times_sync, company_id, user_token, date, service_id, staff_id)
