"""
Нарезает JSON с оплатами на батчи по 1000 и отправляет последовательно.

Использование:
  python3 split_and_send.py /Users/nikitazulikov/Documents/ELAND/x/initial_payments_amo.json          # только нарезать
  python3 split_and_send.py <путь_к_файлу.json> --send   # нарезать и отправить

Пример:
  python3 scripts/split_and_send.py /Users/nikitazulikov/Downloads/batch.json --send
"""

import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BATCH_SIZE = 1000
SERVER_URL = "http://5.129.203.166:8000/webhook/payment-batch"


def split_to_batches(data: list, batch_size: int) -> list[list]:
    return [data[i:i + batch_size] for i in range(0, len(data), batch_size)]


def send_batch(batch: list, batch_num: int, total_batches: int) -> bool:
    body = json.dumps(batch, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        SERVER_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            response_body = resp.read().decode("utf-8")
            print(f"  Батч {batch_num}/{total_batches}: {resp.status} {response_body[:120]}")
            return True
    except urllib.error.HTTPError as e:
        print(f"  Батч {batch_num}/{total_batches}: HTTP {e.code} — {e.read().decode()[:200]}")
        return False
    except Exception as e:
        print(f"  Батч {batch_num}/{total_batches}: Ошибка — {e}")
        return False


def main():
    send = "--send" in sys.argv

    # Путь к JSON файлу — первый аргумент (не --send)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("Ошибка: укажите путь к JSON файлу")
        print("Пример: python3 scripts/split_and_send.py /путь/к/файлу.json --send")
        sys.exit(1)

    input_file = Path(args[0])
    if not input_file.exists():
        print(f"Ошибка: файл не найден: {input_file}")
        sys.exit(1)

    print(f"Читаем {input_file.name}...")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Всего записей: {len(data)}")

    batches = split_to_batches(data, BATCH_SIZE)
    print(f"Батчей: {len(batches)} (по {BATCH_SIZE})")
    print(f"Последний батч: {len(batches[-1])} записей")
    print(f"Расчётное время обработки: ~{len(data) * 4 / 60:.0f} мин (~{len(data) * 4 / 3600:.1f} ч)")
    print()

    # Сохраняем батчи рядом с исходным файлом
    output_dir = input_file.parent / "batches"
    output_dir.mkdir(exist_ok=True)

    batch_files = []
    for i, batch in enumerate(batches, start=1):
        out_file = output_dir / f"batch_{i:02d}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(batch, f, ensure_ascii=False)
        batch_files.append(out_file)
        print(f"  Сохранён {out_file.name} ({len(batch)} записей)")

    print()
    print("Команды для ручной отправки:")
    print("-" * 60)
    for i, bf in enumerate(batch_files, start=1):
        print(f"curl -X POST {SERVER_URL} \\")
        print(f"  -H 'Content-Type: application/json' \\")
        print(f"  -d @{bf}")
        print()

    if not send:
        print("Для автоматической отправки запустите: python3 split_and_send.py --send")
        return

    # Отправляем последовательно
    print("=" * 60)
    print(f"Отправляем на {SERVER_URL}")
    print("=" * 60)

    succeeded = 0
    failed = 0

    for i, batch in enumerate(batches, start=1):
        print(f"\nОтправка батча {i}/{len(batches)} ({len(batch)} записей)...")
        ok = send_batch(batch, i, len(batches))
        if ok:
            succeeded += 1
        else:
            failed += 1

        # Пауза между батчами чтобы не перегружать
        if i < len(batches):
            print(f"  Пауза 3 сек...")
            time.sleep(3)

    print()
    print("=" * 60)
    print(f"Готово: {succeeded} батчей приняты, {failed} ошибок")
    print(f"Обработка идёт на сервере в фоне ~{len(data) * 4 / 60:.0f} мин")
    print("Следить за прогрессом:")
    print("  ssh deploy@5.129.203.166 'sudo journalctl -u platform-payment -f'")
    print("=" * 60)


if __name__ == "__main__":
    main()
