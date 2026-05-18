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

def parse_amount(amount_str: str, op_type: str) -> float:
    try:
        amount = float(amount_str.strip().replace(",", ".").replace(" ", ""))
        if op_type == "Дебет":
            amount = -amount
        return amount
    except:
        return 0.0

def parse_date(date_str: str):
    try:
        return datetime.strptime(date_str.strip(), "%d.%m.%Y").strftime("%Y-%m-%d")
    except:
        return None

def import_csv(filepath: str):
    rows = []
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
            amount = parse_amount(amount_str, op_type)
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

    # Дедупликация перед отправкой
    seen = set()
    deduped = []
    for r in rows:
        key = (r['company_id'], r['date'], r['amount'], r['description'], r['counterparty'])
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    rows = deduped
    print(f"Всего строк в файле: {len(rows)} (после дедупликации)")
    batch_size = 100
    saved = 0
    skipped = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        result = supabase.table("bank_transactions").upsert(
            batch,
            on_conflict="company_id,date,amount,description,counterparty"
        ).execute()
        saved += len(result.data)
        print(f"Обработано: {i+len(batch)}/{len(rows)}")

    print(f"Готово! Upsert {saved} транзакций (дубли пропущены автоматически)")

if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "bank.csv"
    import_csv(filepath)
