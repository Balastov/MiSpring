from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from extensions import db
from models import User, StudentPayment, Task, TaskStatus, TaskType
from helpers import user_has_role
from lesson_price_service import (
    sync_student_lesson_price,
    lesson_price_history,
    build_price_history_index,
    price_at_date,
)

payments_bp = Blueprint('payments', __name__)


def sync_prepaid_marks(student):
    """
    Пересчитывает флаг is_paid на уроках ученика в периоде предоплаты.

    Логика:
    - Всего оплачено N уроков (сумма всех StudentPayment).
    - Берём все уроки ученика с start_date >= prepaid_since (кроме отменённых),
      сортируем по дате.
    - Первые N уроков (по дате) помечаем is_paid=True, остальные — is_paid=False.
    - Урок с is_paid_manual и is_paid=True не перезаписывается (ручная «оплачен»).
    - Урок с is_paid_manual и is_paid=False пересчитывается автоматически (сбрасывается manual).
    - Отменённые уроки пропускаем (не тратят баланс, не помечаются).
    - Обновляем кеш prepaid_lessons = N − кол-во проведённых среди оплаченных.
    """
    if not student or not student.prepaid_since:
        return

    lesson_type = TaskType.query.filter_by(name='Урок').first()
    if not lesson_type:
        return

    cancelled_statuses = TaskStatus.query.filter(
        (TaskStatus.name == 'Отменён') | (TaskStatus.group == 'cancelled')
    ).all()
    cancelled_ids = {s.id for s in cancelled_statuses}
    conducted_status = TaskStatus.query.filter_by(name='Проведён').first()
    conducted_id = conducted_status.id if conducted_status else None

    payments = StudentPayment.query.filter_by(student_id=student.id).all()
    total_paid = sum(p.lessons_count for p in payments)

    # Все уроки в периоде предоплаты, кроме отменённых, по дате
    all_lessons = Task.query.filter(
        Task.student_id == student.id,
        Task.task_type_id == lesson_type.id,
        Task.start_date >= student.prepaid_since,
    ).order_by(Task.start_date.asc(), Task.id.asc()).all()

    active = [t for t in all_lessons
              if not t.status_id or t.status_id not in cancelled_ids]

    assigned = 0
    conducted_in_paid = 0
    for t in active:
        manual = bool(getattr(t, 'is_paid_manual', False))
        if manual and t.is_paid:
            assigned += 1
            if conducted_id and t.status_id == conducted_id:
                conducted_in_paid += 1
            continue
        should_pay = assigned < total_paid
        t.is_paid = should_pay
        if manual and not t.is_paid:
            t.is_paid_manual = False
        assigned += 1
        if should_pay and conducted_id and t.status_id == conducted_id:
            conducted_in_paid += 1

    # Отменённые — снимаем is_paid, они не тратят баланс
    for t in all_lessons:
        if t.status_id and t.status_id in cancelled_ids:
            t.is_paid = False

    remaining = max(0, total_paid - conducted_in_paid)
    student.prepaid_lessons = remaining

    db.session.commit()


def _get_balance(student):
    """Вычисляет текущий баланс ученика."""
    payments = StudentPayment.query.filter_by(student_id=student.id).order_by(StudentPayment.payment_date).all()
    total_paid = sum(p.lessons_count for p in payments)

    conducted_count = 0
    if student.prepaid_since:
        lesson_type = TaskType.query.filter_by(name='Урок').first()
        conducted_status = TaskStatus.query.filter_by(name='Проведён').first()
        if lesson_type and conducted_status:
            conducted_count = Task.query.filter(
                Task.student_id == student.id,
                Task.task_type_id == lesson_type.id,
                Task.status_id == conducted_status.id,
                Task.start_date >= student.prepaid_since
            ).count()

    remaining = total_paid - conducted_count
    history = lesson_price_history(student.id)
    return {
        'total_paid': total_paid,
        'conducted': conducted_count,
        'remaining': remaining,
        'prepaid_since': student.prepaid_since.strftime('%d.%m.%Y') if student.prepaid_since else None,
        'prepaid_since_iso': student.prepaid_since.strftime('%Y-%m-%d') if student.prepaid_since else None,
        'lesson_price': student.lesson_price,
        'lesson_price_history': [h.to_dict() for h in history],
        'requires_price_effective_date': bool(history)
        and not (len(history) == 1 and history[0].effective_from is None),
        'payments': [p.to_dict() for p in payments],
    }


@payments_bp.route('/api/students/<int:student_id>/balance', methods=['GET'])
@login_required
def get_balance(student_id):
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    student = db.get_or_404(User, student_id)
    if student.prepaid_since:
        sync_prepaid_marks(student)
    return jsonify(_get_balance(student))


@payments_bp.route('/api/students/<int:student_id>/payment', methods=['POST'])
@login_required
def add_payment(student_id):
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    student = db.get_or_404(User, student_id)
    data = request.get_json(force=True, silent=True) or {}

    lessons_count = data.get('lessons_count')
    if not lessons_count or int(lessons_count) <= 0:
        return jsonify({'error': 'Укажите количество уроков (больше 0)'}), 400

    lessons_count = int(lessons_count)
    amount = data.get('amount')
    if amount is not None:
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return jsonify({'error': 'Некорректная сумма'}), 400

    payment_date_str = data.get('payment_date')
    if payment_date_str:
        try:
            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Некорректная дата'}), 400
    else:
        payment_date = datetime.now()

    notes = (data.get('notes') or '').strip() or None

    # Создаём запись
    payment = StudentPayment(
        student_id=student_id,
        lessons_count=lessons_count,
        amount=amount,
        payment_date=payment_date,
        notes=notes,
    )
    db.session.add(payment)

    # Если баланс был 0 — обновляем дату начала отсчёта
    current_remaining = (student.prepaid_lessons or 0)
    if current_remaining == 0:
        student.prepaid_since = payment_date

    student.prepaid_lessons = current_remaining + lessons_count
    db.session.commit()

    sync_prepaid_marks(student)

    return jsonify({'ok': True, 'balance': _get_balance(student)}), 201


@payments_bp.route('/api/students/<int:student_id>/payment/<int:payment_id>', methods=['DELETE'])
@login_required
def delete_payment(student_id, payment_id):
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    payment = db.get_or_404(StudentPayment, payment_id)
    if payment.student_id != student_id:
        return jsonify({'error': 'Не найдено'}), 404

    student = db.get_or_404(User, student_id)
    student.prepaid_lessons = max(0, (student.prepaid_lessons or 0) - payment.lessons_count)

    db.session.delete(payment)
    db.session.commit()

    sync_prepaid_marks(student)

    return jsonify({'ok': True, 'balance': _get_balance(student)})


@payments_bp.route('/api/students/<int:student_id>/lesson-price', methods=['PUT'])
@login_required
def update_lesson_price(student_id):
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    student = db.get_or_404(User, student_id)
    data = request.get_json(force=True, silent=True) or {}

    err = sync_student_lesson_price(
        student,
        data.get('lesson_price'),
        effective_from=data.get('effective_from'),
        created_by_user_id=current_user.id,
    )
    if err:
        return jsonify({'error': err}), 400

    db.session.commit()
    history = lesson_price_history(student.id)
    return jsonify({
        'ok': True,
        'lesson_price': student.lesson_price,
        'lesson_price_history': [h.to_dict() for h in history],
    })


@payments_bp.route('/api/students/<int:student_id>/test-notification', methods=['POST'])
@login_required
def test_notification(student_id):
    if not user_has_role('admin', 'owner'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    import os, asyncio
    student = db.get_or_404(User, student_id)

    # Шаг 1: токен бота
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        return jsonify({'error': 'TELEGRAM_BOT_TOKEN не задан в окружении'}), 500

    # Шаг 2: учителя с Telegram
    from models import UserRole as UR, Role
    teacher_roles = Role.query.filter(Role.name.in_(['teacher', 'owner', 'admin'])).all()
    role_ids = [r.id for r in teacher_roles]
    teacher_user_ids = [ur.user_id for ur in UR.query.filter(UR.role_id.in_(role_ids)).all()]
    teachers = User.query.filter(
        User.id.in_(teacher_user_ids),
        User.telegram_id.isnot(None),
        User.telegram_notifications == True
    ).all()

    if not teachers:
        return jsonify({'error': 'Нет пользователей с ролью teacher/owner/admin с привязанным Telegram'}), 500

    # Шаг 3: отправка
    text = (
        f'⚠️ [ТЕСТ] У ученика <b>{student.display_name}</b>'
        f' остался <b>1 оплаченный урок</b>.'
    )
    try:
        import telegram

        sent_to = []
        errors = []

        async def _send():
            bot = telegram.Bot(token=token)
            for teacher in teachers:
                try:
                    await bot.send_message(chat_id=teacher.telegram_id, text=text, parse_mode='HTML')
                    sent_to.append(teacher.display_name)
                except Exception as e:
                    errors.append(f'{teacher.display_name}: {e}')

        asyncio.run(_send())

        if errors and not sent_to:
            return jsonify({'error': 'Ошибки при отправке: ' + '; '.join(errors)}), 500

        return jsonify({'ok': True, 'sent_to': sent_to, 'errors': errors})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@payments_bp.route('/api/reports/earnings', methods=['GET'])
@login_required
def earnings_report():
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    year = request.args.get('year', type=int, default=datetime.now().year)

    payments = StudentPayment.query.filter(
        db.extract('year', StudentPayment.payment_date) == year
    ).order_by(StudentPayment.payment_date).all()

    # Группируем по месяцам
    months = {}
    for p in payments:
        key = p.payment_date.month
        if key not in months:
            months[key] = {'month': key, 'month_name': _month_name(key), 'total_amount': 0.0, 'total_lessons': 0, 'payments': []}
        months[key]['total_amount'] += p.amount or 0
        months[key]['total_lessons'] += p.lessons_count

        student = db.session.get(User, p.student_id)
        entry = p.to_dict()
        entry['student_name'] = student.display_name if student else '—'
        months[key]['payments'].append(entry)

    result = [months[m] for m in sorted(months.keys())]
    return jsonify({'year': year, 'months': result})


def _parse_report_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), '%Y-%m-%d').date()
    except ValueError:
        return None


@payments_bp.route('/api/reports/income', methods=['GET'])
@login_required
def income_by_lessons_report():
    """Доход: уроки с отметкой «оплачен» (is_paid), дата начала в интервале; сумма — по стоимости на дату урока."""
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    d_from = _parse_report_date(request.args.get('date_from'))
    d_to = _parse_report_date(request.args.get('date_to'))
    if not d_from or not d_to:
        return jsonify({'error': 'Укажите даты интервала (date_from, date_to)'}), 400
    if d_to < d_from:
        return jsonify({'error': 'Конец периода не может быть раньше начала'}), 400

    lesson_type = TaskType.query.filter_by(name='Урок').first()
    if not lesson_type:
        return jsonify({
            'date_from': d_from.isoformat(),
            'date_to': d_to.isoformat(),
            'total_amount': 0.0,
            'lessons_count': 0,
            'students': [],
        })

    dt_from = datetime.combine(d_from, datetime.min.time())
    dt_to_exclusive = datetime.combine(d_to + timedelta(days=1), datetime.min.time())

    query = Task.query.filter(
        Task.task_type_id == lesson_type.id,
        Task.is_paid == True,
        Task.student_id.isnot(None),
        Task.start_date.isnot(None),
        Task.start_date >= dt_from,
        Task.start_date < dt_to_exclusive,
    )
    if user_has_role('teacher') and not user_has_role('admin', 'owner'):
        query = query.filter(Task.user_id == current_user.id)

    tasks = query.all()
    student_ids = {t.student_id for t in tasks if t.student_id}
    users_by_id = {u.id: u for u in User.query.filter(User.id.in_(student_ids)).all()} if student_ids else {}
    price_history_by_student = build_price_history_index(list(student_ids))

    by_student = {}
    total_amount = 0.0
    lessons_without_price = 0

    for t in tasks:
        sid = t.student_id
        user = users_by_id.get(sid)
        fallback = float(user.lesson_price) if user and user.lesson_price is not None else None
        history = price_history_by_student.get(sid, [])
        resolved = price_at_date(history, t.start_date, fallback=fallback)
        if resolved is None:
            price = 0.0
            lessons_without_price += 1
        else:
            price = float(resolved)

        if sid not in by_student:
            by_student[sid] = {
                'student_id': sid,
                'student_name': user.display_name if user else '—',
                'lessons_count': 0,
                'amount': 0.0,
            }
        by_student[sid]['lessons_count'] += 1
        by_student[sid]['amount'] += price
        total_amount += price

    students = sorted(by_student.values(), key=lambda x: (-x['amount'], x['student_name'] or ''))
    for row in students:
        row['amount'] = round(row['amount'], 2)

    return jsonify({
        'date_from': d_from.isoformat(),
        'date_to': d_to.isoformat(),
        'total_amount': round(total_amount, 2),
        'lessons_count': len(tasks),
        'lessons_without_price': lessons_without_price,
        'students': students,
    })


def _month_name(n):
    names = ['', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
             'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    return names[n] if 0 < n <= 12 else str(n)
