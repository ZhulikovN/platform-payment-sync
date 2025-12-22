"""Маппинг enum_id для полей AmoCRM со списками выбора."""

from app.core.settings import settings


def normalize_phone(phone: str) -> str:
    """
    Нормализация телефона к единому формату (только цифры, начинается с 7).

    Примеры:
        +7 (987) 672-60-10 → 79876726010
        +79876726010       → 79876726010
        8 (987) 672-60-10  → 79876726010
        9876726010         → 79876726010

    Args:
        phone: Телефон в любом формате

    Returns:
        Нормализованный телефон (только цифры, начинается с 7)
    """
    if not phone:
        return phone

    digits = "".join(filter(str.isdigit, phone))

    if not digits:
        return phone

    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]

    if not digits.startswith("7") and len(digits) == 10:
        digits = "7" + digits

    return digits


EXCLUDED_STATUSES = [
    settings.AMO_STATUS_AUTOPAY_SITE,
    settings.AMO_STATUS_AUTOPAY_YANDEX,
    settings.AMO_STATUS_AUTOPAY_PARTNERS,
    settings.STATUS_SUCCESS,
    settings.STATUS_CLOSED,
]

ALLOWED_PIPELINES = [
    settings.AMO_PIPELINE_SITE,  # Сайт
    settings.AMO_PIPELINE_PARTNERS,  # Партнеры
    settings.AMO_PIPELINE_YANDEX,  # Яндекс
]

SUBJECTS_MAPPING: dict[str, int] = {
    "Обществознание": settings.AMO_SUBJECT_OBSHCHESTVO,
    "Английский язык": settings.AMO_SUBJECT_ENGLISH,
    "История": settings.AMO_SUBJECT_HISTORY,
    "Русский": settings.AMO_SUBJECT_RUSSIAN,
    "Физика": settings.AMO_SUBJECT_PHYSICS,
    "Химия": settings.AMO_SUBJECT_CHEMISTRY,
    "Литература": settings.AMO_SUBJECT_LITERATURE,
    "Проф. мат (Маша)": settings.AMO_SUBJECT_MATH_PROF_MASHA,
    "Математика (база)": settings.AMO_SUBJECT_MATH_BASE,
    "Биология (Женя)": settings.AMO_SUBJECT_BIOLOGY_ZHENYA,
    "Обществознание ОГЭ": settings.AMO_SUBJECT_OBSHCHESTVO,
    "Русский ОГЭ": settings.AMO_SUBJECT_RUSSIAN,
    "Математика ОГЭ": settings.AMO_LEAD_FIELD_SUBJECT_MATH_OGE,
    "Биология ОГЭ": settings.AMO_SUBJECT_BIOLOGY_GELYA,
    "Информатика": settings.AMO_SUBJECT_INFORMATICS,
    "Проф. мат (Саша)": settings.AMO_SUBJECT_MATH_PROF_SASHA,
    "Биология (Геля)": settings.AMO_SUBJECT_BIOLOGY_GELYA,
    "Математика": settings.AMO_LEAD_FIELD_SUBJECT_MATH_7_8,
}

DIRECTION_MAPPING: dict[str, int] = {
    "ОГЭ": settings.AMO_DIRECTION_OGE,
    "ЕГЭ": settings.AMO_DIRECTION_EGE,
}


def get_subject_enum_ids(subject_names: list[str]) -> list[int]:
    """
    Получить список enum_id для предметов.

    Args:
        subject_names: Список названий предметов

    Returns:
        Список enum_id для AmoCRM (пропускает неизвестные предметы)
    """
    enum_ids = []
    for name in subject_names:
        enum_id = SUBJECTS_MAPPING.get(name)
        if enum_id:
            enum_ids.append(enum_id)
    return enum_ids


def get_direction_enum_id(direction_name: str) -> int | None:
    """
    Получить enum_id для направления курса.

    Args:
        direction_name: Название курса

    Returns:
        enum_id для AmoCRM или None если курс не найден
    """
    return DIRECTION_MAPPING.get(direction_name)
