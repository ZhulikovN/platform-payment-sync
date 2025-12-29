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


def get_direction_enum_id_by_class(user_class: int) -> int | None:
    """
    Получить enum_id направления по классу пользователя.

    Args:
        user_class: Класс пользователя (7-11)

    Returns:
        enum_id для AmoCRM или None если класс не поддерживается
    """
    class_to_direction = {
        7: settings.AMO_DIRECTION_CLASS_7,   # "Математика 7 класс 2к26"
        8: settings.AMO_DIRECTION_CLASS_8,   # "Математика 8 класс 2к26"
        9: settings.AMO_DIRECTION_CLASS_9,   # "Полугодовой 2к26 ОГЭ"
        10: settings.AMO_DIRECTION_CLASS_10, # "Полугодовой 2к26 10 класс"
        11: settings.AMO_DIRECTION_CLASS_11, # "Полугодовой 2к26 11 класс"
    }
    return class_to_direction.get(user_class)


def get_direction_enum_id_by_course_name(course_name: str) -> int | None:
    """
    Получить enum_id направления по названию курса.

    Args:
        course_name: Название курса

    Returns:
        enum_id для AmoCRM или None если направление не определено
    """
    if "11 класс" in course_name:
        return settings.AMO_DIRECTION_CLASS_11
    elif "10 класс" in course_name:
        return settings.AMO_DIRECTION_CLASS_10
    elif "9 класс" in course_name or "ОГЭ" in course_name:
        return settings.AMO_DIRECTION_CLASS_9
    elif "8 класс" in course_name:
        return settings.AMO_DIRECTION_CLASS_8
    elif "7 класс" in course_name:
        return settings.AMO_DIRECTION_CLASS_7
    return None


def _get_class_enum_id(user_class: int) -> int | None:
    """
    Получить enum_id для класса пользователя.

    Args:
        user_class: Класс пользователя (7, 8, 9, 10, 11)

    Returns:
        enum_id для AmoCRM или None если класс не поддерживается
    """
    mapping = {
        7: settings.AMO_LEAD_FIELD_CLASS_7,
        8: settings.AMO_LEAD_FIELD_CLASS_8,
        9: settings.AMO_LEAD_FIELD_CLASS_9,
        10: settings.AMO_LEAD_FIELD_CLASS_10,
        11: settings.AMO_LEAD_FIELD_CLASS_11,
    }
    return mapping.get(user_class)
