"""Настройки приложения через переменные окружения."""

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    AMO_ACCESS_TOKEN: str = Field(..., description="AmoCRM долгосрочный токен доступа")
    AMO_BASE_URL: str = Field(default="https://api-b.amocrm.ru", description="AmoCRM API Base URL")

    AMO_CONTACT_FIELD_TG_ID: int = Field(..., description="ID поля 'Telegram user id' в контакте")
    AMO_CONTACT_FIELD_TG_USERNAME: int = Field(..., description="ID поля 'Telegram username' в контакте")
    AMO_CONTACT_FIELD_TG_NAME: int = Field(..., description="ID поля 'Telegram name' в контакте")

    AMO_LEAD_FIELD_SUBJECTS: int = Field(..., description="ID поля 'Какой предмет выбрал' в сделке")
    AMO_LEAD_FIELD_DIRECTION: int = Field(..., description="ID поля 'Направления курса' в сделке")
    AMO_LEAD_FIELD_PURCHASE_COUNT: int = Field(..., description="ID поля 'Купленных курсов' в сделке")

    # Enum ID для предметов
    AMO_SUBJECT_OBSHCHESTVO: int = Field(..., description="enum_id для 'Обществознание'")
    AMO_SUBJECT_ENGLISH: int = Field(..., description="enum_id для 'Английский язык'")
    AMO_SUBJECT_HISTORY: int = Field(..., description="enum_id для 'История'")
    AMO_SUBJECT_RUSSIAN: int = Field(..., description="enum_id для 'Русский'")
    AMO_SUBJECT_PHYSICS: int = Field(..., description="enum_id для 'Физика'")
    AMO_SUBJECT_CHEMISTRY: int = Field(..., description="enum_id для 'Химия'")
    AMO_SUBJECT_LITERATURE: int = Field(..., description="enum_id для 'Литература'")
    AMO_SUBJECT_MATH_PROF_MASHA: int = Field(..., description="enum_id для 'Проф. мат (Маша)'")
    AMO_SUBJECT_MATH_BASE: int = Field(..., description="enum_id для 'Математика (база)'")
    AMO_SUBJECT_BIOLOGY_ZHENYA: int = Field(..., description="enum_id для 'Биология (Женя)'")
    AMO_SUBJECT_BIOLOGY_GELYA: int = Field(..., description="enum_id для 'Биология (Геля)'")
    AMO_SUBJECT_INFORMATICS: int = Field(..., description="enum_id для 'Информатика'")
    AMO_SUBJECT_MATH_PROF_SASHA: int = Field(..., description="enum_id для 'Проф. мат (Саша)'")

    # Enum ID для направлений
    AMO_DIRECTION_OGE: int = Field(..., description="enum_id для направления 'ОГЭ'")
    AMO_DIRECTION_EGE: int = Field(...,  description="enum_id для направления 'ЕГЭ'")

    AMO_PURCHASE_COUNT_1: int = Field(..., description="enum_id для значения '1' в поле 'Купленных курсов'")
    AMO_PURCHASE_COUNT_2: int = Field(..., description="enum_id для значения '2' в поле 'Купленных курсов'")
    AMO_PURCHASE_COUNT_3: int = Field(..., description="enum_id для значения '3' в поле 'Купленных курсов'")
    AMO_PURCHASE_COUNT_4: int = Field(..., description="enum_id для значения '4' в поле 'Купленных курсов'")
    AMO_PURCHASE_COUNT_5: int = Field(..., description="enum_id для значения '5' в поле 'Купленных курсов'")
    AMO_PURCHASE_COUNT_6: int = Field(..., description="enum_id для значения '6' в поле 'Купленных курсов'")
    AMO_PURCHASE_COUNT_7: int = Field(..., description="enum_id для значения '7' в поле 'Купленных курсов'")
    AMO_PURCHASE_COUNT_8: int = Field(..., description="enum_id для значения '8' в поле 'Купленных курсов'")
    AMO_PURCHASE_COUNT_9: int = Field(..., description="enum_id для значения '9' в поле 'Купленных курсов'")
    AMO_PURCHASE_COUNT_10: int = Field(..., description="enum_id для значения '10' в поле 'Купленных курсов'")

    # UTM поля статистики (tracking_data)
    AMO_LEAD_FIELD_UTM_SOURCE: int = Field(..., description="ID поля 'utm_source' в сделке")
    AMO_LEAD_FIELD_UTM_MEDIUM: int = Field(..., description="ID поля 'utm_medium' в сделке")
    AMO_LEAD_FIELD_UTM_CAMPAIGN: int = Field(..., description="ID поля 'utm_campaign' в сделке")
    AMO_LEAD_FIELD_UTM_CONTENT: int = Field(..., description="ID поля 'utm_content' в сделке")
    AMO_LEAD_FIELD_UTM_TERM: int = Field(..., description="ID поля 'utm_term' в сделке")
    AMO_LEAD_FIELD_YM_UID: int = Field(..., description="ID поля '_ym_uid' в сделке")

    # New fields (создать позже)
    AMO_LEAD_FIELD_LAST_PAYMENT_AMOUNT: int | None = Field(None, description="ID поля 'Сумма последней оплаты' в сделке")
    AMO_LEAD_FIELD_TOTAL_PAID: int | None = Field(None, description="ID поля 'Общий оплаченный итог' в сделке")
    AMO_LEAD_FIELD_PAYMENT_STATUS: int | None = Field(None, description="ID поля 'Статус оплаты' в сделке")
    AMO_LEAD_FIELD_LAST_PAYMENT_DATE: int | None = Field(None, description="ID поля 'Дата/время последней оплаты' в сделке")
    AMO_LEAD_FIELD_INVOICE_ID: int | None = Field(None, description="ID поля 'Invoice ID' в сделке")
    AMO_LEAD_FIELD_PAYMENT_ID: int | None = Field(None, description="ID поля 'Payment ID' в сделке")

    # Воронки для автоплаты (определяются по UTM)
    AMO_PIPELINE_SITE: int = Field(..., description="ID воронки 'Сайт'")
    AMO_PIPELINE_PARTNERS: int = Field(..., description="ID воронки 'ПАРТНЕРЫ'")
    AMO_PIPELINE_YANDEX: int = Field(..., description="ID воронки 'Сайт Яндекс'")

    # Статусы сделок (общие для всех воронок)
    STATUS_SUCCESS: int = Field(default=142, description="ID статуса 'Успешно реализовано' (общий для всех воронок)")
    STATUS_CLOSED: int = Field(default=143, description="ID статуса 'Закрыто и не реализовано' (общий для всех воронок)")

    # Этапы "Автооплаты ООО" для каждой воронки
    AMO_STATUS_AUTOPAY_SITE: int = Field(..., description="ID этапа 'Автооплаты ООО' в воронке Сайт")
    AMO_STATUS_AUTOPAY_PARTNERS: int = Field(..., description="ID этапа 'Автооплаты ООО' в воронке ПАРТНЕРЫ")
    AMO_STATUS_AUTOPAY_YANDEX: int = Field(..., description="ID этапа 'Автооплаты ООО' в воронке Сайт Яндекс")

    # UTM правила для определения воронки
    PARTNER_SOURCES: str = Field(
        ...,
        description="utm_source для воронки ПАРТНЕРЫ (через запятую)"
    )
    YANDEX_MEDIUMS: str = Field(
        ...,
        description="utm_medium для воронки Сайт Яндекс (через запятую)"
    )

    CREATE_IF_NOT_FOUND: bool = Field(
        default=False,
        description="Создавать ли новый контакт/сделку, если не найдены. "
        "False - вернуть ошибку 404, True - создать автоматически",
    )

    RETRY_MAX_ATTEMPTS: int = Field(default=3, description="Максимальное количество попыток retry", ge=1, le=10)
    RETRY_WAIT_MIN: int = Field(default=2, description="Минимальное время ожидания между попытками (сек)", ge=1)
    RETRY_WAIT_MAX: int = Field(default=10, description="Максимальное время ожидания между попытками (сек)", ge=1)

    LOG_LEVEL: str = Field(default="INFO", description="Уровень логирования (DEBUG, INFO, WARNING, ERROR)")

    # Webhook security
    WEBHOOK_SECRET: str = Field(..., description="Секретный ключ для проверки подлинности webhook запросов")

    # CORS settings
    ALLOWED_ORIGINS: str = Field(
        default="https://pl.el-ed.ru",
        description="Разрешенные CORS origins (через запятую)"
    )


settings = Settings()
