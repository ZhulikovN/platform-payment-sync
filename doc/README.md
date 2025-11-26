# Event Logger - Логирование событий обработки платежей

## Назначение

Модуль `EventLogger` обеспечивает:

1. **Защиту от дубликатов** - предотвращает повторную обработку одного платежа
2. **Аналитику** - сохраняет данные для отчетов и анализа
3. **Отладку** - хранит полный payload для разбора ошибок

## Архитектура

Основано на паттерне из `amocrm-events-monitor` с использованием SQLite + aiosqlite.

## База данных

**Файл:** `db/payments.sqlite` (создается автоматически)

**Таблица:** `payment_events`

| Поле            | Тип     | Описание                        |
|-----------------|---------|---------------------------------|
| id              | INTEGER | PRIMARY KEY                     |
| payment_id      | TEXT    | UNIQUE - ID платежа             |
| amount          | INTEGER | Сумма платежа                   |
| payment_date    | TEXT    | Дата платежа                    |
| status          | TEXT    | success/duplicate/error/skipped |
| contact_id      | INTEGER | ID контакта в AmoCRM            |
| lead_id         | INTEGER | ID сделки в AmoCRM              |
| pipeline_id     | INTEGER | ID воронки                      |
| status_id       | INTEGER | ID этапа                        |
| is_lead_created | INTEGER | 1=создана, 0=найдена            |
| retry_count     | INTEGER | Количество повторов             |
| last_error      | TEXT    | Текст ошибки                    |
| payload         | TEXT    | Полный JSON webhook             |
| created_at      | TEXT    | Время получения                 |
| processed_at    | TEXT    | Время обработки                 |

**Индексы:**

- `idx_payment_id` - для быстрой проверки дубликатов
- `idx_contact_id` - для поиска по контактам
- `idx_lead_id` - для поиска по сделкам
- `idx_created_at` - для временных запросов
- `idx_status` - для фильтрации по статусу

## Интеграция с PaymentProcessor

Автоматически интегрирован в `PaymentProcessor`:

1. При инициализации создается `EventLogger`
2. В начале `process_payment` проверяется дубликат
3. При успехе логируется результат
4. При ошибке логируется ошибка
