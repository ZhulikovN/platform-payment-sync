"""
Скрипт для исправления бюджета сделок в AmoCRM.
Находит все успешные платежи с amount=0 в SQLite,
берёт реальную сумму из payload (course_order.amount)
и обновляет бюджет сделки в AmoCRM через PATCH /api/v4/leads.

Запуск:

cd /home/deploy/platform-payment/releases/release_001/platform-payment-sync-main

# Сначала dry run
.venv/bin/python fix_zero_amount_leads.py --dry-run

    cd /home/deploy/platform-payment/releases/release_001/platform-payment-main
    python scripts/fix_zero_amount_leads.py

    # Dry run (только вывод, без изменений):
    python scripts/fix_zero_amount_leads.py --dry-run
"""

import argparse
import json
import sqlite3
import time
import sys

import httpx

# --- Настройки ---
DB_PATH = "/home/deploy/platform-payment/shared/db/payments.sqlite"
AMO_BASE_URL = "https://egeland.amocrm.ru"
AMO_TOKEN = None  # заполняется из .env

BATCH_SIZE = 50     # AmoCRM принимает до 50 сделок за раз
SLEEP_BETWEEN_BATCHES = 1.0  # секунды между батчами


def load_token() -> str:
    """Прочитать токен из .env файла."""
    try:
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if line.startswith("AMO_ACCESS_TOKEN=") and not line.startswith("#"):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    raise RuntimeError("AMO_ACCESS_TOKEN не найден в .env")


def get_zero_amount_leads(db_path: str) -> list[dict]:
    """Получить все сделки с amount=0 и реальной суммой из payload."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        """
        SELECT
            payment_id,
            lead_id,
            json_extract(payload, '$.course_order.amount') AS actual_amount,
            payment_date
        FROM payment_events
        WHERE amount = 0 AND status = 'success'
          AND lead_id IS NOT NULL
          AND json_extract(payload, '$.course_order.amount') > 0
        ORDER BY created_at
        """
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_lead_price(lead_id: int, headers: dict) -> int | None:
    """Получить текущий бюджет сделки из AmoCRM. None если сделка не найдена."""
    try:
        resp = httpx.get(
            f"{AMO_BASE_URL}/api/v4/leads/{lead_id}",
            headers=headers,
            timeout=30.0,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json().get("price", None)
    except Exception as e:
        print(f"  ОШИБКА при получении lead={lead_id}: {e}")
        return None


def patch_one_lead(lead_id: int, amount: int, headers: dict) -> bool:
    """Обновить бюджет сделки. Возвращает True если успешно."""
    try:
        resp = httpx.patch(
            f"{AMO_BASE_URL}/api/v4/leads",
            headers=headers,
            json=[{"id": lead_id, "price": amount}],
            timeout=30.0,
        )
        resp.raise_for_status()
        return True
    except httpx.HTTPStatusError as e:
        print(f"  ОШИБКА HTTP {e.response.status_code}: {e.response.text[:150]}")
        return False
    except Exception as e:
        print(f"  ОШИБКА: {e}")
        return False


def patch_leads(leads: list[dict], token: str, dry_run: bool) -> None:
    """
    Обновить бюджет сделок в AmoCRM — только там где бюджет равен 0.
    Сохраняет лог в fix_results.csv с колонками:
    lead_id, previous_price, new_price, status
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    total = len(leads)
    updated = 0
    skipped_nonzero = 0
    not_found = 0
    errors = 0

    log_rows = []

    for idx, row in enumerate(leads, start=1):
        lead_id = row["lead_id"]
        amount = row["actual_amount"]
        payment_id = row["payment_id"]

        print(f"[{idx}/{total}] lead={lead_id} payment={payment_id}", end="")

        if dry_run:
            print(f" → new_price={amount} [DRY RUN]")
            log_rows.append(f"{lead_id},?,{amount},dry_run")
            updated += 1
            continue

        current_price = get_lead_price(lead_id, headers)
        time.sleep(0.35)

        if current_price is None:
            print(" → НЕ НАЙДЕНА")
            log_rows.append(f"{lead_id},not_found,{amount},skipped")
            not_found += 1
            continue

        if current_price != 0:
            print(f" → бюджет уже {current_price}, пропускаем")
            log_rows.append(f"{lead_id},{current_price},{amount},skipped_nonzero")
            skipped_nonzero += 1
            continue

        # Текущий бюджет = 0, обновляем
        ok = patch_one_lead(lead_id, amount, headers)
        time.sleep(0.35)

        if ok:
            print(f" → 0 → {amount} OK")
            log_rows.append(f"{lead_id},0,{amount},updated")
            updated += 1
        else:
            log_rows.append(f"{lead_id},0,{amount},error")
            errors += 1

    # Сохранить лог
    with open("fix_results.csv", "w") as f:
        f.write("lead_id,previous_price,new_price,status\n")
        f.write("\n".join(log_rows))
    print(f"\nЛог сохранён: fix_results.csv")

    print(f"\n--- Итог ---")
    print(f"Всего: {total}")
    print(f"Обновлено (было 0): {updated}")
    print(f"Пропущено (не 0): {skipped_nonzero}")
    print(f"Не найдено: {not_found}")
    print(f"Ошибок: {errors}")


def main():
    parser = argparse.ArgumentParser(description="Исправление бюджета сделок с amount=0")
    parser.add_argument("--dry-run", action="store_true", help="Только вывод, без изменений в AmoCRM")
    args = parser.parse_args()

    print(f"Режим: {'DRY RUN' if args.dry_run else 'PROD (реальные изменения)'}")
    print(f"БД: {DB_PATH}")

    token = load_token()
    print(f"Токен: {token[:30]}...")

    leads = get_zero_amount_leads(DB_PATH)
    print(f"\nНайдено сделок с amount=0: {len(leads)}")

    if not leads:
        print("Нечего исправлять.")
        return

    # Показать первые 5
    print("\nПримеры:")
    for row in leads[:5]:
        print(f"  lead={row['lead_id']} actual_amount={row['actual_amount']} payment={row['payment_id']}")

    if not args.dry_run:
        confirm = input(f"\nОбновить {len(leads)} сделок в AmoCRM? (yes/no): ")
        if confirm.strip().lower() != "yes":
            print("Отменено.")
            sys.exit(0)

    patch_leads(leads, token, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
