import csv
import os
import sys
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

COMPANY_ID = int(os.getenv("YCLIENTS_COMPANY_ID"))

# Категории которые относятся к салону
SALON_CATEGORIES = [
    "эквайринг", "юkassa", "юкасса", "tinkoff", "тинькофф",
    "головы", "head spa", "spa", "массаж", "салон",
    "онлайн-оплата", "оплата услуг"
]

def is_salon_income(description: str, category: str) -> bool:
    """Определяем относится ли транзакция к салону"""
    desc_lower = description.lower()
    return any(keyword in desc_lower for keyword in SALON_CATEGORIES)

def parse_date(date_str: str):
    try:
        return datetime.strptime(date_str.strip(), "%d.%m.%Y").strftime("%Y-%m-%d")
    except:
        return None

def import_csv(filepath: str):
    rows = []
    skipped = 0
    
    with open(filepath, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            date = parse_date(row.get("Дата проведения", ""))
            if not date:
                continue
            
            op_type = row.get("Тип операции (пополнение/списание)", "").strip()
            category = row.get("Категория операции", "").strip()
            amount_str = row.get("Сумма в валюте счёта", "0").strip()
            description = row.get("Описание операции", "").strip()
            counterparty = row.get("Наименование контрагента", "").strip()
            inn = row.get("ИНН контрагента", "").strip()
            
            try:
                amount = float(amount_str)
            except:
                amount = 0
            
            # Для дебета делаем сумму отрицательной
            if op_type == "Дебет":
                amount = -amount
            
            rows.append({
                "company_id": COMPANY_ID,
                "date": date,
                "type": op_type,
                "category": category,
                "amount": amount,
                "description": description,
                "counterparty": counterparty,
                "inn": inn
            })
    
    print(f"Всего строк: {len(rows)}")
    
    # Загружаем батчами по 100
    batch_size = 100
    saved = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        result = supabase.table("bank_transactions").insert(batch).execute()
        saved += len(result.data)
        print(f"Загружено: {saved}/{len(rows)}")
    
    print(f"Готово! Загружено {saved} транзакций")

if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "bank.csv"
    import_csv(filepath)