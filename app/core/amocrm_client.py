"""Клиент для работы с AmoCRM API."""

import logging
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.settings import settings

logger = logging.getLogger(__name__)


class AmoCRMClient:
    """Клиент для взаимодействия с AmoCRM API."""

    def __init__(self) -> None:
        """Инициализация клиента AmoCRM."""
        self.base_url = settings.AMO_BASE_URL
        self.access_token = settings.AMO_ACCESS_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(settings.RETRY_MAX_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=settings.RETRY_WAIT_MIN, max=settings.RETRY_WAIT_MAX),
    )
    def _make_request(self, method: str, endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Выполнить HTTP запрос к AmoCRM API с retry механизмом.

        Args:
            method: HTTP метод (GET, POST, PATCH)
            endpoint: Endpoint API (например, /api/v4/contacts)
            data: Данные для отправки (для POST/PATCH)

        Returns:
            Ответ от API в виде dict

        Raises:
            requests.HTTPError: При ошибке API
        """
        url = f"{self.base_url}{endpoint}"

        logger.info(f"AmoCRM API request: {method} {url}")
        if data and method in ["POST", "PATCH"]:
            logger.debug(f"Request data: {data}")

        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=data, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method == "PATCH":
                response = requests.patch(url, headers=self.headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Обработка rate limits
            if response.status_code == 429:
                logger.warning("AmoCRM rate limit exceeded, retrying...")
                response.raise_for_status()

            response.raise_for_status()

            logger.info(f"AmoCRM API response: {response.status_code}")

            return response.json() if response.text else {}

        except requests.exceptions.RequestException as e:
            logger.error(f"AmoCRM API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response text: {e.response.text}")
            raise

    def find_contact_by_custom_field(self, field_id: int, value: str) -> dict[str, Any] | None:
        """
        Найти контакт по кастомному полю.

        Args:
            field_id: ID кастомного поля
            value: Значение для поиска

        Returns:
            Данные контакта или None если не найден
        """
        logger.info(f"Searching contact by custom field {field_id}={value}")

        try:
            response = self._make_request(
                "GET",
                "/api/v4/contacts",
                data={"filter": {f"custom_fields_values[{field_id}]": value}},
            )

            contacts = response.get("_embedded", {}).get("contacts", [])

            if not contacts:
                logger.info("Contact not found")
                return None

            if len(contacts) > 1:
                logger.warning(f"Found {len(contacts)} contacts, taking the first one")

            contact = contacts[0]
            logger.info(f"Found contact: {contact['id']}")
            return contact

        except Exception as e:
            logger.error(f"Error finding contact by custom field: {e}")
            return None

    def find_contact_by_phone(self, phone: str) -> dict[str, Any] | None:
        """
        Найти контакт по телефону.

        Args:
            phone: Номер телефона

        Returns:
            Данные контакта или None если не найден
        """
        logger.info(f"Searching contact by phone: {phone}")

        try:
            response = self._make_request(
                "GET",
                "/api/v4/contacts",
                data={"query": phone},
            )

            contacts = response.get("_embedded", {}).get("contacts", [])

            if not contacts:
                logger.info("Contact not found by phone")
                return None

            if len(contacts) > 1:
                logger.warning(f"Found {len(contacts)} contacts by phone, taking the first one")

            contact = contacts[0]
            logger.info(f"Found contact by phone: {contact['id']}")
            return contact

        except Exception as e:
            logger.error(f"Error finding contact by phone: {e}")
            return None

    def find_contact_by_email(self, email: str) -> dict[str, Any] | None:
        """
        Найти контакт по email.

        Args:
            email: Email адрес

        Returns:
            Данные контакта или None если не найден
        """
        logger.info(f"Searching contact by email: {email}")

        try:
            response = self._make_request(
                "GET",
                "/api/v4/contacts",
                data={"query": email},
            )

            contacts = response.get("_embedded", {}).get("contacts", [])

            if not contacts:
                logger.info("Contact not found by email")
                return None

            if len(contacts) > 1:
                logger.warning(f"Found {len(contacts)} contacts by email, taking the first one")

            contact = contacts[0]
            logger.info(f"Found contact by email: {contact['id']}")
            return contact

        except Exception as e:
            logger.error(f"Error finding contact by email: {e}")
            return None

    def find_contact(self, tg_id: str | None, phone: str | None, email: str | None) -> dict[str, Any] | None:
        """
        Найти контакт по приоритетам: tg_id -> phone -> email.

        Args:
            tg_id: Telegram ID
            phone: Номер телефона
            email: Email адрес

        Returns:
            Данные контакта или None если не найден
        """
        logger.info(f"Finding contact: tg_id={tg_id}, phone={phone}, email={email}")

        # Приоритет 1: поиск по tg_id
        if tg_id:
            contact = self.find_contact_by_custom_field(settings.AMO_CONTACT_FIELD_TG_ID, tg_id)
            if contact:
                return contact

        # Приоритет 2: поиск по телефону
        if phone:
            contact = self.find_contact_by_phone(phone)
            if contact:
                return contact

        # Приоритет 3: поиск по email
        if email:
            contact = self.find_contact_by_email(email)
            if contact:
                return contact

        logger.info("Contact not found by any criteria")
        return None

    def create_contact(
        self,
        name: str,
        phone: str | None = None,
        email: str | None = None,
        tg_id: str | None = None,
        tg_username: str | None = None,
    ) -> int:
        """
        Создать новый контакт в AmoCRM.

        Args:
            name: Имя контакта
            phone: Телефон
            email: Email
            tg_id: Telegram ID
            tg_username: Telegram username

        Returns:
            ID созданного контакта
        """
        logger.info(f"Creating contact: {name}")

        contact_data: dict[str, Any] = {
            "name": name,
            "custom_fields_values": [],
        }

        # Добавить телефон
        if phone:
            contact_data["custom_fields_values"].append(
                {"field_code": "PHONE", "values": [{"value": phone, "enum_code": "WORK"}]}
            )

        # Добавить email
        if email:
            contact_data["custom_fields_values"].append(
                {"field_code": "EMAIL", "values": [{"value": email, "enum_code": "WORK"}]}
            )

        # Добавить tg_id
        if tg_id:
            contact_data["custom_fields_values"].append(
                {"field_id": settings.AMO_CONTACT_FIELD_TG_ID, "values": [{"value": tg_id}]}
            )

        # Добавить tg_username
        if tg_username:
            contact_data["custom_fields_values"].append(
                {"field_id": settings.AMO_CONTACT_FIELD_TG_USERNAME, "values": [{"value": tg_username}]}
            )

        try:
            response = self._make_request("POST", "/api/v4/contacts", data=[contact_data])

            contact_id = response["_embedded"]["contacts"][0]["id"]
            logger.info(f"Contact created: {contact_id}")
            return contact_id

        except Exception as e:
            logger.error(f"Error creating contact: {e}")
            raise

    def update_contact_fields(self, contact_id: int, tg_id: str | None = None, tg_username: str | None = None) -> None:
        """
        Обновить кастомные поля контакта (идемпотентно - только пустые поля).

        Args:
            contact_id: ID контакта
            tg_id: Telegram ID (обновить только если пусто)
            tg_username: Telegram username (обновить только если пусто)
        """
        logger.info(f"Updating contact {contact_id} fields")

        try:
            response = self._make_request("GET", f"/api/v4/contacts/{contact_id}", data={"with": "contacts"})
            current_fields = response.get("custom_fields_values", [])

            current_tg_id = None
            current_tg_username = None

            for field in current_fields:
                if field["field_id"] == settings.AMO_CONTACT_FIELD_TG_ID:
                    current_tg_id = field["values"][0]["value"] if field["values"] else None
                elif field["field_id"] == settings.AMO_CONTACT_FIELD_TG_USERNAME:
                    current_tg_username = field["values"][0]["value"] if field["values"] else None

            update_data: dict[str, Any] = {"custom_fields_values": []}

            if tg_id and not current_tg_id:
                logger.info(f"Updating tg_id: {tg_id}")
                update_data["custom_fields_values"].append(
                    {"field_id": settings.AMO_CONTACT_FIELD_TG_ID, "values": [{"value": tg_id}]}
                )

            if tg_username and not current_tg_username:
                logger.info(f"Updating tg_username: {tg_username}")
                update_data["custom_fields_values"].append(
                    {"field_id": settings.AMO_CONTACT_FIELD_TG_USERNAME, "values": [{"value": tg_username}]}
                )

            if update_data["custom_fields_values"]:
                self._make_request("PATCH", f"/api/v4/contacts/{contact_id}", data=update_data)
                logger.info(f"Contact {contact_id} fields updated")
            else:
                logger.info(f"Contact {contact_id} fields are already filled, skipping update")

        except Exception as e:
            logger.error(f"Error updating contact fields: {e}")
            raise

    def update_contact(
        self,
        contact_id: int,
        name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        tg_id: str | None = None,
        tg_username: str | None = None,
    ) -> None:
        """
        Полное обновление контакта (имя, телефон, email, telegram).

        Args:
            contact_id: ID контакта
            name: Имя контакта
            phone: Телефон
            email: Email
            tg_id: Telegram ID
            tg_username: Telegram username
        """
        logger.info(f"Updating contact {contact_id}")

        update_data: dict[str, Any] = {}
        custom_fields: list[dict[str, Any]] = []

        # Обновить имя
        if name:
            update_data["name"] = name

        # Обновить телефон
        if phone:
            custom_fields.append(
                {"field_code": "PHONE", "values": [{"value": phone, "enum_code": "WORK"}]}
            )

        # Обновить email
        if email:
            custom_fields.append(
                {"field_code": "EMAIL", "values": [{"value": email, "enum_code": "WORK"}]}
            )

        # Обновить tg_id
        if tg_id:
            custom_fields.append(
                {"field_id": settings.AMO_CONTACT_FIELD_TG_ID, "values": [{"value": tg_id}]}
            )

        # Обновить tg_username
        if tg_username:
            custom_fields.append(
                {"field_id": settings.AMO_CONTACT_FIELD_TG_USERNAME, "values": [{"value": tg_username}]}
            )

        # Добавить custom_fields_values только если есть что обновлять
        if custom_fields:
            update_data["custom_fields_values"] = custom_fields

        try:
            logger.debug(f"Contact update data: {update_data}")
            self._make_request("PATCH", f"/api/v4/contacts/{contact_id}", data=update_data)
            logger.info(f"Contact {contact_id} updated successfully")

        except Exception as e:
            logger.error(f"Error updating contact: {e}")
            raise

    def find_active_lead(self, contact_id: int) -> dict[str, Any] | None:
        """
        Найти активную сделку для контакта (во ВСЕХ воронках).

        Args:
            contact_id: ID контакта

        Returns:
            Данные сделки или None если не найдена
        """
        logger.info(f"Searching active lead for contact {contact_id}")

        try:
            response = self._make_request(
                "GET",
                "/api/v4/leads",
                data={"filter[contacts]": contact_id},
            )

            leads = response.get("_embedded", {}).get("leads", [])

            if not leads:
                logger.info("No leads found for contact")
                return None

            # Отфильтровать закрытые/проигранные сделки
            active_leads = [lead for lead in leads if not lead.get("is_deleted", False) and lead.get("status_id")]

            if not active_leads:
                logger.info("No active leads found")
                return None

            # Выбрать последнюю обновленную
            active_lead = max(active_leads, key=lambda x: x.get("updated_at", 0))

            logger.info(f"Found active lead: {active_lead['id']} (pipeline: {active_lead.get('pipeline_id')})")
            return active_lead

        except Exception as e:
            logger.error(f"Error finding active lead: {e}")
            return None

    def create_lead(
        self,
        name: str,
        contact_id: int,
        price: int = 0,
        tg_id: str | None = None,
    ) -> int:
        """
        Создать новую сделку в AmoCRM.

        Args:
            name: Название сделки
            contact_id: ID контакта
            price: Бюджет сделки
            tg_id: Telegram ID (если есть отдельное поле в сделке)

        Returns:
            ID созданной сделки
        """
        logger.info(f"Creating lead: {name} for contact {contact_id}")

        lead_data: dict[str, Any] = {
            "name": name,
            "price": price,
            "pipeline_id": settings.AMO_PIPELINE_ID,
            "status_id": settings.AMO_DEFAULT_STATUS_ID,
            "_embedded": {"contacts": [{"id": contact_id}]},
            "custom_fields_values": [],
        }

        # Добавить tg_id в сделку (если есть поле)
        if tg_id and settings.AMO_LEAD_FIELD_TG_ID:
            lead_data["custom_fields_values"].append({"field_id": settings.AMO_LEAD_FIELD_TG_ID, "values": [{"value": tg_id}]})

        try:
            response = self._make_request("POST", "/api/v4/leads", data=[lead_data])

            lead_id = response["_embedded"]["leads"][0]["id"]
            logger.info(f"Lead created: {lead_id}")
            return lead_id

        except Exception as e:
            logger.error(f"Error creating lead: {e}")
            raise

    def update_lead_fields(
        self,
        lead_id: int,
        subjects: list[int] | None = None,
        direction: int | None = None,
        last_payment_amount: int | None = None,
        total_paid_increment: int | None = None,
        payment_status: str | None = None,
        last_payment_date: str | None = None,
        invoice_id: str | None = None,
        payment_id: str | None = None,
    ) -> None:
        """
        Обновить кастомные поля сделки.

        Args:
            lead_id: ID сделки
            subjects: Список enum_id предметов (для мультисписка)
            direction: enum_id направления курса (ЕГЭ/ОГЭ)
            last_payment_amount: Сумма последней оплаты
            total_paid_increment: Сумма для добавления к общему итогу
            payment_status: Статус оплаты
            last_payment_date: Дата последней оплаты
            invoice_id: Invoice ID
            payment_id: Payment ID
        """
        logger.info(f"Updating lead {lead_id} fields")

        try:
            # Получить текущие значения сделки
            response = self._make_request("GET", f"/api/v4/leads/{lead_id}")
            current_fields = response.get("custom_fields_values") or []

            # Получить текущий общий оплаченный итог
            current_total_paid = 0
            current_purchase_count = 0

            for field in current_fields:
                if settings.AMO_LEAD_FIELD_TOTAL_PAID and field["field_id"] == settings.AMO_LEAD_FIELD_TOTAL_PAID:
                    current_total_paid = int(field["values"][0]["value"]) if field["values"] else 0
                elif field["field_id"] == settings.AMO_LEAD_FIELD_PURCHASE_COUNT:
                    # Поле "Купленных курсов" - это select, значение хранится как текст
                    current_purchase_count = int(field["values"][0]["value"]) if field["values"] else 0

            # Подготовить данные для обновления
            update_data: dict[str, Any] = {"custom_fields_values": []}

            # tg_id в сделке не используется (есть только в контакте)

            # Обновить предметы (всегда)
            if subjects:
                logger.info(f"Updating subjects: {subjects}")
                # Для мультисписка нужно передавать enum_id для каждого значения
                values = [{"enum_id": enum_id} for enum_id in subjects]
                update_data["custom_fields_values"].append(
                    {"field_id": settings.AMO_LEAD_FIELD_SUBJECTS, "values": values}
                )

            # Обновить направление курса (всегда)
            if direction:
                logger.info(f"Updating direction: {direction}")
                update_data["custom_fields_values"].append(
                    {"field_id": settings.AMO_LEAD_FIELD_DIRECTION, "values": [{"enum_id": direction}]}
                )

            # Обновить сумму последней оплаты (всегда)
            if last_payment_amount is not None and settings.AMO_LEAD_FIELD_LAST_PAYMENT_AMOUNT:
                logger.info(f"Updating last payment amount: {last_payment_amount}")
                update_data["custom_fields_values"].append(
                    {"field_id": settings.AMO_LEAD_FIELD_LAST_PAYMENT_AMOUNT, "values": [{"value": last_payment_amount}]}
                )

            # Обновить общий оплаченный итог (инкрементально)
            if total_paid_increment is not None and settings.AMO_LEAD_FIELD_TOTAL_PAID:
                new_total_paid = current_total_paid + total_paid_increment
                logger.info(f"Updating total paid: {current_total_paid} + {total_paid_increment} = {new_total_paid}")
                update_data["custom_fields_values"].append(
                    {"field_id": settings.AMO_LEAD_FIELD_TOTAL_PAID, "values": [{"value": new_total_paid}]}
                )

            # Обновить счетчик покупок (инкрементально +1)
            # Поле "Купленных курсов" - это select с enum_id
            # Маппинг: 1->1373533, 2->1373535, 3->1373537, ..., 10->1373551
            new_purchase_count = current_purchase_count + 1
            logger.info(f"Updating purchase count: {current_purchase_count} + 1 = {new_purchase_count}")

            # Получить enum_id для нового значения (1373533 + (count-1)*2)
            if 1 <= new_purchase_count <= 10:
                purchase_count_enum_id = 1373533 + (new_purchase_count - 1) * 2
                update_data["custom_fields_values"].append(
                    {"field_id": settings.AMO_LEAD_FIELD_PURCHASE_COUNT, "values": [{"enum_id": purchase_count_enum_id}]}
                )
            else:
                logger.warning(f"Purchase count {new_purchase_count} is out of range (1-10), skipping update")

            if payment_status and settings.AMO_LEAD_FIELD_PAYMENT_STATUS:
                logger.info(f"Updating payment status: {payment_status}")
                update_data["custom_fields_values"].append(
                    {"field_id": settings.AMO_LEAD_FIELD_PAYMENT_STATUS, "values": [{"value": payment_status}]}
                )

            if last_payment_date and settings.AMO_LEAD_FIELD_LAST_PAYMENT_DATE:
                logger.info(f"Updating last payment date: {last_payment_date}")
                update_data["custom_fields_values"].append(
                    {"field_id": settings.AMO_LEAD_FIELD_LAST_PAYMENT_DATE, "values": [{"value": last_payment_date}]}
                )

            if invoice_id and settings.AMO_LEAD_FIELD_INVOICE_ID:
                logger.info(f"Updating invoice ID: {invoice_id}")
                update_data["custom_fields_values"].append(
                    {"field_id": settings.AMO_LEAD_FIELD_INVOICE_ID, "values": [{"value": invoice_id}]}
                )

            if payment_id and settings.AMO_LEAD_FIELD_PAYMENT_ID:
                logger.info(f"Updating payment ID: {payment_id}")
                update_data["custom_fields_values"].append(
                    {"field_id": settings.AMO_LEAD_FIELD_PAYMENT_ID, "values": [{"value": payment_id}]}
                )

            if update_data["custom_fields_values"]:
                self._make_request("PATCH", f"/api/v4/leads/{lead_id}", data=update_data)
                logger.info(f"Lead {lead_id} fields updated")
            else:
                logger.info(f"No fields to update for lead {lead_id}")

        except Exception as e:
            logger.error(f"Error updating lead fields: {e}")
            raise

    def update_lead(
        self,
        lead_id: int,
        name: str | None = None,
        price: int | None = None,
        subjects: list[int] | None = None,
        direction: int | None = None,
        purchase_count: int | None = None,
    ) -> None:
        """
        Полное обновление сделки (название, бюджет, кастомные поля).

        Args:
            lead_id: ID сделки
            name: Название сделки
            price: Бюджет сделки
            subjects: Список enum_id предметов (для мультисписка)
            direction: enum_id направления курса (ЕГЭ/ОГЭ)
            purchase_count: enum_id количества купленных курсов
        """
        logger.info(f"Updating lead {lead_id}")

        update_data: dict[str, Any] = {}
        custom_fields: list[dict[str, Any]] = []

        if name:
            update_data["name"] = name

        if price is not None:
            update_data["price"] = price

        if subjects:
            values = [{"enum_id": enum_id} for enum_id in subjects]
            custom_fields.append(
                {"field_id": settings.AMO_LEAD_FIELD_SUBJECTS, "values": values}
            )

        if direction:
            custom_fields.append(
                {"field_id": settings.AMO_LEAD_FIELD_DIRECTION, "values": [{"enum_id": direction}]}
            )

        if purchase_count:
            custom_fields.append(
                {"field_id": settings.AMO_LEAD_FIELD_PURCHASE_COUNT, "values": [{"enum_id": purchase_count}]}
            )

        if custom_fields:
            update_data["custom_fields_values"] = custom_fields

        try:
            self._make_request("PATCH", f"/api/v4/leads/{lead_id}", data=update_data)
            logger.info(f"Lead {lead_id} updated successfully")

        except Exception as e:
            logger.error(f"Error updating lead: {e}")
            raise

    def add_lead_note(self, lead_id: int, text: str) -> None:
        """
        Добавить примечание к сделке.

        Args:
            lead_id: ID сделки
            text: Текст примечания
        """
        logger.info(f"Adding note to lead {lead_id}")

        note_data = {
            "entity_id": lead_id,
            "note_type": "common",
            "params": {"text": text},
        }

        try:
            self._make_request("POST", f"/api/v4/leads/{lead_id}/notes", data=[note_data])
            logger.info(f"Note added to lead {lead_id}")

        except Exception as e:
            logger.error(f"Error adding note to lead: {e}")
            raise
