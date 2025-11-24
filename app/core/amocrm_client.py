"""Клиент для работы с AmoCRM API."""

import logging
from typing import Any

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.amocrm_mappings import EXCLUDED_STATUSES
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

    def _get_purchase_count_enum_id(self, count: int) -> int | None:
        """
        Получить enum_id для значения счетчика покупок.

        Args:
            count: Количество покупок (1-10)

        Returns:
            enum_id для AmoCRM или None если значение вне диапазона
        """
        mapping = {
            1: settings.AMO_PURCHASE_COUNT_1,
            2: settings.AMO_PURCHASE_COUNT_2,
            3: settings.AMO_PURCHASE_COUNT_3,
            4: settings.AMO_PURCHASE_COUNT_4,
            5: settings.AMO_PURCHASE_COUNT_5,
            6: settings.AMO_PURCHASE_COUNT_6,
            7: settings.AMO_PURCHASE_COUNT_7,
            8: settings.AMO_PURCHASE_COUNT_8,
            9: settings.AMO_PURCHASE_COUNT_9,
            10: settings.AMO_PURCHASE_COUNT_10,
        }
        return mapping.get(count)

    async def _make_request(self, method: str, endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Выполнить HTTP запрос к AmoCRM API с retry механизмом.

        Args:
            method: HTTP метод (GET, POST, PATCH)
            endpoint: Endpoint API (например, /api/v4/contacts)
            data: Данные для отправки (для POST/PATCH)

        Returns:
            Ответ от API в виде dict

        Raises:
            httpx.HTTPError: При ошибке API
        """
        url = f"{self.base_url}{endpoint}"

        logger.info(f"AmoCRM API request: {method} {url}")
        if data and method in ["POST", "PATCH"]:
            logger.debug(f"Request data: {data}")

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.RETRY_MAX_ATTEMPTS),
            wait=wait_exponential(multiplier=1, min=settings.RETRY_WAIT_MIN, max=settings.RETRY_WAIT_MAX),
            retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        ):
            with attempt:
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        if method == "GET":
                            response = await client.get(url, headers=self.headers, params=data)
                        elif method == "POST":
                            response = await client.post(url, headers=self.headers, json=data)
                        elif method == "PATCH":
                            response = await client.patch(url, headers=self.headers, json=data)
                        else:
                            raise ValueError(f"Unsupported HTTP method: {method}")

                        if response.status_code == 429:
                            logger.warning("AmoCRM rate limit exceeded, retrying...")
                            response.raise_for_status()

                        response.raise_for_status()

                        logger.info(f"AmoCRM API response: {response.status_code}")

                        return response.json() if response.text else {}

                except httpx.HTTPError as e:
                    logger.error(f"AmoCRM API error: {e}")
                    if hasattr(e, "response") and e.response is not None:
                        logger.error(f"Response text: {e.response.text}")
                    raise

    async def find_contact_by_custom_field(self, value: str) -> dict[str, Any] | None:
        """
        Найти контакт по кастомному полю через filter[query].

        Args:
            field_id: ID кастомного поля (используется для логирования)
            value: Значение для поиска

        Returns:
            Данные контакта или None если не найден
        """
        logger.info(f"Searching contact by custom value {value} using filter[query]")

        try:
            response = await self._make_request(
                "GET",
                "/api/v4/contacts",
                data={
                    "query": value,
                    "limit": 50,
                },
            )

            contacts = response.get("_embedded", {}).get("contacts", [])

            if not contacts:
                logger.info(f"Contact not found by value: {value}")
                return None

            logger.info(f"Found {len(contacts)} contacts by query={value}")

            if len(contacts) > 1:
                logger.warning(f"Found {len(contacts)} contacts, taking the first one")

            contact = contacts[0]
            logger.info(f"Found contact: {contact['id']}")
            return contact

        except Exception as e:
            logger.error(f"Error finding contact by custom field: {e}")
            return None

    async def find_contact_by_phone(self, phone: str) -> dict[str, Any] | None:
        """
        Найти контакт по телефону.

        Args:
            phone: Номер телефона

        Returns:
            Данные контакта или None если не найден
        """
        logger.info(f"Searching contact by phone: {phone}")

        try:
            response = await self._make_request(
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

    async def find_contact_by_email(self, email: str) -> dict[str, Any] | None:
        """
        Найти контакт по email.

        Args:
            email: Email адрес

        Returns:
            Данные контакта или None если не найден
        """
        logger.info(f"Searching contact by email: {email}")

        try:
            response = await self._make_request(
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

    async def find_contact(self, tg_id: str | None, phone: str | None, email: str | None) -> dict[str, Any] | None:
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

        if tg_id:
            contact = await self.find_contact_by_custom_field(tg_id)
            if contact:
                return contact

        if phone:
            contact = await self.find_contact_by_phone(phone)
            if contact:
                return contact

        if email:
            contact = await self.find_contact_by_email(email)
            if contact:
                return contact

        logger.info("Contact not found by any criteria")
        return None

    async def find_active_lead(
        self,
        contact_id: int,
        telegram_id: str | None = None,
        phone: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Найти активную сделку для контакта.

        Сначала пытается найти через filter[query] по telegram_id, телефону или email,
        затем фильтрует по contact_id для проверки совпадения.

        Args:
            contact_id: ID контакта
            telegram_id: Telegram ID для поиска (приоритет 1)
            phone: Телефон для поиска (приоритет 2)
            email: Email для поиска (приоритет 3)

        Returns:
            Данные сделки или None если не найдена
        """
        logger.info(
            f"Searching active lead for contact {contact_id}, telegram_id={telegram_id}, phone={phone}, email={email}"
        )

        try:
            leads = []

            if telegram_id:
                logger.info(f"Searching leads by telegram_id: {telegram_id}")
                try:
                    response = await self._make_request(
                        "GET",
                        "/api/v4/leads",
                        data={
                            "filter[query]": telegram_id,
                            "limit": 50,
                        },
                    )
                    telegram_leads = response.get("_embedded", {}).get("leads", [])
                    logger.info(f"Found {len(telegram_leads)} leads by telegram_id")
                    leads.extend(telegram_leads)
                except Exception as e:
                    logger.warning(f"Error searching leads by telegram_id: {e}")

            if phone:
                logger.info(f"Searching leads by phone: {phone}")
                try:
                    response = await self._make_request(
                        "GET",
                        "/api/v4/leads",
                        data={
                            "filter[query]": phone,
                            "limit": 50,
                        },
                    )
                    phone_leads = response.get("_embedded", {}).get("leads", [])
                    logger.info(f"Found {len(phone_leads)} leads by phone")
                    leads.extend(phone_leads)
                except Exception as e:
                    logger.warning(f"Error searching leads by phone: {e}")

            if email:
                logger.info(f"Searching leads by email: {email}")
                try:
                    response = await self._make_request(
                        "GET",
                        "/api/v4/leads",
                        data={
                            "filter[query]": email,
                            "limit": 50,
                        },
                    )
                    email_leads = response.get("_embedded", {}).get("leads", [])
                    logger.info(f"Found {len(email_leads)} leads by email")
                    leads.extend(email_leads)
                except Exception as e:
                    logger.warning(f"Error searching leads by email: {e}")

            if not leads:
                logger.info("No leads found by telegram_id, phone or email")
                return None

            unique_leads = {lead["id"]: lead for lead in leads}.values()
            leads = list(unique_leads)
            logger.info(f"Total unique leads found: {len(leads)}")

            verified_leads = []
            for lead in leads:
                lead_id = lead.get("id")
                try:
                    lead_with_contacts = await self._make_request(
                        "GET", f"/api/v4/leads/{lead_id}", data={"with": "contacts"}
                    )

                    embedded_contacts = (
                        lead_with_contacts.get("_embedded", {}).get("contacts", [])
                    )
                    contact_ids = [c.get("id") for c in embedded_contacts]

                    if contact_id in contact_ids:
                        logger.info(
                            f"Lead {lead_id} verified: contains contact {contact_id}"
                        )
                        verified_leads.append(lead)
                    else:
                        logger.info(
                            f"Lead {lead_id} skipped: contact {contact_id} not found (contacts: {contact_ids})"
                        )

                except Exception as e:
                    logger.warning(f"Error verifying lead {lead_id}: {e}")
                    continue

            if not verified_leads:
                logger.info("No leads matched contact_id after verification")
                return None

            logger.info(f"Verified leads: {len(verified_leads)}")

            active_leads = [
                lead
                for lead in verified_leads
                if not lead.get("is_deleted", False)
                and lead.get("status_id") not in EXCLUDED_STATUSES
                and lead.get("updated_at", 0) > 0
            ]

            logger.info(f"Active leads after status filtering: {len(active_leads)}")

            if not active_leads:
                logger.info("No active leads found after filtering")
                return None

            active_lead = max(active_leads, key=lambda x: x.get("updated_at", 0))

            logger.info(
                f"Selected active lead: ID={active_lead['id']}, "
                f"Pipeline={active_lead.get('pipeline_id')}, "
                f"Status={active_lead.get('status_id')}, "
                f"Updated_at={active_lead.get('updated_at')}"
            )
            return active_lead

        except Exception as e:
            logger.error(f"Error finding active lead: {e}")
            return None


    async def create_contact(
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

        if phone:
            contact_data["custom_fields_values"].append(
                {"field_code": "PHONE", "values": [{"value": phone, "enum_code": "WORK"}]}
            )

        if email:
            contact_data["custom_fields_values"].append(
                {"field_code": "EMAIL", "values": [{"value": email, "enum_code": "WORK"}]}
            )

        if tg_id:
            contact_data["custom_fields_values"].append(
                {"field_id": settings.AMO_CONTACT_FIELD_TG_ID, "values": [{"value": tg_id}]}
            )

        if tg_username:
            contact_data["custom_fields_values"].append(
                {"field_id": settings.AMO_CONTACT_FIELD_TG_USERNAME, "values": [{"value": tg_username}]}
            )

        try:
            response = await self._make_request("POST", "/api/v4/contacts", data=[contact_data])

            contact_id = response["_embedded"]["contacts"][0]["id"]
            logger.info(f"Contact created: {contact_id}")
            return contact_id

        except Exception as e:
            logger.error(f"Error creating contact: {e}")
            raise

    async def update_contact_fields(self, contact_id: int, tg_id: str | None = None, tg_username: str | None = None) -> None:
        """
        Обновить кастомные поля контакта (идемпотентно - только пустые поля).

        Args:
            contact_id: ID контакта
            tg_id: Telegram ID (обновить только если пусто)
            tg_username: Telegram username (обновить только если пусто)
        """
        logger.info(f"Updating contact {contact_id} fields")

        try:
            response = await self._make_request("GET", f"/api/v4/contacts/{contact_id}", data={"with": "contacts"})
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
                await self._make_request("PATCH", f"/api/v4/contacts/{contact_id}", data=update_data)
                logger.info(f"Contact {contact_id} fields updated")
            else:
                logger.info(f"Contact {contact_id} fields are already filled, skipping update")

        except Exception as e:
            logger.error(f"Error updating contact fields: {e}")
            raise

    async def update_contact(
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
            tg_username: Telegram username (без @)
        """
        logger.info(f"Updating contact {contact_id}")

        contact_data: dict[str, Any] = {"id": contact_id}
        custom_fields: list[dict[str, Any]] = []

        if name:
            contact_data["name"] = name

        if phone:
            custom_fields.append({"field_code": "PHONE", "values": [{"value": phone, "enum_code": "WORK"}]})

        if email:
            custom_fields.append({"field_code": "EMAIL", "values": [{"value": email, "enum_code": "WORK"}]})

        if tg_id:
            custom_fields.append({"field_id": settings.AMO_CONTACT_FIELD_TG_ID, "values": [{"value": tg_id}]})

        if tg_username:
            custom_fields.append({"field_id": settings.AMO_CONTACT_FIELD_TG_USERNAME, "values": [{"value": tg_username}]})

        if custom_fields:
            contact_data["custom_fields_values"] = custom_fields

        try:
            logger.debug(f"Contact update data: {contact_data}")
            await self._make_request("PATCH", "/api/v4/contacts", data=[contact_data])
            logger.info(f"Contact {contact_id} updated successfully")

        except Exception as e:
            logger.error(f"Error updating contact: {e}")
            raise

    async def create_lead(
        self,
        name: str,
        contact_id: int,
        price: int = 0,
        pipeline_id: int | None = None,
        status_id: int | None = None,
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
        utm_content: str | None = None,
        utm_term: str | None = None,
        ym_uid: str | None = None,
    ) -> int:
        """
        Создать новую сделку в AmoCRM с UTM параметрами.

        Args:
            name: Название сделки
            contact_id: ID контакта
            price: Бюджет сделки
            pipeline_id: ID воронки (если не указан - используется AMO_PIPELINE_ID из настроек)
            status_id: ID этапа (если не указан - используется AMO_DEFAULT_STATUS_ID из настроек)
            utm_source: UTM source
            utm_medium: UTM medium
            utm_campaign: UTM campaign
            utm_content: UTM content
            utm_term: UTM term
            ym_uid: Yandex Metrika UID

        Returns:
            ID созданной сделки
        """
        target_pipeline_id = pipeline_id if pipeline_id is not None else settings.AMO_PIPELINE_ID
        target_status_id = status_id if status_id is not None else settings.AMO_DEFAULT_STATUS_ID

        logger.info(f"Creating lead: {name} for contact {contact_id}")
        logger.info(f"  Pipeline: {target_pipeline_id}, Status: {target_status_id}")

        lead_data: dict[str, Any] = {
            "name": name,
            "price": price,
            "pipeline_id": target_pipeline_id,
            "status_id": target_status_id,
            "_embedded": {"contacts": [{"id": contact_id}]},
            "custom_fields_values": [],
        }

        if utm_source:
            logger.info(f"Adding UTM source: {utm_source}")
            lead_data["custom_fields_values"].append(
                {"field_id": settings.AMO_LEAD_FIELD_UTM_SOURCE, "values": [{"value": utm_source}]}
            )

        if utm_medium:
            logger.info(f"Adding UTM medium: {utm_medium}")
            lead_data["custom_fields_values"].append(
                {"field_id": settings.AMO_LEAD_FIELD_UTM_MEDIUM, "values": [{"value": utm_medium}]}
            )

        if utm_campaign:
            logger.info(f"Adding UTM campaign: {utm_campaign}")
            lead_data["custom_fields_values"].append(
                {"field_id": settings.AMO_LEAD_FIELD_UTM_CAMPAIGN, "values": [{"value": utm_campaign}]}
            )

        if utm_content:
            logger.info(f"Adding UTM content: {utm_content}")
            lead_data["custom_fields_values"].append(
                {"field_id": settings.AMO_LEAD_FIELD_UTM_CONTENT, "values": [{"value": utm_content}]}
            )

        if utm_term:
            logger.info(f"Adding UTM term: {utm_term}")
            lead_data["custom_fields_values"].append(
                {"field_id": settings.AMO_LEAD_FIELD_UTM_TERM, "values": [{"value": utm_term}]}
            )

        if ym_uid:
            logger.info(f"Adding Yandex Metrika UID: {ym_uid}")
            lead_data["custom_fields_values"].append(
                {"field_id": settings.AMO_LEAD_FIELD_YM_UID, "values": [{"value": ym_uid}]}
            )

        try:
            response = await self._make_request("POST", "/api/v4/leads", data=[lead_data])

            lead_id = response["_embedded"]["leads"][0]["id"]
            logger.info(f"Lead created: {lead_id}")
            return lead_id

        except Exception as e:
            logger.error(f"Error creating lead: {e}")
            raise

    async def update_lead_fields(
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
        status_id: int | None = None,
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
            status_id: ID этапа для перевода сделки
        """
        logger.info(f"Updating lead {lead_id} fields")

        try:
            response = await self._make_request("GET", f"/api/v4/leads/{lead_id}")
            current_fields = response.get("custom_fields_values") or []

            current_total_paid = 0
            current_purchase_count = 0

            for field in current_fields:
                if settings.AMO_LEAD_FIELD_TOTAL_PAID and field["field_id"] == settings.AMO_LEAD_FIELD_TOTAL_PAID:
                    current_total_paid = int(field["values"][0]["value"]) if field["values"] else 0
                elif field["field_id"] == settings.AMO_LEAD_FIELD_PURCHASE_COUNT:
                    current_purchase_count = int(field["values"][0]["value"]) if field["values"] else 0

            update_data: dict[str, Any] = {"custom_fields_values": []}


            if subjects:
                logger.info(f"Updating subjects: {subjects}")
                values = [{"enum_id": enum_id} for enum_id in subjects]
                update_data["custom_fields_values"].append({"field_id": settings.AMO_LEAD_FIELD_SUBJECTS, "values": values})

            if direction:
                logger.info(f"Updating direction: {direction}")
                update_data["custom_fields_values"].append(
                    {"field_id": settings.AMO_LEAD_FIELD_DIRECTION, "values": [{"enum_id": direction}]}
                )

            if last_payment_amount is not None and settings.AMO_LEAD_FIELD_LAST_PAYMENT_AMOUNT:
                logger.info(f"Updating last payment amount: {last_payment_amount}")
                update_data["custom_fields_values"].append(
                    {"field_id": settings.AMO_LEAD_FIELD_LAST_PAYMENT_AMOUNT, "values": [{"value": last_payment_amount}]}
                )

            if total_paid_increment is not None and settings.AMO_LEAD_FIELD_TOTAL_PAID:
                new_total_paid = current_total_paid + total_paid_increment
                logger.info(f"Updating total paid: {current_total_paid} + {total_paid_increment} = {new_total_paid}")
                update_data["custom_fields_values"].append(
                    {"field_id": settings.AMO_LEAD_FIELD_TOTAL_PAID, "values": [{"value": new_total_paid}]}
                )

            new_purchase_count = current_purchase_count + 1
            logger.info(f"Updating purchase count: {current_purchase_count} + 1 = {new_purchase_count}")

            purchase_count_enum_id = self._get_purchase_count_enum_id(new_purchase_count)
            if purchase_count_enum_id:
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

            if status_id is not None:
                logger.info(f"Updating lead status to: {status_id}")
                update_data["status_id"] = status_id

            if update_data["custom_fields_values"] or status_id is not None:
                await self._make_request("PATCH", f"/api/v4/leads/{lead_id}", data=update_data)
                logger.info(f"Lead {lead_id} fields updated")
            else:
                logger.info(f"No fields to update for lead {lead_id}")

        except Exception as e:
            logger.error(f"Error updating lead fields: {e}")
            raise

    async def update_lead(
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
            custom_fields.append({"field_id": settings.AMO_LEAD_FIELD_SUBJECTS, "values": values})

        if direction:
            custom_fields.append({"field_id": settings.AMO_LEAD_FIELD_DIRECTION, "values": [{"enum_id": direction}]})

        if purchase_count:
            custom_fields.append({"field_id": settings.AMO_LEAD_FIELD_PURCHASE_COUNT, "values": [{"enum_id": purchase_count}]})

        if custom_fields:
            update_data["custom_fields_values"] = custom_fields

        try:
            await self._make_request("PATCH", f"/api/v4/leads/{lead_id}", data=update_data)
            logger.info(f"Lead {lead_id} updated successfully")

        except Exception as e:
            logger.error(f"Error updating lead: {e}")
            raise


    async def add_lead_note(self, lead_id: int, text: str) -> None:
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
            await self._make_request("POST", f"/api/v4/leads/{lead_id}/notes", data=[note_data])
            logger.info(f"Note added to lead {lead_id}")

        except Exception as e:
            logger.error(f"Error adding note to lead: {e}")
            raise
