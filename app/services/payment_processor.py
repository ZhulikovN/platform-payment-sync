"""Сервис обработки оплат - центральная бизнес-логика."""

import logging
from dataclasses import dataclass
from datetime import datetime

from app.core.amocrm_client import AmoCRMClient
from app.core.amocrm_mappings import SUBJECTS_MAPPING, get_direction_enum_id_by_class, get_direction_enum_id_by_course_name
from app.core.settings import settings
from app.db.event_logger import EventLogger
from app.models.payment_webhook import PaymentUTM, PaymentWebhook

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    """Результат обработки оплаты."""

    status: str  # "success", "duplicate", "contact_not_found", "lead_not_found", "error", "skipped"
    contact_id: int | None = None
    lead_id: int | None = None
    message: str = ""
    error: str | None = None


class PaymentProcessor:
    """Процессор для обработки оплат с платформы."""

    def __init__(self, amocrm_client: AmoCRMClient | None = None, event_logger: EventLogger | None = None) -> None:
        """
        Инициализация процессора.

        Args:
            amocrm_client: Клиент для работы с amoCRM API (опционально для тестов)
            event_logger: Логгер событий (опционально для тестов)
        """
        self.client = amocrm_client or AmoCRMClient()
        self.event_logger = event_logger or EventLogger()

    def is_op_payment(self, payment: PaymentWebhook) -> bool:
        """
        Проверить является ли это OP платежом (utm_source=op).

        Args:
            payment: Данные об оплате

        Returns:
            True если utm_source=op, иначе False
        """
        utm_source = (payment.course_order.utm.source or "").lower()
        return utm_source == "op"

    def determine_pipeline_and_status(self, utm: PaymentUTM, user_class: int | None = None) -> tuple[int, int]:
        """
        Определить воронку и этап на основе класса пользователя и UTM меток.

        ЛОГИКА:
        1. ПРИОРИТЕТ: Если класс 7 или 8 → воронка "7/8 класс"
        2. ВСЕ остальные автооплаты идут в этап "Автооплаты ООО", но в разные воронки:
           - ПАРТНЕРЫ - если utm_source совпал с правилами
           - Сайт Яндекс - если utm_medium совпал с правилами
           - Сайт - по умолчанию (если ничего не совпало)

        Args:
            utm: Объект PaymentUTM с UTM метками из payment.course_order.utm
            user_class: Класс пользователя (7, 8, 9, 10, 11 и т.д.)

        Returns:
            Кортеж (pipeline_id, status_id):
            - pipeline_id: ID воронки
            - status_id: ID этапа "Автооплаты ООО" для соответствующей воронки
        """
        if user_class in [7, 8]:
            logger.info(
                f"Класс {user_class} обнаружен → воронка '7/8 класс' "
                f"(ID={settings.PIPELINE_7_8_CLASS}) → Автооплаты ООО (ID={settings.PIPELINE_7_8_CLASS_AUTOPAY})"
            )
            return (
                settings.PIPELINE_7_8_CLASS,
                settings.PIPELINE_7_8_CLASS_AUTOPAY,
            )

        utm_source = (utm.source or "").lower()
        utm_medium = (utm.medium or "").lower()

        logger.info(f"Определение воронки: user_class={user_class}, utm_source='{utm_source}', utm_medium='{utm_medium}'")

        partner_sources = settings.PARTNER_SOURCES.split(",")
        for partner in partner_sources:
            if partner.strip().lower() in utm_source:
                logger.info(
                    f"UTM совпали: ПАРТНЕРЫ (ID={settings.AMO_PIPELINE_PARTNERS}, "
                    f"utm_source содержит '{partner}') → Автооплаты ООО"
                )
                return (
                    settings.AMO_PIPELINE_PARTNERS,
                    settings.AMO_STATUS_AUTOPAY_PARTNERS,
                )

        yandex_mediums = settings.YANDEX_MEDIUMS.split(",")
        for medium in yandex_mediums:
            if medium.strip().lower() in utm_medium:
                logger.info(
                    f"UTM совпали: Сайт Яндекс (ID={settings.AMO_PIPELINE_YANDEX}, "
                    f"utm_medium содержит '{medium}') → Автооплаты ООО"
                )
                return (
                    settings.AMO_PIPELINE_YANDEX,
                    settings.AMO_STATUS_AUTOPAY_YANDEX,
                )

        logger.info(f"UTM НЕ совпали: Сайт (ID={settings.AMO_PIPELINE_SITE}, по умолчанию) → Автооплаты ООО")
        return (
            settings.AMO_PIPELINE_SITE,
            settings.AMO_STATUS_AUTOPAY_SITE,
        )

    async def process_payment(self, payment: PaymentWebhook) -> ProcessResult:
        """
        Обработать оплату с платформы.

        Шаги обработки:
        1. Проверка дубликата по payment_id
        2. Матчинг контакта (tg_id → phone → email)
        3. Создание контакта с UTM (если не найден и CREATE_IF_NOT_FOUND=True)
        4. Обновление полей контакта (tg_id, tg_username) - только пустые
        5. Матчинг активной сделки (во ВСЕХ воронках)
        6. Создание сделки в AMO_PIPELINE_ID (если не найдена и CREATE_IF_NOT_FOUND=True)
        7. Обновление полей сделки (суммы, статус, даты, IDs)
        8. Создание примечания в сделке

        Args:
            payment: Данные об оплате

        Returns:
            ProcessResult с результатом обработки
        """
        payment_id = payment.payment_id or "unknown"
        logger.info("=" * 80)
        logger.info(f"Начало обработки оплаты: payment_id={payment_id}")
        logger.info("=" * 80)

        try:
            # Шаг 1: Проверка дубликата по payment_id
            if await self.event_logger.is_payment_processed(payment_id):
                logger.warning(f"Payment {payment_id} already processed (duplicate)")
                return ProcessResult(
                    status="duplicate",
                    message=f"Payment {payment_id} already processed",
                )

            # ========================================================================
            # ЛОГИКА ПОИСКА СУЩЕСТВУЮЩИХ СДЕЛОК
            # ========================================================================
            user = payment.course_order.user
            tg_id = user.telegram_id or None
            phone = user.phone or None
            email = user.email or None

            existing_lead = None
            is_op_utm = self.is_op_payment(payment)

            # ШАГ 1: ВСЕГДА искать сделки с названием "Оплата: ОГЭ/ЕГЭ/Средняя школа" в 2 воронках
            logger.info("=" * 80)
            logger.info("ШАГ 1: Поиск сделок с названием 'Оплата: ОГЭ/ЕГЭ/Средняя школа'")
            logger.info("=" * 80)

            existing_lead = await self.client.find_op_lead(
                telegram_id=tg_id,
                phone=phone,
                email=email,
                is_utm_op=False,  # Поиск по названию → 2 воронки
            )

            if existing_lead:
                logger.info(f"Сделка с названием 'Оплата:...' найдена: {existing_lead['id']}")

            # ШАГ 2: ЕСЛИ utm_source=op И сделка не найдена на шаге 1
            if is_op_utm and not existing_lead:
                logger.info("=" * 80)
                logger.info("ШАГ 2: utm_source=op обнаружен, расширенный поиск в 14 воронках")
                logger.info("=" * 80)

                existing_lead = await self.client.find_op_lead(
                    telegram_id=tg_id,
                    phone=phone,
                    email=email,
                    is_utm_op=True,  # utm_source=op → 13 воронок
                )

                if existing_lead:
                    logger.info(f"OP сделка найдена в расширенном поиске: {existing_lead['id']}")

            # ШАГ 2.5: ЕСЛИ СДЕЛКА НАЙДЕНА - проверить, не в необработанном ли этапе
            if existing_lead:
                current_pipeline = existing_lead["pipeline_id"]
                current_status = existing_lead["status_id"]
                
                # Необработанные этапы (менеджер еще не работал)
                UNPROCESSED_STATUSES = {
                    settings.AMO_PIPELINE_SITE: [82318294, 41044773],      # Не оплативший, Новая заявка
                    settings.AMO_PIPELINE_YANDEX: [82465570, 79982002],    # Не оплативший, Новая заявка
                    settings.AMO_PIPELINE_PARTNERS: [82324050, 69764098],  # Не оплатившие, Новая заявка
                    settings.PIPELINE_7_8_CLASS: [82320578, 81078194],     # Не оплатившие, Новая
                }
                
                unprocessed = UNPROCESSED_STATUSES.get(current_pipeline, [])
                
                if current_status in unprocessed:
                    logger.info("=" * 80)
                    logger.info(
                        f"СДЕЛКА {existing_lead['id']} В НЕОБРАБОТАННОМ ЭТАПЕ "
                        f"(pipeline={current_pipeline}, status={current_status})"
                    )
                    logger.info("ИГНОРИРУЕМ её → создаем новую сделку в автооплатах")
                    logger.info("=" * 80)
                    existing_lead = None  # Сбрасываем, чтобы пошла логика создания новой

            # ШАГ 3: ЕСЛИ СДЕЛКА НАЙДЕНА (И ОБРАБОТАНА МЕНЕДЖЕРОМ) - обновить БЕЗ смены воронки/статуса
            if existing_lead:
                logger.info("=" * 80)
                logger.info("СДЕЛКА НАЙДЕНА - обновляем БЕЗ смены воронки/статуса")
                logger.info("=" * 80)

                lead_id = existing_lead["id"]
                current_pipeline = existing_lead["pipeline_id"]
                current_status = existing_lead["status_id"]

                # Получить ID контакта из сделки
                embedded_contacts = existing_lead.get("_embedded", {}).get("contacts", [])
                contact_id = embedded_contacts[0]["id"] if embedded_contacts else None

                if not contact_id:
                    logger.error(f"Lead {lead_id} has no contacts!")
                    raise ValueError(f"Lead {lead_id} has no contacts")

                logger.info(
                    f"Обновляем сделку: lead_id={lead_id}, contact_id={contact_id}, "
                    f"pipeline={current_pipeline}, status={current_status}"
                )

                # Обновить только поля платежа (БЕЗ status_id и БЕЗ перезаписи UTM!)
                await self._update_lead_fields(lead_id, payment, status_id=None, skip_utm=True)

                # Добавить примечание
                await self._add_payment_note(lead_id, payment)

                # Создать задачу для менеджера сделки
                logger.info(f"Создание задачи для менеджера сделки {lead_id}")
                try:
                    task_id = await self.client.create_task_for_contact_manager(
                        lead_id=lead_id,
                        text="Пришел платеж. Проверь все данные на корректность и отправь сделку в нужный этап",
                    )
                    logger.info(f"Задача создана: task_id={task_id}")
                except Exception as task_error:
                    logger.error(f"Ошибка создания задачи: {task_error}")
                    # Продолжаем выполнение, задача не критична

                logger.info(f"Платеж {payment_id} обработан успешно (существующая сделка обновлена)")
                logger.info("=" * 80)

                await self.event_logger.log_payment(
                    payment_id=payment_id,
                    amount=payment.total_cost,
                    payment_date=payment.course_order.updated_at,
                    status="success",
                    contact_id=contact_id,
                    lead_id=lead_id,
                    pipeline_id=current_pipeline,
                    status_id=current_status,
                    is_lead_created=False,  # Обновили существующую
                    payload=payment.model_dump_json(),
                )

                return ProcessResult(
                    status="success",
                    contact_id=contact_id,
                    lead_id=lead_id,
                    message=f"Payment {payment_id} processed (existing lead updated)",
                )

            # ========================================================================
            # СТАНДАРТНАЯ ЛОГИКА - создание новой сделки в автооплатах
            # ========================================================================
            logger.info("=" * 80)
            logger.info("СДЕЛКА НЕ НАЙДЕНА - создаем новую в автооплатах")
            logger.info("=" * 80)

            utm = payment.course_order.utm
            user_class = payment.course_order.user.user_class
            pipeline_id, status_id = self.determine_pipeline_and_status(utm, user_class)

            logger.info(f"Целевая воронка: pipeline_id={pipeline_id}, status_id={status_id}")

            # ========================================================================
            # СТАРАЯ ЛОГИКА (ЗАКОММЕНТИРОВАНА): Поиск существующего контакта
            # ========================================================================
            # # Шаг 2: Матчинг контакта
            # contact = await self._find_or_create_contact(payment)
            # if contact is None:
            #     logger.error("Contact not found and CREATE_IF_NOT_FOUND=False")
            #     return ProcessResult(
            #         status="contact_not_found",
            #         message="Contact not found and CREATE_IF_NOT_FOUND=False",
            #     )
            #
            # contact_id = contact["id"] if isinstance(contact, dict) else contact
            # logger.info(f"Contact resolved: ID={contact_id}")
            #
            # # Шаг 3: Обновление полей контакта (идемпотентно)
            # await self._update_contact_fields(contact_id, payment)
            # ========================================================================

            # НОВАЯ ЛОГИКА: Всегда создавать новый контакт
            logger.info("Создание нового контакта для каждого платежа...")
            user = payment.course_order.user
            name = f"{user.first_name} {user.last_name}".strip() or "Клиент без имени"
            phone = user.phone or None
            email = user.email or None
            tg_id = user.telegram_id or None
            tg_username = user.telegram_tag or None

            contact_id = await self.client.create_contact(
                name=name,
                phone=phone,
                email=email,
                tg_id=tg_id,
                tg_username=tg_username,
            )
            logger.info(f"Новый контакт создан: ID={contact_id}")

            # ========================================================================
            # СТАРАЯ ЛОГИКА (ЗАКОММЕНТИРОВАНА): Поиск существующей сделки
            # ========================================================================
            # # Шаг 4: Матчинг активной сделки
            # lead_result = await self._find_or_create_lead(contact_id, payment, pipeline_id, status_id)
            # if lead_result is None:
            #     logger.error("Lead not found and CREATE_IF_NOT_FOUND=False")
            #     return ProcessResult(
            #         status="lead_not_found",
            #         contact_id=contact_id,
            #         message="Lead not found and CREATE_IF_NOT_FOUND=False",
            #     )
            #
            # lead, is_lead_created = lead_result
            # lead_id = lead["id"] if isinstance(lead, dict) else lead
            # logger.info(f"Lead resolved: ID={lead_id}")
            # ========================================================================

            # НОВАЯ ЛОГИКА: Всегда создавать новую сделку
            logger.info(f"Создание новой сделки в воронке {pipeline_id} (этап {status_id})...")

            user_name = f"{user.first_name} {user.last_name}".strip() or "Клиент без имени"
            lead_name = f"Оплата платформы - {user_name}"
            price = payment.total_cost

            utm = payment.course_order.utm
            utm_source = utm.source or None
            utm_medium = utm.medium or None
            utm_campaign = utm.campaign or None
            utm_content = utm.content or None
            utm_term = utm.term or None
            ym_uid = utm.ym or None
            domain = payment.course_order.domain or None
            user_class_value = payment.course_order.user.user_class
            is_parent_value = payment.course_order.is_parent
            promo_code_value = payment.course_order.code if payment.course_order.code else None

            lead_id = await self.client.create_lead(
                name=lead_name,
                contact_id=contact_id,
                price=price,
                pipeline_id=pipeline_id,
                status_id=status_id,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                utm_content=utm_content,
                utm_term=utm_term,
                ym_uid=ym_uid,
                domain=domain,
                user_class=user_class_value,
                is_parent=is_parent_value,
                promo_code=promo_code_value,
            )
            logger.info(f"Новая сделка создана: ID={lead_id}")

            lead = {"id": lead_id}
            is_lead_created = True

            # Шаг 5: Обновление полей сделки (skip_utm=True, т.к. UTM уже установлены в create_lead)
            await self._update_lead_fields(lead_id, payment, status_id, skip_utm=True)

            # Шаг 6: Создание примечания
            await self._add_payment_note(lead_id, payment)

            logger.info(f"Payment {payment_id} processed successfully")
            logger.info("=" * 80)

            await self.event_logger.log_payment(
                payment_id=payment_id,
                amount=payment.total_cost,
                payment_date=payment.course_order.updated_at,
                status="success",
                contact_id=contact_id,
                lead_id=lead_id,
                pipeline_id=pipeline_id,
                status_id=status_id,
                is_lead_created=is_lead_created,
                payload=payment.model_dump_json(),
            )

            return ProcessResult(
                status="success",
                contact_id=contact_id,
                lead_id=lead_id,
                message=f"Payment {payment_id} processed successfully",
            )

        except Exception as e:
            logger.error(f"Error processing payment {payment_id}: {e}", exc_info=True)

            try:
                await self.event_logger.log_payment(
                    payment_id=payment_id,
                    amount=payment.total_cost,
                    payment_date=payment.course_order.updated_at,
                    status="error",
                    error=str(e),
                    payload=payment.model_dump_json(),
                )
            except Exception as log_error:
                logger.error(f"Failed to log error to database: {log_error}")

            return ProcessResult(
                status="error",
                message=f"Error processing payment: {str(e)}",
                error=str(e),
            )

    async def _find_or_create_contact(self, payment: PaymentWebhook) -> dict | int | None:
        """
        Найти или создать контакт.

        Приоритеты поиска:
        1. По tg_id (если есть)
        2. По телефону
        3. По email

        Args:
            payment: Данные об оплате

        Returns:
            Данные контакта (dict) или ID контакта (int), или None если не найден
        """
        user = payment.course_order.user
        tg_id = user.telegram_id or None
        phone = user.phone or None
        email = user.email or None

        logger.info(f"Поиск контакта: tg_id={tg_id}, phone={phone}, email={email}")

        contact = await self.client.find_contact(tg_id=tg_id, phone=phone, email=email)

        if contact:
            logger.info(f"Контакт найден: ID={contact['id']}")
            return contact

        logger.warning("Контакт не найден")

        if not settings.CREATE_IF_NOT_FOUND:
            logger.warning("CREATE_IF_NOT_FOUND=False, контакт не будет создан")
            return None

        logger.info("Создание нового контакта с UTM метками...")
        name = f"{user.first_name} {user.last_name}".strip() or "Клиент без имени"
        tg_username = user.telegram_tag or None

        contact_id = await self.client.create_contact(
            name=name,
            phone=phone,
            email=email,
            tg_id=tg_id,
            tg_username=tg_username,
        )

        logger.info(f"Контакт создан: ID={contact_id}")
        return contact_id

    async def _update_contact_fields(self, contact_id: int, payment: PaymentWebhook) -> None:
        """
        Обновить поля контакта (идемпотентно - только пустые поля).

        Args:
            contact_id: ID контакта
            payment: Данные об оплате
        """
        user = payment.course_order.user
        tg_id = user.telegram_id or None
        tg_username = user.telegram_tag or None
        email = user.email or None

        if not tg_id and not tg_username and not email:
            logger.info("Нет данных для обновления контакта")
            return

        logger.info(f"Обновление полей контакта {contact_id}...")
        await self.client.update_contact_fields(
            contact_id=contact_id,
            tg_id=tg_id,
            tg_username=tg_username,
            email=email,
        )

    async def _find_or_create_lead(
        self, contact_id: int, payment: PaymentWebhook, pipeline_id: int, status_id: int
    ) -> tuple[dict | int, bool] | None:
        """
        Найти или создать активную сделку для контакта.

        Поиск во ВСЕХ воронках, выбор последней обновленной активной сделки.

        Args:
            contact_id: ID контакта
            payment: Данные об оплате
            pipeline_id: ID воронки для создания новой сделки
            status_id: ID этапа для создания новой сделки

        Returns:
            tuple[dict | int, bool] | None: (сделка, была_создана) или None если не найдена
        """
        user = payment.course_order.user
        telegram_id = str(user.telegram_id) if user.telegram_id else None
        phone = user.phone or None
        email = user.email or None

        logger.info(f"Поиск активной сделки для контакта {contact_id}...")

        lead = await self.client.find_active_lead(contact_id=contact_id, telegram_id=telegram_id, phone=phone, email=email)

        if lead:
            logger.info(f"Активная сделка найдена: ID={lead['id']}, Pipeline={lead.get('pipeline_id')}")
            return (lead, False)  # Найдена, не создана

        logger.warning("Активная сделка не найдена")

        if not settings.CREATE_IF_NOT_FOUND:
            logger.warning("CREATE_IF_NOT_FOUND=False, сделка не будет создана")
            return None

        logger.info(f"Создание новой сделки в воронке {pipeline_id} (этап {status_id}) с UTM метками...")

        user_name = f"{user.first_name} {user.last_name}".strip() or "Клиент без имени"
        lead_name = f"Оплата платформы - {user_name}"

        price = payment.total_cost

        utm = payment.course_order.utm
        utm_source = utm.source or None
        utm_medium = utm.medium or None
        utm_campaign = utm.campaign or None
        utm_content = utm.content or None
        utm_term = utm.term or None
        ym_uid = utm.ym or None
        domain = payment.course_order.domain or None
        user_class_value = payment.course_order.user.user_class
        is_parent_value = payment.course_order.is_parent
        promo_code_value = payment.course_order.code if payment.course_order.code else None

        lead_id = await self.client.create_lead(
            name=lead_name,
            contact_id=contact_id,
            price=price,
            pipeline_id=pipeline_id,
            status_id=status_id,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            ym_uid=ym_uid,
            domain=domain,
            user_class=user_class_value,
            is_parent=is_parent_value,
            promo_code=promo_code_value,
        )

        logger.info(f"✓ Сделка создана: ID={lead_id}")
        return ({"id": lead_id}, True)  # Создана

    async def _update_lead_fields(
        self, lead_id: int, payment: PaymentWebhook, status_id: int | None, skip_utm: bool = False
    ) -> None:
        """
        Обновить кастомные поля сделки.

        Обновляемые поля:
        - Предметы (из списка курсов)
        - Направление курса (ЕГЭ/ОГЭ)
        - Сумма последней оплаты (amount)
        - Бюджет (общая сумма покупок - инкрементально)
        - Статус оплаты
        - Дата/время последней оплаты
        - Payment ID
        - Этап сделки (если status_id передан)
        - UTM метки (если skip_utm=False)

        Args:
            lead_id: ID сделки
            payment: Данные об оплате
            status_id: ID этапа для обновления сделки (если None - этап не меняется)
            skip_utm: Если True - не обновлять UTM метки (используется после create_lead)
        """
        logger.info(f"Обновление полей сделки {lead_id}...")

        subjects_enum_ids = []
        direction_enum_id = None

        # Приоритет 1: Определяем направление по названию первого платного курса
        try:
            for item in payment.course_order.course_order_items:
                if item.cost > 0:  # Только платные курсы
                    course_name = item.course.name
                    direction_enum_id = get_direction_enum_id_by_course_name(course_name)
                    if direction_enum_id:
                        logger.info(f"Direction determined by course name: '{course_name}' → {direction_enum_id}")
                        break
        except Exception as e:
            logger.warning(f"Error determining direction by course name: {e}")

        # Приоритет 2: Если по названию не определили, пробуем по классу пользователя
        if direction_enum_id is None:
            user_class = payment.course_order.user.user_class
            if user_class:
                try:
                    direction_enum_id = get_direction_enum_id_by_class(user_class)
                    if direction_enum_id:
                        logger.info(f"Direction determined by user class: {user_class} → {direction_enum_id}")
                except Exception as e:
                    logger.warning(f"Error determining direction by class: {e}")

        # Приоритет 3 (Fallback): Старая логика по project (ЕГЭ/ОГЭ)
        if direction_enum_id is None:
            try:
                for item in payment.course_order.course_order_items:
                    project_name = item.course.subject.project
                    if project_name == "ОГЭ":
                        direction_enum_id = settings.AMO_DIRECTION_OGE
                        logger.info(f"Direction determined by project (fallback): 'ОГЭ' → {direction_enum_id}")
                        break
                    elif project_name == "ЕГЭ":
                        direction_enum_id = settings.AMO_DIRECTION_EGE
                        logger.info(f"Direction determined by project (fallback): 'ЕГЭ' → {direction_enum_id}")
                        break
            except Exception as e:
                logger.warning(f"Error determining direction by project: {e}")

        # Последний fallback: ЕГЭ по умолчанию
        if direction_enum_id is None:
            direction_enum_id = settings.AMO_DIRECTION_EGE
            logger.warning(f"Direction not determined, using ultimate fallback: EGE → {direction_enum_id}")

        # Собираем предметы
        for item in payment.course_order.course_order_items:
            subject_name = item.course.subject.name

            subject_enum_id = SUBJECTS_MAPPING.get(subject_name)
            if subject_enum_id:
                subjects_enum_ids.append(subject_enum_id)
            else:
                logger.warning(f"Предмет '{subject_name}' не найден в маппинге")

        subjects_enum_ids = list(set(subjects_enum_ids))
        
        purchased_subjects_count = len(subjects_enum_ids) if subjects_enum_ids else 0

        amount = payment.total_cost
        payment_status = payment.course_order.status
        payment_date = payment.course_order.updated_at
        payment_id = payment.course_order.payment_id

        # UTM метки (если не пропускаем)
        utm_source = None
        utm_medium = None
        utm_campaign = None
        utm_content = None
        utm_term = None
        ym_uid = None

        if not skip_utm:
            utm = payment.course_order.utm
            utm_source = utm.source or None
            utm_medium = utm.medium or None
            utm_campaign = utm.campaign or None
            utm_content = utm.content or None
            utm_term = utm.term or None
            ym_uid = utm.ym or None

        domain = payment.course_order.domain or None
        user_class_value = payment.course_order.user.user_class
        is_parent_value = payment.course_order.is_parent
        promo_code_value = payment.course_order.code if payment.course_order.code else None

        await self.client.update_lead_fields(
            lead_id=lead_id,
            subjects=subjects_enum_ids if subjects_enum_ids else None,
            direction=direction_enum_id,
            last_payment_amount=amount,
            payment_status=payment_status,
            last_payment_date=payment_date,
            payment_id=payment_id,
            status_id=status_id,
            total_paid=amount,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            ym_uid=ym_uid,
            domain=domain,
            purchased_subjects_count=purchased_subjects_count,
            user_class=user_class_value,
            is_parent=is_parent_value,
            promo_code=promo_code_value,
        )

        if status_id:
            logger.info(f"Поля сделки {lead_id} обновлены, бюджет установлен {amount}, переведена в этап {status_id}")
        else:
            logger.info(f"Поля сделки {lead_id} обновлены, бюджет установлен {amount}, этап НЕ изменен (OP платеж)")

    async def _add_payment_note(self, lead_id: int, payment: PaymentWebhook) -> None:
        """
        Создать примечание в сделке с деталями оплаты.

        Шаблон примечания:
        ```
        Оплата проведена
        Имя клиента: {name}
        Дата/время: {datetime_local} / {datetime_utc}
        Статус: {status}
        Сумма: {amount} {currency}
        Метод: {payment_method}
        Курсы: {courses}
        Промокод: {promo_code}
        TGID: {tg_id} | TG Username: @{tg_username} | Телефон: {phone}
        Источник: {source}
        Payment ID: {payment_id}
        ```

        Args:
            lead_id: ID сделки
            payment: Данные об оплате
        """
        logger.info(f"Создание примечания в сделке {lead_id}...")

        user = payment.course_order.user
        order = payment.course_order
        utm = order.utm

        name = f"{user.first_name} {user.last_name}".strip() or "Не указано"

        datetime_str = order.updated_at
        try:
            dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            datetime_utc = dt.isoformat() + "Z"
            datetime_local = dt.strftime("%Y-%m-%d %H:%M:%S") + " (Moscow)"
        except Exception as e:
            logger.warning(f"Ошибка парсинга даты: {e}")
            datetime_local = datetime_str
            datetime_utc = datetime_str

        courses_list = []
        for item in order.course_order_items:
            course_name = item.course.name
            subject_name = item.course.subject.name
            courses_list.append(f"{course_name} ({subject_name})")
        courses_str = "\n  ".join(courses_list)

        note_parts = [
            "Оплата проведена",
            "",
            f"Имя клиента: {name}",
            f"Дата/время: {datetime_local}",
            f"Дата/время UTC: {datetime_utc}",
            f"Статус: {order.status}",
            f"Сумма: {payment.total_cost} {order.currency}",
        ]

        if order.payment_method:
            note_parts.append(f"Метод оплаты: {order.payment_method}")

        note_parts.append(f"Курсы:\n  {courses_str}")

        if order.code:
            note_parts.append(f"Промокод: {order.code}")

        tg_parts = []
        if user.telegram_id:
            tg_parts.append(f"TGID: {user.telegram_id}")
        if user.telegram_tag:
            tg_parts.append(f"TG Username: @{user.telegram_tag}")
        if user.phone:
            tg_parts.append(f"Телефон: {user.phone}")
        if tg_parts:
            note_parts.append(" | ".join(tg_parts))

        if utm.source:
            note_parts.append(f"Источник: {utm.source}")

        if order.payment_id:
            note_parts.append(f"Payment ID: {order.payment_id}")

        note_text = "\n".join(note_parts)

        await self.client.add_lead_note(lead_id, note_text)

        logger.info(f"✓ Примечание добавлено в сделку {lead_id}")
