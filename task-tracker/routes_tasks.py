from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Task, User, TaskStatus, TaskType, Role, UserRole, Homework
from helpers import parse_datetime, user_has_role
import os
import asyncio
import re

tasks_bp = Blueprint('tasks', __name__)


def _clean_html_for_telegram(html):
    """Удаляет атрибуты, неподдерживаемые Telegram HTML-парсером (target, rel и др.)"""
    html = re.sub(r'\s+target=["\'][^"\']*["\']', '', html)
    html = re.sub(r'\s+rel=["\'][^"\']*["\']', '', html)
    html = html.replace('&nbsp;', ' ')
    return html


def _send_homework_notification(student, task, homework):
    """Отправляет ученику домашнее задание после проведённого урока."""
    if not homework.comment or not student.telegram_id or not student.telegram_notifications:
        return
    try:
        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not token:
            return

        date_str = task.start_date.strftime('%d.%m') if task.start_date else ''
        text = f'📚 Домашнее задание к уроку {date_str}:\n\n{_clean_html_for_telegram(homework.comment)}'

        import telegram

        async def _send():
            bot = telegram.Bot(token=token)
            await bot.send_message(chat_id=student.telegram_id, text=text, parse_mode='HTML')

        asyncio.run(_send())
    except Exception:
        pass


def _send_prepay_warning(student):
    """Отправляет учителю уведомление в Telegram, если у ученика остался 1 оплаченный урок."""
    try:
        # Находим пользователей с ролью teacher или owner, у которых есть telegram_id
        teacher_role = Role.query.filter(Role.name.in_(['teacher', 'owner', 'admin'])).all()
        role_ids = [r.id for r in teacher_role]
        if not role_ids:
            return
        from models import UserRole as UR
        teacher_user_ids = [ur.user_id for ur in UR.query.filter(UR.role_id.in_(role_ids)).all()]
        teachers = User.query.filter(
            User.id.in_(teacher_user_ids),
            User.telegram_id.isnot(None),
            User.telegram_notifications == True
        ).all()

        if not teachers:
            return

        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not token:
            return

        tg_username = f'@{student.telegram_username}' if student.telegram_username else ''
        text = (
            f'⚠️ Внимание! У ученика <b>{student.display_name}</b>'
            + (f' ({tg_username})' if tg_username else '')
            + f' остался <b>1 оплаченный урок</b>.'
        )

        import telegram

        async def _send():
            bot = telegram.Bot(token=token)
            for teacher in teachers:
                try:
                    await bot.send_message(chat_id=teacher.telegram_id, text=text, parse_mode='HTML')
                except Exception:
                    pass

        asyncio.run(_send())
    except Exception:
        pass


@tasks_bp.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    page = request.args.get('page', 1, type=int)
    per_page = 50

    query = db.select(Task).order_by(Task.created_at.desc())
    if not user_has_role('admin', 'owner'):
        if user_has_role('teacher', 'student'):
            query = query.where(Task.user_id == current_user.id)
        else:
            return jsonify({
                'tasks': [], 'total': 0, 'pages': 0, 'current_page': 1, 'next_id': 1,
            })

    # Filters
    student_id = request.args.get('student_id', type=int)
    if student_id:
        query = query.where(Task.student_id == student_id)

    task_type_id = request.args.get('task_type_id', type=int)
    if task_type_id:
        query = query.where(Task.task_type_id == task_type_id)

    date_from = request.args.get('date_from')
    if date_from:
        dt_from = parse_datetime(date_from)
        if dt_from:
            query = query.where(Task.start_date >= dt_from)

    date_to = request.args.get('date_to')
    if date_to:
        dt_to = parse_datetime(date_to)
        if dt_to:
            query = query.where(Task.start_date <= dt_to)

    is_paid = request.args.get('is_paid')
    if is_paid == '1':
        query = query.where(Task.is_paid == True)
    elif is_paid == '0':
        query = query.where(Task.is_paid == False)

    paginator = db.paginate(query, page=page, per_page=per_page, error_out=False)

    max_id_result = db.session.execute(db.select(db.func.max(Task.id))).scalar()
    next_id = (max_id_result or 0) + 1

    status_ids = {t.status_id for t in paginator.items if t.status_id}
    student_ids = {t.student_id for t in paginator.items if t.student_id}
    type_ids = {t.task_type_id for t in paginator.items if t.task_type_id}
    homework_ids = {t.homework_id for t in paginator.items if t.homework_id}
    status_map = {}
    student_map = {}
    type_map = {}
    homework_map = {}
    if status_ids:
        status_map = {s.id: s.name for s in TaskStatus.query.filter(TaskStatus.id.in_(status_ids)).all()}
    if student_ids:
        student_map = {u.id: u.display_name for u in User.query.filter(User.id.in_(student_ids)).all()}
    if type_ids:
        type_map = {tt.id: tt.name for tt in TaskType.query.filter(TaskType.id.in_(type_ids)).all()}
    if homework_ids:
        homework_map = {hw.id: hw.name for hw in Homework.query.filter(Homework.id.in_(homework_ids)).all()}

    tasks = []
    for t in paginator.items:
        d = t.to_dict()
        d['status_name'] = status_map.get(t.status_id)
        d['student_name'] = student_map.get(t.student_id)
        d['task_type_name'] = type_map.get(t.task_type_id)
        d['homework_name'] = homework_map.get(t.homework_id)
        tasks.append(d)

    return jsonify({
        'tasks': tasks,
        'total': paginator.total,
        'pages': paginator.pages,
        'current_page': paginator.page,
        'next_id': next_id,
    })


@tasks_bp.route('/api/tasks', methods=['POST'])
@login_required
def add_task():
    data = request.get_json()
    description = (data.get('description') or '').strip()
    if len(description) > 100:
        return jsonify({'error': 'Описание: не более 100 символов'}), 400

    comment = (data.get('comment') or '').strip() or None
    if comment and len(comment) > 500:
        return jsonify({'error': 'Комментарий: не более 500 символов'}), 400

    task = Task(
        description=description,
        start_date=parse_datetime(data.get('start_date')),
        end_date=parse_datetime(data.get('end_date')),
        author=current_user.display_name,
        user_id=current_user.id,
        student_id=data.get('student_id'),
        is_paid=bool(data.get('is_paid', False)),
        payment_date=parse_datetime(data.get('payment_date')),
        homework_id=data.get('homework_id'),
        homework_required=bool(data.get('homework_required', True)),
        status_id=data.get('status_id'),
        task_type_id=data.get('task_type_id'),
        duration=data.get('duration'),
        comment=comment,
        closing_date=parse_datetime(data.get('closing_date')),
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@tasks_bp.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    task = db.get_or_404(Task, task_id)

    if not user_has_role('admin', 'owner') and task.user_id != current_user.id:
        return jsonify({'error': 'Недостаточно прав'}), 403

    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'error': 'Нет данных'}), 400

    try:
        if 'description' in data:
            description = (data['description'] or '').strip()
            if len(description) > 100:
                return jsonify({'error': 'Описание: не более 100 символов'}), 400
            task.description = description
        if 'start_date' in data:
            task.start_date = parse_datetime(data['start_date'])
        if 'end_date' in data:
            task.end_date = parse_datetime(data['end_date'])
        if 'student_id' in data:
            task.student_id = data['student_id']
        if 'is_paid' in data:
            task.is_paid = bool(data['is_paid'])
        if 'payment_date' in data:
            task.payment_date = parse_datetime(data['payment_date'])
        if 'homework_id' in data:
            task.homework_id = data['homework_id']
        if 'homework_required' in data:
            task.homework_required = bool(data['homework_required'])
        old_status_id = task.status_id
        if 'status_id' in data:
            task.status_id = data['status_id']
        if 'task_type_id' in data:
            task.task_type_id = data['task_type_id']
        if 'duration' in data:
            task.duration = data['duration']
        if 'comment' in data:
            comment = (data['comment'] or '').strip() or None
            if comment and len(comment) > 500:
                return jsonify({'error': 'Комментарий: не более 500 символов'}), 400
            task.comment = comment
        if 'closing_date' in data:
            task.closing_date = parse_datetime(data['closing_date'])

        db.session.commit()

        # Проверяем, стал ли статус "Проведён"
        new_status_id = task.status_id
        if new_status_id and new_status_id != old_status_id:
            conducted_status = TaskStatus.query.filter_by(name='Проведён').first()
            lesson_type = TaskType.query.filter_by(name='Урок').first()
            if (conducted_status and conducted_status.id == new_status_id
                    and lesson_type and task.task_type_id == lesson_type.id
                    and task.student_id):
                student = db.session.get(User, task.student_id)
                if student:
                    # Уменьшаем баланс предоплаты
                    if ((student.prepaid_lessons or 0) > 0
                            and student.prepaid_since
                            and task.start_date and task.start_date >= student.prepaid_since):
                        student.prepaid_lessons -= 1
                        db.session.commit()
                        if student.prepaid_lessons == 1:
                            _send_prepay_warning(student)

                    # Отправляем домашнее задание ученику
                    if task.homework_id:
                        homework = db.session.get(Homework, task.homework_id)
                        if homework:
                            _send_homework_notification(student, task, homework)

        return jsonify(task.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    task = db.get_or_404(Task, task_id)

    if not user_has_role('admin', 'owner') and task.user_id != current_user.id:
        return jsonify({'error': 'Недостаточно прав'}), 403

    db.session.delete(task)
    db.session.commit()
    return '', 204


@tasks_bp.route('/api/students/<int:student_id>/last-homework', methods=['GET'])
@login_required
def get_last_homework_for_student(student_id):
    """Get the last homework assigned to a student in their most recent lesson task"""
    # Find "Урок" task type
    lesson_type = TaskType.query.filter_by(name='Урок').first()
    if not lesson_type:
        return jsonify({'homework_id': None})

    # Find the most recent task for this student with task_type "Урок" and homework assigned
    last_task = Task.query.filter_by(
        student_id=student_id,
        task_type_id=lesson_type.id
    ).filter(
        Task.homework_id.isnot(None)
    ).order_by(Task.start_date.desc()).first()

    if last_task and last_task.homework_id:
        return jsonify({'homework_id': last_task.homework_id})

    return jsonify({'homework_id': None})


# ========== Calendar Endpoint ==========

@tasks_bp.route('/api/tasks/calendar', methods=['GET'])
@login_required
def get_tasks_calendar():
    start = request.args.get('start')
    end = request.args.get('end')

    query = db.select(Task).where(Task.start_date.isnot(None))

    if not user_has_role('admin', 'owner'):
        if user_has_role('teacher', 'student'):
            query = query.where(Task.user_id == current_user.id)
        else:
            return jsonify([])

    if start:
        dt_start = parse_datetime(start[:16]) if len(start) > 16 else parse_datetime(start)
        if dt_start:
            query = query.where(Task.start_date >= dt_start)
    if end:
        dt_end = parse_datetime(end[:16]) if len(end) > 16 else parse_datetime(end)
        if dt_end:
            query = query.where(Task.start_date <= dt_end)

    tasks = db.session.execute(query).scalars().all()

    student_ids = {t.student_id for t in tasks if t.student_id}
    type_ids = {t.task_type_id for t in tasks if t.task_type_id}
    status_ids = {t.status_id for t in tasks if t.status_id}
    student_map = {}
    type_map = {}
    status_map = {}
    if student_ids:
        student_map = {u.id: u.display_name for u in User.query.filter(User.id.in_(student_ids)).all()}
    if type_ids:
        type_map = {tt.id: tt.name for tt in TaskType.query.filter(TaskType.id.in_(type_ids)).all()}
    if status_ids:
        status_map = {s.id: s.name for s in TaskStatus.query.filter(TaskStatus.id.in_(status_ids)).all()}

    events = []
    for t in tasks:
        student_name = student_map.get(t.student_id, '')
        type_name = type_map.get(t.task_type_id, '')
        status_name = status_map.get(t.status_id, '')
        title_parts = [p for p in [student_name, type_name] if p]
        title = ' — '.join(title_parts) or f'Задача #{t.id}'
        if status_name:
            title += f' [{status_name}]'
        events.append({
            'id': t.id,
            'title': title,
            'start': t.start_date.strftime('%Y-%m-%dT%H:%M') if t.start_date else None,
            'end': t.end_date.strftime('%Y-%m-%dT%H:%M') if t.end_date else None,
            'color': '#38a169' if t.is_paid else '#1A515F',
            'extendedProps': t.to_dict(),
        })

    return jsonify(events)


# ========== Students Endpoint ==========

@tasks_bp.route('/api/students/all', methods=['GET'])
@login_required
def get_all_students():
    """Return users with role 'student' for task form dropdown."""
    student_role = Role.query.filter_by(name='student').first()
    if not student_role:
        return jsonify({'students': []})
    student_user_ids = [ur.user_id for ur in UserRole.query.filter_by(role_id=student_role.id).all()]
    if not student_user_ids:
        return jsonify({'students': []})
    students = User.query.filter(
        User.id.in_(student_user_ids),
        User.is_active == True
    ).order_by(User.display_name).all()
    return jsonify({
        'students': [{'id': u.id, 'display_name': u.display_name} for u in students]
    })
