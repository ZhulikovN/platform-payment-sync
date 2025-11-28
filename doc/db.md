# База данных платежей (SQLite)

## Структура таблицы `payment_events`

### Описание полей

| Поле | Тип | Описание | Пример |
|------|-----|----------|--------|
| **id** | INTEGER | Первичный ключ (автоинкремент) | 1, 2, 3... |
| **payment_id** | TEXT | ID платежа в платформе (UNIQUE) | "7452942205" |
| **amount** | INTEGER | Сумма платежа в рублях | 9480 |
| **payment_date** | TEXT | Дата и время платежа | "2025-11-27 15:28:28" |
| **status** | TEXT | Статус обработки | "success", "error", "duplicate", "skipped" |
| **contact_id** | INTEGER | ID контакта в AmoCRM | 59569231 |
| **lead_id** | INTEGER | ID сделки в AmoCRM | 39445533 |
| **pipeline_id** | INTEGER | ID воронки в AmoCRM | 4423755 |
| **status_id** | INTEGER | ID этапа воронки в AmoCRM | 63242022 |
| **is_lead_created** | INTEGER | Была ли создана новая сделка (0/1) | 0 - найдена, 1 - создана |
| **retry_count** | INTEGER | Количество повторных попыток | 0, 1, 2... |
| **last_error** | TEXT | Текст последней ошибки | NULL или текст ошибки |
| **payload** | TEXT | Полный JSON webhook (для отладки) | "{...}" |
| **created_at** | TEXT | Дата и время получения webhook | "2025-11-27T14:31:15Z" |
| **processed_at** | TEXT | Дата и время успешной обработки | "2025-11-27T14:31:26Z" |

### Индексы

- `idx_payment_id` - по payment_id (для быстрого поиска дубликатов)
- `idx_contact_id` - по contact_id (для аналитики по клиентам)
- `idx_lead_id` - по lead_id (для поиска платежей по сделке)
- `idx_created_at` - по created_at (для выборки по датам)
- `idx_status` - по status (для статистики)

---

Открыть SQLite консоль

```bash
sqlite3 ~/platform-payment/current/db/payments.sqlite
```

---

## Полезные SQL-запросы

### Посмотреть все индексы

```sql
.indexes payment_events
```

### Включить красивый вывод

```sql
.mode column
.headers on
.width 10 15 10 10 15 15 10 10 15
```

---

### Последние 10 платежей

```sql
SELECT 
    id,
    payment_id,
    amount,
    status,
    contact_id,
    lead_id,
    pipeline_id,
    created_at
FROM payment_events
ORDER BY created_at DESC
LIMIT 10;
```

---

### Платежи за сегодня

```sql
SELECT 
    id,
    payment_id,
    amount,
    status,
    contact_id,
    lead_id,
    created_at
FROM payment_events
WHERE date(created_at) = date('now')
ORDER BY created_at DESC;
```

## Статистика

### Общая статистика по статусам

```sql
SELECT 
    status,
    COUNT(*) as count,
    SUM(amount) as total_amount
FROM payment_events
GROUP BY status
ORDER BY count DESC;
```

**Статусы:**
- `success` - успешно обработан
- `error` - ошибка обработки
- `duplicate` - дубликат (уже обрабатывался)
- `skipped` - пропущен

---

### Статистика по воронкам

```sql
SELECT 
    pipeline_id,
    COUNT(*) as count,
    SUM(amount) as total_amount
FROM payment_events
WHERE status = 'success' AND pipeline_id IS NOT NULL
GROUP BY pipeline_id
ORDER BY count DESC;
```

**Воронки:**
- `4423755` - Сайт
- `8598230` - Партнеры
- `10089806` - Яндекс

---

### Платежи с ошибками (последние 20)

```sql
SELECT 
    id,
    payment_id,
    amount,
    last_error,
    retry_count,
    created_at
FROM payment_events
WHERE status = 'error'
ORDER BY created_at DESC
LIMIT 20;
```

### Статистика за последние 7 дней

```sql
SELECT 
    date(created_at) as date,
    COUNT(*) as count,
    SUM(amount) as total_amount,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
FROM payment_events
WHERE datetime(created_at) >= datetime('now', '-7 days')
GROUP BY date(created_at)
ORDER BY date DESC;
```

## Обслуживание базы данных

### Размер базы данных

```bash
du -h payments.sqlite
```

---

### Количество записей в таблице

```sql
SELECT COUNT(*) as total_records FROM payment_events;
```

---

### Удалить записи старше 30 дней

```sql
DELETE FROM payment_events
WHERE datetime(created_at) < datetime('now', '-30 days');
```

**Внимание:** Это удалит данные безвозвратно!

---

### Экспорт данных в CSV

```bash
sqlite3 payments.sqlite -header -csv "SELECT * FROM payment_events WHERE date(created_at) = '2025-11-27';" > export_2025-11-27.csv
```

---

### Создать бэкап базы данных

```bash
cp payments.sqlite payments_backup_$(date +%Y%m%d_%H%M%S).sqlite
```

---

## Мониторинг в реальном времени

### Следить за новыми записями (Linux watch)

```bash
watch -n 5 "sqlite3 payments.sqlite 'SELECT id, payment_id, amount, status, created_at FROM payment_events ORDER BY created_at DESC LIMIT 5;'"
```

Обновляет каждые 5 секунд.

---

### Последний платеж (одной командой)

```bash
sqlite3 payments.sqlite "SELECT payment_id, amount, status, contact_id, lead_id, created_at FROM payment_events ORDER BY created_at DESC LIMIT 1;"
```

---

## Выход из SQLite

```sql
.quit
```

или

```sql
.exit
```

---
