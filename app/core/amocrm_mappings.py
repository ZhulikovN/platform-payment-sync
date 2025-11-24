"""Маппинг enum_id для полей AmoCRM со списками выбора."""

from app.core.settings import settings

EXCLUDED_STATUSES = [
    settings.AMO_STATUS_AUTOPAY_SITE,
    settings.AMO_STATUS_AUTOPAY_YANDEX,
    settings.AMO_STATUS_AUTOPAY_PARTNERS,
    settings.STATUS_SUCCESS,
    settings.STATUS_CLOSED,
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
    "Математика ОГЭ": settings.AMO_SUBJECT_MATH_BASE,
    "Биология ОГЭ": settings.AMO_SUBJECT_BIOLOGY_GELYA,
    "Информатика": settings.AMO_SUBJECT_INFORMATICS,
    "Проф. мат (Саша)": settings.AMO_SUBJECT_MATH_PROF_SASHA,
    "Биология (Геля)": settings.AMO_SUBJECT_BIOLOGY_GELYA,
    "Математика": settings.AMO_SUBJECT_MATH_BASE,
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
