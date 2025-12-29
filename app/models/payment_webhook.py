"""Pydantic модели для валидации входящих данных от платформы оплаты."""

from pydantic import BaseModel, Field


class CourseSubject(BaseModel):
    """Модель предмета курса."""

    name: str = Field(..., description="Название предмета (например, 'Русский', 'Математика')")
    project: str = Field(..., description="Название проекта (например, 'ЕГЭ', 'ОГЭ')")


class PaymentCourse(BaseModel):
    """Модель курса."""

    name: str = Field(..., description="Название курса")
    subject: CourseSubject = Field(..., description="Предмет курса")


class CourseOrderItem(BaseModel):
    """Модель элемента заказа (курс в заказе)."""

    cost: int = Field(..., description="Стоимость курса в рублях", ge=0)
    number_lessons: int = Field(..., description="Количество уроков", ge=0)
    course: PaymentCourse = Field(..., description="Информация о курсе")
    package_id: int | None = Field(None, description="ID пакета (если есть)")


class PaymentUser(BaseModel):
    """Модель данных пользователя."""

    first_name: str = Field(..., description="Имя пользователя")
    last_name: str = Field(default="", description="Фамилия пользователя")
    phone: str = Field(..., description="Телефон пользователя")
    email: str = Field(..., description="Email пользователя")
    user_class: int | None = Field(default=None, alias="class", description="Класс пользователя (7, 8, 9, 10, 11)")
    telegram_tag: str = Field(default="", description="Username в Telegram (без @)")
    telegram_id: str = Field(default="", description="Telegram ID пользователя")

    model_config = {"populate_by_name": True}


class PaymentUTM(BaseModel):
    """Модель UTM меток."""

    source: str = Field(default="", description="UTM source")
    medium: str = Field(default="", description="UTM medium")
    campaign: str = Field(default="", alias="compaign", description="UTM campaign")
    term: str = Field(default="", description="UTM term")
    content: str = Field(default="", description="UTM content")
    ym: str = Field(default="", description="Yandex Metrika")


class CourseOrder(BaseModel):
    """Модель заказа курса."""

    status: str = Field(..., description="Статус заказа (например, 'CONFIRMED')")
    amount: int = Field(..., description="Сумма заказа", ge=0)
    created_at: str = Field(..., description="Дата и время создания заказа")
    updated_at: str = Field(..., description="Дата и время последнего обновления заказа")
    code: str | int | None = Field(default="", description="Промокод (может быть строкой, числом или null)")
    course_order_items: list[CourseOrderItem] = Field(..., description="Список курсов в заказе")
    user: PaymentUser = Field(..., description="Данные пользователя")
    utm: PaymentUTM = Field(..., description="UTM метки")
    domain: str = Field(default="", description="Домен платформы")
    payment_id: str | None = Field(None, description="Уникальный ID оплаты (для защиты от дубликатов)")
    payment_method: str | None = Field(None, description="Метод оплаты (SBP, карта и т.д.)")
    currency: str = Field(default="RUB", description="Валюта оплаты")


class PaymentWebhook(BaseModel):
    """Главная модель webhook от платформы."""

    course_order: CourseOrder = Field(..., description="Данные заказа")

    @property
    def payment_id(self) -> str | None:
        """Получить payment_id из заказа."""
        return self.course_order.payment_id

    @property
    def total_cost(self) -> int:
        """Вычислить общую стоимость всех курсов в заказе."""
        return sum(item.cost for item in self.course_order.course_order_items)

    @property
    def subjects_list(self) -> list[str]:
        """Получить список всех предметов в заказе."""
        return [item.course.subject.name for item in self.course_order.course_order_items]

    @property
    def subjects_str(self) -> str:
        """Получить строку с перечислением всех предметов."""
        return ", ".join(self.subjects_list)
