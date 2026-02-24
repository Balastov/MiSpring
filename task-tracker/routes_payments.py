from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime
from extensions import db
from models import User, StudentPayment, Task, TaskStatus, TaskType
from helpers import user_has_role

payments_bp = Blueprint('payments', __name__)


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
    return {
        'total_paid': total_paid,
        'conducted': conducted_count,
        'remaining': remaining,
        'prepaid_since': student.prepaid_since.strftime('%d.%m.%Y') if student.prepaid_since else None,
        'prepaid_since_iso': student.prepaid_since.strftime('%Y-%m-%d') if student.prepaid_since else None,
        'lesson_price': student.lesson_price,
        'payments': [p.to_dict() for p in payments],
    }


@payments_bp.route('/api/students/<int:student_id>/balance', methods=['GET'])
@login_required
def get_balance(student_id):
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    student = db.get_or_404(User, student_id)
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

    return jsonify({'ok': True, 'balance': _get_balance(student)})


@payments_bp.route('/api/students/<int:student_id>/lesson-price', methods=['PUT'])
@login_required
def update_lesson_price(student_id):
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    student = db.get_or_404(User, student_id)
    data = request.get_json(force=True, silent=True) or {}

    price = data.get('lesson_price')
    if price is None or price == '':
        student.lesson_price = None
    else:
        try:
            student.lesson_price = float(price)
        except (ValueError, TypeError):
            return jsonify({'error': 'Некорректная цена'}), 400

    db.session.commit()
    return jsonify({'ok': True, 'lesson_price': student.lesson_price})


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


def _month_name(n):
    names = ['', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
             'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    return names[n] if 0 < n <= 12 else str(n)
