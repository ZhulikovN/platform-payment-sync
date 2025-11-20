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

    # New fields (создать позже)
    AMO_LEAD_FIELD_LAST_PAYMENT_AMOUNT: int | None = Field(None, description="ID поля 'Сумма последней оплаты' в сделке")
    AMO_LEAD_FIELD_TOTAL_PAID: int | None = Field(None, description="ID поля 'Общий оплаченный итог' в сделке")
    AMO_LEAD_FIELD_PAYMENT_STATUS: int | None = Field(None, description="ID поля 'Статус оплаты' в сделке")
    AMO_LEAD_FIELD_LAST_PAYMENT_DATE: int | None = Field(None, description="ID поля 'Дата/время последней оплаты' в сделке")
    AMO_LEAD_FIELD_INVOICE_ID: int | None = Field(None, description="ID поля 'Invoice ID' в сделке")
    AMO_LEAD_FIELD_PAYMENT_ID: int | None = Field(None, description="ID поля 'Payment ID' в сделке")

    AMO_PIPELINE_ID: int = Field(..., description="ID целевой воронки для создания новых сделок")
    AMO_DEFAULT_STATUS_ID: int = Field(..., description="ID статуса по умолчанию при создании сделки")

    CREATE_IF_NOT_FOUND: bool = Field(
        default=False,
        description="Создавать ли новый контакт/сделку, если не найдены. "
        "False - вернуть ошибку 404, True - создать автоматически",
    )

    RETRY_MAX_ATTEMPTS: int = Field(default=3, description="Максимальное количество попыток retry", ge=1, le=10)
    RETRY_WAIT_MIN: int = Field(default=2, description="Минимальное время ожидания между попытками (сек)", ge=1)
    RETRY_WAIT_MAX: int = Field(default=10, description="Максимальное время ожидания между попытками (сек)", ge=1)

    LOG_LEVEL: str = Field(default="INFO", description="Уровень логирования (DEBUG, INFO, WARNING, ERROR)")


settings = Settings()
