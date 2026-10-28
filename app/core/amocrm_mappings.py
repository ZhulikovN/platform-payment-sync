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
    # ЕГЭ предметы
    "Обществознание": settings.AMO_SUBJECT_OBSHCHESTVO,
    "Английский язык": settings.AMO_SUBJECT_ENGLISH,
    "История": settings.AMO_SUBJECT_HISTORY,
    "Русский": settings.AMO_SUBJECT_RUSSIAN,
    "Физика": settings.AMO_SUBJECT_PHYSICS,
    "Химия": settings.AMO_SUBJECT_CHEMISTRY,
    "Литература": settings.AMO_SUBJECT_LITERATURE,
    "Проф. мат (Ильяс)": settings.AMO_SUBJECT_MATH_PROF_ILYAS,
    "Проф. мат (Маша)": settings.AMO_SUBJECT_MATH_PROF_MASHA,
    "Математика (база)": settings.AMO_SUBJECT_MATH_BASE,
    "Биология (Глеб)": settings.AMO_SUBJECT_BIOLOGY_GLEB,
    "Биология (Женя)": settings.AMO_SUBJECT_BIOLOGY_ZHENYA,
    "Информатика": settings.AMO_SUBJECT_INFORMATICS,
    "Проф. мат (Саша)": settings.AMO_SUBJECT_MATH_PROF_SASHA,
    "Биология (Геля)": settings.AMO_SUBJECT_BIOLOGY_GELYA,

    "Математика":           1378893,  # "Математика 6-8"

    # ОГЭ предметы (поле 797182)
    "Математика ОГЭ":       1378895,  # "Математика | ОГЭ"
    "Русский ОГЭ":          1381293,  # "Русский язык | ОГЭ"
    "История ОГЭ":          1381295,  # "История | ОГЭ"
    "Биология ОГЭ":         1381297,  # "Биология | ОГЭ"
    "Обществознание ОГЭ":   1381299,  # "Обществознание | ОГЭ"
    "Информатика ОГЭ":      1381301,  # "Информатика | ОГЭ"
    "География ОГЭ":        1381819,  # "География | ОГЭ"
    "Физика ОГЭ":           1381823,  # "Физика | ОГЭ"
    "Химия ОГЭ":            1381825,  # "Химия | ОГЭ"

    # ЕГЭ — География
    "География":            1381821,  # "География"

}


def get_direction_enum_id_by_class(user_class: int) -> int | None:
    """
    Получить enum_id направления по классу пользователя.

    Args:
        user_class: Класс пользователя (7-11)

    Returns:
        enum_id для AmoCRM или None если класс не поддерживается
    """
    class_to_direction = {
        6: settings.AMO_DIRECTION_MIDDLE_SCHOOL,   # Средняя Школа 2к26
        7: settings.AMO_DIRECTION_MIDDLE_SCHOOL,   # Средняя Школа 2к26
        8: settings.AMO_DIRECTION_MIDDLE_SCHOOL,   # Средняя Школа 2к26
        9: settings.AMO_DIRECTION_ANNUAL_2027_CLASS_9, # Годовой курс 2к27
        10: settings.AMO_DIRECTION_ANNUAL_2027_CLASS_10, # Годовой курс 2к27
        11: settings.AMO_DIRECTION_ANNUAL_2027_CLASS_11, # Годовой курс 2к27
    }
    return class_to_direction.get(user_class)


def get_direction_enum_id_by_course_name(course_name: str) -> int | None:
    """
    Получить enum_id направления по названию курса.

    Приоритет:
    1. Марафон 2к26 ЕГЭ
    2. Годовой курс 2к27 (по классу/типу экзамена)

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
            return settings.AMO_DIRECTION_ANNUAL_2027_CLASS_11
        elif "10 класс" in course_lower:
            return settings.AMO_DIRECTION_ANNUAL_2027_CLASS_10
        elif "9 класс" in course_lower:
            return settings.AMO_DIRECTION_ANNUAL_2027_CLASS_9
        elif "8 класс" in course_lower:
            return settings.AMO_DIRECTION_ANNUAL_2027_CLASS_8
        elif "огэ" in course_lower:
            return settings.AMO_DIRECTION_ANNUAL_2027_CLASS_9
        elif "еге" in course_lower or "ege" in course_lower:
            return settings.AMO_DIRECTION_ANNUAL_2027_CLASS_11

    return None


def get_course_type_enum_id(course_name: str) -> int | None:
    """
    Определить тариф курса (Standart/PRO) по названию.

    Работает только для актуальных курсов: Марафон 2к26, Годовой 2к27, Годовой 2к26,
    курсы 7/8/6 класса. Для остальных → None (поле не заполняем).

    Args:
        course_name: Название курса

    Returns:
        enum_id тарифа или None
    """
    course_lower = course_name.lower()

    is_new_course = (
        "марафон" in course_lower or
        "годовой 2к27" in course_lower or
        "годовой курс 2к27" in course_lower or
        "годовой 2к26" in course_lower or
        "годовой курс 2к26" in course_lower or
        "математика 7 класс" in course_lower or
        "математика 8 класс" in course_lower or
        "математика 6 класс" in course_lower or
        "русский язык 7 класс" in course_lower or
        "русский язык 8 класс" in course_lower
    )

    if not is_new_course:
        return None

    if "базовый" in course_lower:
        return 1381125  # "Базовый"

    if "премиум" in course_lower:
        return 1381195  # "Премиум"

    if "pro" in course_lower or "про" in course_lower:
        return settings.AMO_COURSE_TYPE_PRO  # "ПРО" (1380929)

    if "standart" in course_lower or "стандарт" in course_lower:
        return settings.AMO_COURSE_TYPE_STANDART  # "Стандарт" (1376634)

    return settings.AMO_COURSE_TYPE_STANDART

