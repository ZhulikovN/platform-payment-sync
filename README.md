# platform-payment-sync

Сервис автоматической фиксации оплат с платформы pl.el-ed.ru в amoCRM.

Документация: https://wiki.pushka228.ru/doc/platforma-platezh-sinhronizaciya-8Vr7cYH0ul

## Описание

Проект предназначен для автоматической синхронизации данных об успешных оплатах курсов с платформы pl.el-ed.ru в систему
amoCRM. Сервис принимает webhook от платформы при каждой успешной оплате и автоматически:

- Находит или создает контакт в amoCRM по Telegram ID, телефону или email
- Находит или создает активную сделку для контакта
- Обновляет кастомные поля сделки (сумма оплаты, предметы, направление курса)
- Создает примечание в сделке с полной информацией об оплате
- Инкрементально обновляет общий оплаченный итог и счетчик покупок

## Основная логика работы

### Поток обработки оплаты

```
Платформа pl.el-ed.ru (успешная оплата)
    ↓
POST /webhook/payment + HMAC подпись
    ↓
FastAPI endpoint (проверка подписи)
    ↓
PaymentProcessor (бизнес-логика)
    ↓
1. Поиск контакта (tg_id → phone → email)
2. Создание контакта (если не найден и CREATE_IF_NOT_FOUND=True)
3. Обновление полей контакта (tg_id, tg_username - только пустые)
4. Поиск активной сделки (во ВСЕХ воронках через filter[query])
5. Создание сделки (если не найдена и CREATE_IF_NOT_FOUND=True, в AMO_PIPELINE_ID)
6. Обновление полей сделки:
   - Предметы (маппинг: "Русский" → enum_id)
   - Направление курса (ЕГЭ/ОГЭ)
   - Сумма последней оплаты
   - Общий оплаченный итог (инкрементально: старое + новое)
   - Счетчик покупок (инкрементально: +1)
   - Дата/время последней оплаты
   - Payment ID, Invoice ID
7. Создание примечания в сделке
    ↓
AmoCRM API (обновление данных)
```

## Архитектура проекта

```
platform-payment-sync/
├── app/                          # Основной код приложения
│   ├── api/                      # REST API endpoints
│   │   ├── __init__.py
│   │   └── webhook_payment.py   # POST /webhook/payment - прием оплат
│   ├── core/                     # Основная логика
│   │   ├── __init__.py
│   │   ├── amocrm_client.py     # Клиент для amoCRM API
│   │   ├── amocrm_mappings.py   # Маппинг предметов и направлений
│   │   └── settings.py          # Настройки приложения (Pydantic)
│   ├── db/                       # Работа с базой данных
│   │   ├── __init__.py
│   │   └── event_logger.py      # Логирование событий в SQLite
│   ├── models/                   # Pydantic модели
│   │   ├── __init__.py
│   │   └── payment_webhook.py   # Модели для валидации webhook
│   ├── services/                 # Бизнес-логика
│   │   ├── __init__.py
│   │   └── payment_processor.py # Обработка оплат
│   └── main.py                   # FastAPI приложение
├── db/                           # База данных SQLite
│   └── payments.sqlite          # Логи всех webhook событий
├── etc/                          # Конфигурационные файлы
│   └── systemd/                 # Systemd unit файлы
│       └── platform-payment-sync.service
├── tests/                        # Тесты
│   ├── test_find_contact/
│   ├── test_setup_contact/
│   └── test_config.py
├── .env                          # Переменные окружения (не в git)
├── env.example                   # Пример переменных окружения
├── pyproject.toml               # Зависимости Poetry
├── Makefile                      # Команды для разработки
└── README.md                     # Документация
```

## Описание модулей

### `webhook_payment.py`

FastAPI endpoint для приема webhook от платформы.

**Endpoints:**

- `POST /webhook/payment` - прием данных об оплате
    - Проверка HMAC-SHA256 подписи в заголовке `X-Signature`
    - Поддержка legacy метода: простой секрет в заголовке `X-Webhook-Secret`
    - Валидация JSON через Pydantic модели
    - Передача данных в `PaymentProcessor` для обработки
    - Возврат HTTP статусов:
        - `200 OK` - успешная обработка
        - `202 Accepted` - пропущено (правила исключения)
        - `401 Unauthorized` - неверная подпись/секрет
        - `404 Not Found` - контакт/сделка не найдены (при CREATE_IF_NOT_FOUND=False)
        - `409 Conflict` - дубликат (payment_id уже обработан)
        - `500 Internal Server Error` - ошибка обработки

- `GET /webhook/health` - health check сервиса

### `payment_processor.py`

Центральная бизнес-логика обработки оплат.

**Класс `PaymentProcessor`:**

Метод `process_payment(payment: PaymentWebhook)` выполняет полный цикл обработки:

1. **Проверка дубликата** по `payment_id` (TODO: через EventLogger)

2. **Матчинг контакта** через `find_contact()`:
    - Приоритет 1: Поиск по `telegram_id` через `filter[query]`
    - Приоритет 2: Поиск по `phone` через `filter[query]`
    - Приоритет 3: Поиск по `email` через `filter[query]`
    - Если не найден и `CREATE_IF_NOT_FOUND=True`: создание нового контакта
    - Если не найден и `CREATE_IF_NOT_FOUND=False`: возврат ошибки "contact_not_found"

3. **Обновление полей контакта** (идемпотентно):
    - `telegram_id` - заполнить только если пусто
    - `telegram_username` - заполнить только если пусто

4. **Матчинг активной сделки** через `find_active_lead()`:
    - Поиск сделок по телефону через `filter[query]` в `/api/v4/leads`
    - Поиск сделок по email через `filter[query]` в `/api/v4/leads`
    - Проверка, что найденная сделка связана с нужным контактом (по contact_id)
    - Фильтрация по статусу: не закрыта, не удалена
    - Выбор последней обновленной сделки (по `updated_at`)
    - **ВАЖНО**: Поиск во ВСЕХ воронках, не только в целевой
    - Если не найдена и `CREATE_IF_NOT_FOUND=True`: создание новой сделки в воронке `AMO_PIPELINE_ID`
    - Если не найдена и `CREATE_IF_NOT_FOUND=False`: возврат ошибки "lead_not_found"

5. **Обновление полей сделки**:
    - **Предметы** (`AMO_LEAD_FIELD_SUBJECTS`): маппинг названий через `SUBJECTS_MAPPING`
        - "Русский" → enum_id из настроек
        - "Математика" → enum_id из настроек
        - "Обществознание" → enum_id из настроек
        - и т.д. (см. `amocrm_mappings.py`)
    - **Направление курса** (`AMO_LEAD_FIELD_DIRECTION`): маппинг через `get_direction_enum_id()`
        - "ЕГЭ" → `AMO_DIRECTION_EGE`
        - "ОГЭ" → `AMO_DIRECTION_OGE`
    - **Сумма последней оплаты** (`AMO_LEAD_FIELD_LAST_PAYMENT_AMOUNT`): сумма всех курсов в заказе
    - **Общий оплаченный итог** (`AMO_LEAD_FIELD_TOTAL_PAID`): инкрементально (старое значение + новая сумма)
    - **Счетчик покупок** (`AMO_LEAD_FIELD_PURCHASE_COUNT`): инкрементально (+1)
    - **Дата/время последней оплаты** (`AMO_LEAD_FIELD_LAST_PAYMENT_DATE`): дата из webhook
    - **Payment ID** (`AMO_LEAD_FIELD_PAYMENT_ID`): ID оплаты
    - **Invoice ID** (`AMO_LEAD_FIELD_INVOICE_ID`): ID счета

6. **Создание примечания** в сделке с форматированным текстом:

```
Оплата проведена

Имя клиента: Иван Петров
Дата/время: 2025-01-20 14:49:20 (Moscow)
Дата/время UTC: 2025-01-20T14:49:20Z
Статус: CONFIRMED
Сумма: 10000 RUB
Метод оплаты: SBP
Курсы:
  Годовой 2к25 стандарт (Русский)
  Годовой 2к25 стандарт (Обществознание)
Промокод: PROMO2025
TGID: 123456789 | TG Username: @ivan | Телефон: +79991234567
Источник: platform
Invoice ID: inv_12345
Payment ID: pay_67890
```

### `amocrm_client.py`

Клиент для работы с amoCRM API. Все методы асинхронные.

**Основные методы:**

- `find_contact(tg_id, phone, email)` - поиск контакта с приоритетами
    - Использует `filter[query]` для универсального поиска
    - Возвращает первый найденный контакт

- `find_contact_by_custom_field(value)` - поиск по значению через `filter[query]`

- `find_contact_by_phone(phone)` - поиск по телефону через `filter[query]`

- `find_contact_by_email(email)` - поиск по email через `filter[query]`

- `find_active_lead(contact_id, phone, email)` - поиск активной сделки
    - Шаг 1: Поиск сделок по телефону и email через `filter[query]`
    - Шаг 2: Проверка, что сделка связана с нужным contact_id
    - Шаг 3: Фильтрация по статусу (не закрыта, не удалена)
    - Шаг 4: Выбор последней обновленной

- `create_contact(name, phone, email, tg_id, tg_username)` - создание контакта
    - Автоматическое заполнение кастомных полей

- `update_contact_fields(contact_id, tg_id, tg_username)` - обновление полей контакта
    - Идемпотентно: обновляет только пустые поля

- `create_lead(name, contact_id, price, utm_*)` - создание сделки
    - Создание в воронке `AMO_PIPELINE_ID` со статусом `AMO_DEFAULT_STATUS_ID`
    - Автоматическое добавление UTM меток

- `update_lead_fields(lead_id, ...)` - обновление полей сделки
    - Поддержка инкрементального обновления (total_paid, purchase_count)

- `add_lead_note(lead_id, text)` - добавление примечания в сделку

**Особенности:**

- Retry механизм через `tenacity` (3 попытки с exponential backoff)
- Обработка rate limits (429 status code)
- Автоматическая обработка пагинации
- Поддержка async/await через `httpx`

### `amocrm_mappings.py`

Маппинг между названиями из платформы и enum_id в amoCRM.

**Словарь `SUBJECTS_MAPPING`:**

```python
{
    "Русский": settings.AMO_SUBJECT_RUSSIAN,
    "Математика": settings.AMO_SUBJECT_MATH_BASE,
    "Обществознание": settings.AMO_SUBJECT_OBSHCHESTVO,
    "История": settings.AMO_SUBJECT_HISTORY,
    # ... и т.д.
}
```

**Словарь `DIRECTION_MAPPING`:**

```python
{
    "ЕГЭ": settings.AMO_DIRECTION_EGE,
    "ОГЭ": settings.AMO_DIRECTION_OGE,
}
```

**Функции:**

- `get_subject_enum_ids(subject_names)` - получить enum_id для списка предметов
- `get_direction_enum_id(direction_name)` - получить enum_id для направления

### `event_logger.py`

Логирование всех webhook событий в SQLite базу данных.

**Таблица `payment_events`:**

```sql
CREATE TABLE payment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_id TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    status TEXT NOT NULL,  -- pending, processing, success, failed, skipped, duplicate
    amount INTEGER,
    contact_id INTEGER,
    lead_id INTEGER,
    pipeline_id INTEGER,
    lead_created INTEGER,  -- 0 = найдена существующая, 1 = создана новая
    payload TEXT NOT NULL,  -- JSON
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);
```

**Методы:**

- `log_event(payment_data, status)` - логирование события
- `update_event_status(payment_id, status, ...)` - обновление статуса
- `is_payment_processed(payment_id)` - проверка на дубликат
- `get_failed_events()` - получение неудачных событий для retry
- `get_stats()` - получение статистики обработки

### `payment_webhook.py` (models)

Pydantic модели для валидации входящих данных.

**Структура данных от платформы:**

```json
{
  "course_order": {
    "status": "CONFIRMED",
    "amount": 100,
    "created_at": "2025-01-20 14:49:20",
    "updated_at": "2025-01-20 14:49:20",
    "code": "PROMO2025",
    "payment_id": "pay_123456",
    "invoice_id": "inv_789",
    "payment_method": "SBP",
    "currency": "RUB",
    "course_order_items": [
      {
        "cost": 5000,
        "number_lessons": 10,
        "course": {
          "name": "Годовой 2к25 стандарт",
          "subject": {
            "name": "Русский",
            "project": "ЕГЭ"
          }
        },
        "package_id": null
      }
    ],
    "user": {
      "first_name": "Иван",
      "last_name": "Петров",
      "phone": "89991234567",
      "email": "ivan@example.com",
      "telegram_id": "123456789",
      "telegram_tag": "ivan_petrov"
    },
    "utm": {
      "source": "platform",
      "medium": "direct",
      "compaign": "summer2025",
      "term": "",
      "content": "",
      "ym": "1234567890"
    },
    "domain": "pl.el-ed.ru"
  }
}
```

**ВАЖНО:** Поле `amount` в `course_order` НЕ используется. Реальная сумма оплаты вычисляется как сумма всех `cost` в
`course_order_items`.

## Логика поиска контактов и сделок

### Поиск контакта (приоритеты)

1. **По Telegram ID** (если передан):
   ```
   GET /api/v4/contacts?query={telegram_id}&limit=50
   ```
    - Универсальный поиск через `filter[query]`
    - amoCRM ищет по всем полям контакта, включая кастомные

2. **По телефону** (если Telegram ID не найден):
   ```
   GET /api/v4/contacts?query={phone}&limit=50
   ```

3. **По email** (если телефон не найден):
   ```
   GET /api/v4/contacts?query={email}&limit=50
   ```

**Если контакт не найден:**

- При `CREATE_IF_NOT_FOUND=True`: создание нового контакта с UTM метками
- При `CREATE_IF_NOT_FOUND=False`: возврат ошибки 404

### Поиск активной сделки

**Алгоритм:**

1. **Поиск сделок по телефону и email:**
   ```
   GET /api/v4/leads?filter[query]={phone}&limit=50
   GET /api/v4/leads?filter[query]={email}&limit=50
   ```
    - Универсальный поиск amoCRM по всем полям сделки
    - Объединение результатов, удаление дубликатов

2. **Проверка принадлежности сделки контакту:**
   ```
   GET /api/v4/leads/{lead_id}?with=contacts
   ```
    - Проверка, что сделка связана с нужным `contact_id`
    - Если не связана - пропускаем эту сделку

3. **Фильтрация по статусу:**
    - Не удалена (`is_deleted` != true)
    - Не закрыта (статус не в списке: 63242022, 142, 143)
    - Есть `updated_at` > 0

4. **Выбор последней обновленной:**
    - Сортировка по `updated_at` по убыванию
    - Возврат первой сделки

**ВАЖНО:** Поиск ведется во ВСЕХ воронках, не только в `AMO_PIPELINE_ID`.

**Если сделка не найдена:**

- При `CREATE_IF_NOT_FOUND=True`: создание новой сделки в воронке `AMO_PIPELINE_ID` со статусом `AMO_DEFAULT_STATUS_ID`
- При `CREATE_IF_NOT_FOUND=False`: возврат ошибки 404

### Создание новой сделки

При создании новой сделки:

- **Воронка**: `AMO_PIPELINE_ID` (указывается в настройках)
- **Статус**: `AMO_DEFAULT_STATUS_ID` (указывается в настройках)
- **Название**: "Оплата {предмет} - {имя клиента}"
- **Бюджет**: Сумма всех курсов в заказе
- **UTM метки**: Автоматически добавляются из webhook

## Переменные окружения (.env)

## Воронки и статусы

### Три воронки для создания новых сделок

Система автоматически выбирает воронку на основе UTM меток из webhook:

#### 1. Воронка "Партнеры" (AMO_PIPELINE_PARTNERS=8598230)

**Условие:** `utm_source` содержит одно из значений: `advcake`, `flocktory`, `tutortop`, `sravni`, `tbank`, `reshuege`,
`ris.promo`, `gdeslon`, `admitad`, `pfm`

**Статус при создании:** `AMO_STATUS_AUTOPAY_PARTNERS=80517738` ("Автооплаты ООО")

**Пример:**

```json
"utm": {
"source": "advcake",
"medium": "cpa"
}
```

Сделка создается в воронке "Партнеры" со статусом "Автооплаты ООО".

#### 2. Воронка "Яндекс" (AMO_PIPELINE_YANDEX=10089806)

**Условие:** `utm_medium` содержит одно из значений: `cpc`, `el-ege`, `cpm`

**Статус при создании:** `AMO_STATUS_AUTOPAY_YANDEX=80579130` ("Автооплаты ООО")

**Пример:**

```json
"utm": {
"source": "yandex",
"medium": "cpc"
}
```

Сделка создается в воронке "Яндекс" со статусом "Автооплаты ООО".

#### 3. Воронка "Сайт" (AMO_PIPELINE_SITE=4423755)

**Условие:** По умолчанию, если не подходят условия для "Партнеров" или "Яндекса"

**Статус при создании:** `AMO_STATUS_AUTOPAY_SITE=63242022` ("Автооплаты ООО")

**Пример:**

```json
"utm": {
"source": "direct",
"medium": "organic"
}
```

Сделка создается в воронке "Сайт" со статусом "Автооплаты ООО".


### Поиск активной сделки

Поиск ведется **во ВСЕХ воронках**, не только в целевой. Это позволяет:

- Обновлять существующие сделки независимо от воронки
- Избежать создания дубликатов
- Работать с клиентами, у которых сделки в разных воронках

### Статусы сделок

**Статусы, которые исключаются при поиске активной сделки:**

- `63242022` - "Автооплаты ООО" в воронке "Сайт"
- `80579130` - "Автооплаты ООО" в воронке "Яндекс"
- `80517738` - "Автооплаты ООО" в воронке "Партнеры"
- `142` - "Закрыта успешно" (общий статус)
- `143` - "Закрыта неуспешно" (общий статус)

**ВАЖНО:** Если найдена активная сделка, она обновляется независимо от того, в какой воронке находится. Воронка
выбирается только при создании новой сделки.

## Установка

### Предварительные требования

- Python 3.12+
- Poetry для управления зависимостями
- Systemd (для автоматического запуска)
- Доступ к amoCRM API (долгосрочный токен)

## Использование

### Автоматический запуск

После настройки systemd сервис будет запускаться автоматически при загрузке сервера.

### Просмотр логов

```bash
# Логи в реальном времени
sudo journalctl -u platform-payment-sync -f

# Логи за последние 24 часа
sudo journalctl -u platform-payment-sync --since "24 hours ago"

# Только ошибки
sudo journalctl -u platform-payment-sync -p err
```

### Перезапуск сервиса

```bash
sudo systemctl restart platform-payment-sync
```

## Разработка

### Команды Makefile

```bash
# Форматирование кода
make format

# Проверка линтером
make lint

# Запуск тестов
make test

# Проверка типов
make mypy

# Форматирование + линтер + тесты
make dev
```

### Просмотр базы данных

```bash
sqlite3 db/payments.sqlite
```

Полезные SQL запросы:

```sql
-- Статистика по статусам
SELECT status, COUNT(*) FROM payment_events GROUP BY status;

-- Последние 10 событий
SELECT payment_id, status, amount, created_at FROM payment_events ORDER BY created_at DESC LIMIT 10;

-- События с ошибками
SELECT payment_id, error_message, created_at FROM payment_events WHERE status = 'failed';
```

## Контакты и автор

**Автор:** Nikita Zhulikov
**Email:** zhulikovnikita884@gmail.com