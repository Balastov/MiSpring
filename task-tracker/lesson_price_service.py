"""Стоимость урока ученика: история и выбор цены на дату."""
from datetime import date, datetime

from extensions import db
from models import StudentLessonPrice


def parse_effective_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip()[:10], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def lesson_price_history(student_id):
    return (
        StudentLessonPrice.query.filter_by(student_id=student_id)
        .order_by(
            StudentLessonPrice.effective_from.is_(None),
            StudentLessonPrice.effective_from.asc(),
            StudentLessonPrice.id.asc(),
        )
        .all()
    )


def has_dated_price_history(student_id):
    return (
        StudentLessonPrice.query.filter(
            StudentLessonPrice.student_id == student_id,
            StudentLessonPrice.effective_from.isnot(None),
        ).count()
        > 0
    )


def price_at_date(entries, lesson_dt, fallback=None):
    """Цена на дату урока по записям истории (entries — список StudentLessonPrice)."""
    if not entries:
        return fallback
    if lesson_dt is None:
        return fallback
    d = lesson_dt.date() if isinstance(lesson_dt, datetime) else lesson_dt

    initial = [e for e in entries if e.effective_from is None]
    dated = [e for e in entries if e.effective_from is not None and e.effective_from <= d]
    if dated:
        return max(dated, key=lambda e: e.effective_from).price
    if initial:
        return initial[-1].price
    return fallback


def build_price_history_index(student_ids):
    if not student_ids:
        return {}
    rows = StudentLessonPrice.query.filter(StudentLessonPrice.student_id.in_(student_ids)).all()
    index = {}
    for row in rows:
        index.setdefault(row.student_id, []).append(row)
    for sid in index:
        index[sid].sort(
            key=lambda e: (0 if e.effective_from is None else 1, e.effective_from or date.min, e.id)
        )
    return index


def sync_student_lesson_price(student, new_price, effective_from=None, created_by_user_id=None):
    """
    Обновляет user.lesson_price и историю.
    - Первая цена или единственная начальная (без даты) — effective_from не обязателен.
    - При наличии датированных записей новая цена требует effective_from.
    """
    history = lesson_price_history(student.id)

    if new_price is None or new_price == '':
        student.lesson_price = None
        StudentLessonPrice.query.filter_by(student_id=student.id).delete()
        return None

    try:
        price = float(new_price)
    except (TypeError, ValueError):
        return 'Некорректная цена'
    if price < 0:
        return 'Стоимость урока не может быть отрицательной'

    eff_date = parse_effective_date(effective_from)

    if not history:
        db.session.add(
            StudentLessonPrice(
                student_id=student.id,
                price=price,
                effective_from=None,
                created_by_user_id=created_by_user_id,
            )
        )
        student.lesson_price = price
        return None

    if len(history) == 1 and history[0].effective_from is None and eff_date is None:
        history[0].price = price
        student.lesson_price = price
        return None

    if eff_date is None:
        return 'Укажите дату, с которой действует новая стоимость'

    existing = next((h for h in history if h.effective_from == eff_date), None)
    if existing:
        existing.price = price
    else:
        db.session.add(
            StudentLessonPrice(
                student_id=student.id,
                price=price,
                effective_from=eff_date,
                created_by_user_id=created_by_user_id,
            )
        )
    student.lesson_price = price
    return None
