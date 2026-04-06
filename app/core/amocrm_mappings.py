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
        9: settings.AMO_DIRECTION_CLASS_9,   # "Весенний курс 2к26 ОГЭ"
        10: settings.AMO_DIRECTION_CLASS_10, # "Весенний курс 2к26 ЕГЭ 10 класс"
        11: settings.AMO_DIRECTION_CLASS_11, # "Весенний курс 2к26 ЕГЭ 11 класс"
    }
    return class_to_direction.get(user_class)


def get_direction_enum_id_by_course_name(course_name: str) -> int | None:
    """
    Получить enum_id направления по названию курса.
    
    Логика (приоритет по порядку):
    1. Марафон 2к26 ЕГЭ → 1368150
    2. Годовой курс 2к27 (8, 9, 10, 11 класс) → новые enum_id
    3. Весенний курс 2к26 (9, 10, 11 класс) → enum_id для весеннего
    4. Математика 7/8 класс 2к26 → без изменений
    5. Fallback → по project (ЕГЭ/ОГЭ)

    Args:
        course_name: Название курса

    Returns:
        enum_id для AmoCRM или None если направление не определено
    """
    course_lower = course_name.lower()
    
    # ПРИОРИТЕТ 1: Марафон 2к26 ЕГЭ
    if "марафон 2к26" in course_lower or "марафон" in course_lower:
        return settings.AMO_DIRECTION_MARATHON_2026  # Марафон 2к26 ЕГЭ (1368150)
    
    # ПРИОРИТЕТ 2: Годовой курс 2к27
    if "годовой курс 2к27" in course_lower or "годовой 2к27" in course_lower:
        if "11 класс" in course_lower:
            return settings.AMO_DIRECTION_ANNUAL_2027_CLASS_11  # Годовой курс 2к27 ЕГЭ 11 класс (1381127)
        elif "10 класс" in course_lower:
            return settings.AMO_DIRECTION_ANNUAL_2027_CLASS_10  # Годовой курс 2к27 ЕГЭ 10 класс (1381129)
        elif "9 класс" in course_lower:
            return settings.AMO_DIRECTION_ANNUAL_2027_CLASS_9   # Годовой курс 2к27 ОГЭ 9 класс (1381131)
        elif "8 класс" in course_lower:
            return settings.AMO_DIRECTION_ANNUAL_2027_CLASS_8   # Годовой курс 2к27 ОГЭ 8 класс (1381133)
    
    # ПРИОРИТЕТ 3: Весенний курс 2к26
    if "весенний курс" in course_lower or "весенний курс 2к26" in course_lower:
        if "11 класс" in course_lower:
            return settings.AMO_DIRECTION_CLASS_11  # Весенний курс 2к26 ЕГЭ 11 класс (1380927)
        elif "10 класс" in course_lower:
            return settings.AMO_DIRECTION_CLASS_10  # Весенний курс 2к26 ЕГЭ 10 класс (1380925)
        elif "9 класс" in course_lower:
            return settings.AMO_DIRECTION_CLASS_9   # Весенний курс 2к26 ОГЭ (1380923)
    
    # ПРИОРИТЕТ 4: Математика 7/8 класс 2к26
    if "математика 8 класс" in course_lower:
        return settings.AMO_DIRECTION_CLASS_8  # Математика 8 класс 2к26
    elif "математика 7 класс" in course_lower:
        return settings.AMO_DIRECTION_CLASS_7  # Математика 7 класс 2к26
    
    return None


def get_course_type_enum_id(course_name: str) -> int | None:
    """
    Определить тип курса (Standart/PRO) по названию.
    
    Работает ТОЛЬКО для новых курсов:
    - Марафон 2к26 ЕГЭ
    - Годовой курс 2к27 (8, 9, 10, 11 класс)
    - Весенний курс 2к26 (9, 10, 11 класс)
    - Математика 2к26 (7, 8 класс)
    
    Для остальных курсов → возвращает None (не заполняем поле).
    
    Ищет в названии:
    - "standart" / "Standart" / "STANDART" → 1376634
    - "pro" / "Pro" / "PRO" → 1380929
    - Если не найдено ни одно → 1376634 (Standart по умолчанию)
    
    Args:
        course_name: Название курса
    
    Returns:
        enum_id: 1376634 (Standart) или 1380929 (PRO), или None (не заполнять)
    """
    course_lower = course_name.lower()
    
    # Проверяем только для новых курсов
    is_new_course = (
        "марафон 2к26" in course_lower or
        "марафон" in course_lower or
        "годовой курс 2к27" in course_lower or
        "годовой 2к27" in course_lower or
        "весенний курс" in course_lower or 
        "математика 8 класс 2к26" in course_lower or 
        "математика 7 класс 2к26" in course_lower
    )
    
    if not is_new_course:
        return None
    
    # Для новых курсов проверяем тип
    if "pro" in course_lower or "про" in course_lower:
        return settings.AMO_COURSE_TYPE_PRO  # 1380929
    
    if "standart" in course_lower or "стандарт" in course_lower:
        return settings.AMO_COURSE_TYPE_STANDART  # 1376634
    
    # По умолчанию для новых курсов → Standart
    return settings.AMO_COURSE_TYPE_STANDART  # 1376634

