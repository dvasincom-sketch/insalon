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

# Правила категоризации расходов салона
def categorize(description: str, category: str) -> str:
    desc = description.lower()
    cat = category.lower()

    # Пополнение с расчётного счёта — не расход
    if "пополнение" in desc and "предприниматель" in desc:
        return "transfer_in"

    # Внутренние переводы между своими счетами
    if "между своими" in desc:
        return "internal"

    # Зарплаты — переводы на имена сотрудников
    salon_staff = ["александра", "светлана", "екатерина", "анна", "анастасия",
                   "юлия", "ольга", "наталья", "мария"]
    if any(name in desc for name in salon_staff):
        return "salary"

    # Расходные материалы — косметика и красота
    if cat in ["красота", "аптеки", "здоровье"]:
        return "materials"
    if any(x in desc for x in ["л'этуаль", "золотое яблоко", "рив гош", "косметик"]):
        return "materials"

    # Аренда
    if any(x in desc for x in ["аренда", "rent"]):
        return "rent"

    # Еда и продукты — личное или для салона
    if cat in ["супермаркеты", "рестораны", "кафе"]:
        return "food"

    # Такси и транспорт
    if any(x in desc for x in ["яндекс такси", "uber", "ситимобил"]):
        return "transport"

    return "other"

def parse_amount(amount_str: str) -> float:
    try:
        return float(amount_str.replace(",", ".").replace(" ", ""))
    except:
        return 0.0

def parse_datetime(dt_str: str):
    try:
        return datetime.strptime(dt_str.strip(), "%d.%m.%Y %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
    except:
        return None

def import_csv(filepath: str):
    rows = []

    with open(filepath, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            status = row.get("Статус", "").strip()
            if status != "OK":
                continue

            dt = parse_datetime(row.get("Дата операции", ""))
            date = dt[:10] if dt else None
            if not date:
                continue

            amount = parse_amount(row.get("Сумма платежа", "0"))
            category = row.get("Категория", "").strip()
            description = row.get("Описание", "").strip()
            card = row.get("Номер карты", "").strip()
            mcc = row.get("MCC", "").strip()
            cashback = parse_amount(row.get("Кэшбэк", "0") or "0")

            expense_category = categorize(description, category)

            rows.append({
                "company_id": COMPANY_ID,
                "datetime": dt,
                "date": date,
                "card": card,
                "status": status,
                "amount": amount,
                "category": category,
                "mcc": mcc,
                "description": description,
                "cashback": cashback,
                "expense_category": expense_category
            })

    print(f"Всего строк: {len(rows)}")

    # Статистика по категориям
    from collections import Counter
    cats = Counter(r["expense_category"] for r in rows)
    print("\nКатегории:")
    for cat, count in cats.most_common():
        total = sum(r["amount"] for r in rows if r["expense_category"] == cat)
        print(f"  {cat}: {count} операций, сумма: {total:,.0f} ₽")

    # Загружаем батчами
    batch_size = 100
    saved = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        result = supabase.table("personal_transactions").insert(batch).execute()
        saved += len(result.data)

    print(f"\nГотово! Загружено {saved} транзакций")

if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "personal.csv"
    import_csv(filepath)
