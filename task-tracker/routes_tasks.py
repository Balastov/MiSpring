from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Task, User, TaskStatus, TaskType, Role, UserRole, Homework, PlanStep, HomeworkEvidence, LessonSeries
from helpers import parse_datetime, user_has_role
import os
import asyncio
import re
import json
import time
from datetime import datetime
from uuid import uuid4

tasks_bp = Blueprint('tasks', __name__)


def _agent_debug_log(hypothesis_id, location, message, data):
    # region agent log
    _p = '/Users/aleksejbalastov/My Pet Projects/MiSpring/.cursor/debug-e062f9.log'
    try:
        os.makedirs(os.path.dirname(_p), exist_ok=True)
        with open(_p, 'a', encoding='utf-8') as _f:
            _f.write(json.dumps({
                'sessionId': 'e062f9',
                'hypothesisId': hypothesis_id,
                'location': location,
                'message': message,
                'data': data,
                'timestamp': int(time.time() * 1000),
            }, ensure_ascii=False) + '\n')
    except Exception:
        pass
    # endregion
HOMEWORK_FILES_TOTAL_LIMIT = 5 * 1024 * 1024
ALLOWED_HOMEWORK_FILE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.webp', '.gif',
    '.pdf', '.doc', '.docx', '.txt', '.zip', '.rar',
}


def _get_student_plan_template_and_steps(student_id):
    from models import UserPlan, PlanTemplate, PlanStep

    up = UserPlan.query.filter_by(student_id=student_id).first()
    if not up:
        return None, [], None
    template = db.session.get(PlanTemplate, up.template_id) if up.template_id else None
    if not template or template.parent_id is None:
        return None, [], up
    steps = PlanStep.query.filter_by(template_id=template.id).order_by(PlanStep.order_num, PlanStep.id).all()
    return template, steps, up


def _get_ordered_plan_homework_ids(student_id):
    """
    Возвращает (homework_ids, step_ids, up, reason_if_empty_or_none).
    homework_ids упорядочены по шагам плана (order_num), затем по Homework.id.
    """
    template, steps, up = _get_student_plan_template_and_steps(student_id)
    if not template:
        return None, None, up, 'plan_missing'
    if not steps:
        return None, None, up, 'plan_no_steps'

    step_ids = [s.id for s in steps]
    step_index = {sid: idx for idx, sid in enumerate(step_ids)}
    items = Homework.query.filter(Homework.plan_step_id.in_(step_ids)).all()
    items.sort(key=lambda hw: (step_index.get(hw.plan_step_id, 10**9), hw.id))
    hw_ids = [hw.id for hw in items]
    if not hw_ids:
        return [], step_ids, up, 'plan_homework_empty'
    return hw_ids, step_ids, up, None


def _find_next_homework_id(student_id, from_homework_id=None):
    """
    Возвращает (homework_id, reason) или (None, reason).
    Логика основана на плане 2-го уровня ученика и шагах плана.
    """
    ordered_hw_ids, step_ids, up, reason = _get_ordered_plan_homework_ids(student_id)
    if ordered_hw_ids is None:
        return None, reason
    if len(ordered_hw_ids) == 0:
        return None, reason

    def _next_after_homework_id(current_hw_id):
        try:
            idx = ordered_hw_ids.index(int(current_hw_id))
        except Exception:
            return None, 'from_homework_not_in_plan'
        if idx + 1 >= len(ordered_hw_ids):
            return None, 'end_of_plan'
        return ordered_hw_ids[idx + 1], 'next_after_from'

    if from_homework_id:
        return _next_after_homework_id(from_homework_id)

    lesson_type = TaskType.query.filter_by(name='Урок').first()
    conducted = TaskStatus.query.filter_by(name='Проведён').first()
    if lesson_type and conducted:
        q = Task.query.filter_by(
            student_id=student_id,
            task_type_id=lesson_type.id,
            status_id=conducted.id,
        ).order_by(Task.start_date.desc(), Task.id.desc()).all()
        for t in q:
            if not t.homework_id:
                continue
            if int(t.homework_id) not in ordered_hw_ids:
                continue
            next_hw_id, next_reason = _next_after_homework_id(t.homework_id)
            if next_reason == 'next_after_from':
                return next_hw_id, 'next_after_last_conducted'
            return None, next_reason

    if up and up.next_step_id and step_ids and up.next_step_id in step_ids:
        for hw_id in ordered_hw_ids:
            hw = db.session.get(Homework, hw_id)
            if hw and hw.plan_step_id == up.next_step_id:
                return hw.id, 'from_userplan_next_step'
    return ordered_hw_ids[0], 'from_first_homework_in_plan'


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


def _get_in_review_status():
    return TaskStatus.query.filter_by(name='На проверке').first()


def _can_teacher_access_task(task):
    if user_has_role('admin', 'owner'):
        return True
    return user_has_role('teacher') and task.user_id == current_user.id


def _serialize_evidence(files):
    return [f.to_dict() for f in files]


def _split_evidence_by_uploader(files):
    student_files = []
    teacher_files = []
    for f in files:
        item = f.to_dict()
        if (f.uploader_role or 'student') == 'teacher':
            teacher_files.append(item)
        else:
            student_files.append(item)
    return student_files, teacher_files


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

    status_id = data.get('status_id')

    homework_required = bool(data.get('homework_required', True))
    homework_id = data.get('homework_id')
    if homework_required and not homework_id and data.get('student_id'):
        next_hw_id, _reason = _find_next_homework_id(data.get('student_id'))
        homework_id = next_hw_id

    # Если это урок и ДЗ обязательно, но подобрать/выбрать не получилось — требуем вручную
    if homework_required and not homework_id and data.get('task_type_id'):
        lesson_type = TaskType.query.filter_by(name='Урок').first()
        if lesson_type and int(data.get('task_type_id') or 0) == lesson_type.id:
            return jsonify({'error': 'Не удалось подобрать следующее ДЗ автоматически — выберите ДЗ вручную'}), 400

    if homework_id:
        in_progress = TaskStatus.query.filter_by(name='В работе').first()
        if not in_progress:
            in_progress = TaskStatus.query.filter_by(group='in_progress').order_by(TaskStatus.id).first()
        if in_progress:
            status_id = in_progress.id

    task = Task(
        description=description,
        start_date=parse_datetime(data.get('start_date')),
        end_date=parse_datetime(data.get('end_date')),
        author=current_user.display_name,
        user_id=current_user.id,
        student_id=data.get('student_id'),
        is_paid=bool(data.get('is_paid', False)),
        payment_date=parse_datetime(data.get('payment_date')),
        homework_id=homework_id,
        homework_required=homework_required,
        status_id=status_id,
        task_type_id=data.get('task_type_id'),
        duration=data.get('duration'),
        comment=comment,
        closing_date=parse_datetime(data.get('closing_date')),
        plan_step_id=data.get('plan_step_id'),
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@tasks_bp.route('/api/lesson-series', methods=['POST'])
@login_required
def create_lesson_series():
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    data = request.get_json(force=True, silent=True) or {}
    student_id = data.get('student_id')
    task_type_id = data.get('task_type_id')
    start_date_raw = data.get('start_date')
    duration = data.get('duration')
    is_paid = bool(data.get('is_paid', False))
    payment_date_raw = data.get('payment_date')
    homework_id = data.get('homework_id')
    homework_required = bool(data.get('homework_required', True))
    comment = (data.get('comment') or '').strip() or None
    series_count = data.get('occurrences_count') or data.get('series_count') or 10

    try:
        series_count = int(series_count)
    except (TypeError, ValueError):
        series_count = 10
    series_count = max(1, min(series_count, 52))

    if not student_id:
        return jsonify({'error': 'Укажите ученика'}), 400
    if not task_type_id:
        return jsonify({'error': 'Укажите тип задачи'}), 400
    start_date = parse_datetime(start_date_raw)
    if not start_date:
        return jsonify({'error': 'Некорректная дата начала'}), 400
    if not duration or int(duration) <= 0:
        return jsonify({'error': 'Некорректная продолжительность'}), 400
    duration = int(duration)

    if homework_required and not homework_id:
        homework_id, _reason = _find_next_homework_id(student_id)
    if homework_required and not homework_id:
        return jsonify({'error': 'Не удалось подобрать ДЗ первого урока автоматически — выберите ДЗ вручную или снимите флаг "ДЗ обязательно"'}), 400

    if comment and len(comment) > 500:
        return jsonify({'error': 'Комментарий: не более 500 символов'}), 400

    payment_date = parse_datetime(payment_date_raw) if payment_date_raw else None

    # Validate foreign keys
    student = db.session.get(User, student_id)
    if not student:
        return jsonify({'error': 'Ученик не найден'}), 400
    task_type = db.session.get(TaskType, task_type_id)
    if not task_type:
        return jsonify({'error': 'Тип задачи не найден'}), 400
    first_homework = None
    if homework_id:
        first_homework = db.session.get(Homework, homework_id)
        if not first_homework:
            return jsonify({'error': 'Домашнее задание не найдено'}), 400

    try:
        from datetime import timedelta

        series = LessonSeries(
            student_id=student_id,
            teacher_id=current_user.id,
            task_type_id=task_type_id,
            start_date=start_date,
            end_date=None,
            recurrence_rule='WEEKLY',
            occurrences_count=series_count,
            first_homework_id=homework_id if homework_required else None,
            homework_required_default=homework_required,
        )
        db.session.add(series)
        db.session.flush()  # get series.id

        end_date_first = start_date + timedelta(minutes=duration)

        in_progress = None
        if homework_required and homework_id:
            in_progress = TaskStatus.query.filter_by(name='В работе').first()
            if not in_progress:
                in_progress = TaskStatus.query.filter_by(group='in_progress').order_by(TaskStatus.id).first()

        current_hw_id = homework_id if homework_required else None
        for idx in range(series_count):
            dt_start = start_date + timedelta(weeks=idx)
            dt_end = dt_start + timedelta(minutes=duration)
            if idx > 0 and homework_required and current_hw_id:
                next_hw_id, _reason = _find_next_homework_id(student_id, from_homework_id=current_hw_id)
                current_hw_id = next_hw_id
            task = Task(
                description='',
                created_at=start_date if idx == 0 else datetime.now(),
                start_date=dt_start,
                end_date=dt_end,
                author=current_user.display_name,
                user_id=current_user.id,
                student_id=student_id,
                is_paid=is_paid,
                payment_date=payment_date,
                homework_id=current_hw_id if homework_required else None,
                homework_required=homework_required if (homework_required and current_hw_id) else False,
                status_id=in_progress.id if (idx == 0 and in_progress) else None,
                task_type_id=task_type_id,
                duration=duration,
                comment=comment if idx == 0 else None,
                plan_step_id=None,
                series_id=series.id,
                series_index=idx,
                series_exception=False,
            )
            db.session.add(task)

        # Update series end_date to the last lesson end
        if series_count > 0:
            series.end_date = end_date_first + timedelta(weeks=series_count - 1)

        db.session.commit()
        return jsonify({'series': series.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/api/lesson-series/<int:series_id>', methods=['GET'])
@login_required
def get_lesson_series(series_id):
    series = db.get_or_404(LessonSeries, series_id)
    if not user_has_role('admin', 'owner') and not (user_has_role('teacher') and series.teacher_id == current_user.id):
        return jsonify({'error': 'Недостаточно прав'}), 403

    # Для удобства UI вернём немного дополнительной информации
    student = db.session.get(User, series.student_id)
    teacher = db.session.get(User, series.teacher_id)
    task_type = db.session.get(TaskType, series.task_type_id)
    data = series.to_dict()
    data.update({
        'student_name': student.display_name if student else None,
        'teacher_name': teacher.display_name if teacher else None,
        'task_type_name': task_type.name if task_type else None,
    })
    return jsonify({'series': data})


@tasks_bp.route('/api/lesson-series/<int:series_id>', methods=['PUT'])
@login_required
def update_lesson_series(series_id):
    series = db.get_or_404(LessonSeries, series_id)
    if not user_has_role('admin', 'owner') and not (user_has_role('teacher') and series.teacher_id == current_user.id):
        return jsonify({'error': 'Недостаточно прав'}), 403

    data = request.get_json(force=True, silent=True) or {}
    new_count = data.get('occurrences_count') or data.get('series_count')
    if new_count is None:
        return jsonify({'error': 'Не указано новое количество уроков в серии'}), 400
    try:
        new_count = int(new_count)
    except (TypeError, ValueError):
        return jsonify({'error': 'Некорректное количество уроков в серии'}), 400
    if new_count < (series.occurrences_count or 0):
        return jsonify({'error': 'Сокращение длины серии пока не поддерживается'}), 400
    new_count = max(1, min(new_count, 52))

    if not series.start_date:
        return jsonify({'error': 'Серия не содержит даты начала'}), 400

    try:
        from datetime import timedelta

        current_count = series.occurrences_count or 0
        if new_count > current_count:
            # Берём первый урок серии как шаблон для новых
            template_task = Task.query.filter_by(series_id=series.id).order_by(Task.series_index.asc()).first()
            if not template_task:
                return jsonify({'error': 'Не найдены уроки этой серии'}), 400

            duration = template_task.duration or 60
            is_paid = template_task.is_paid
            payment_date = template_task.payment_date

            for idx in range(current_count, new_count):
                dt_start = series.start_date + timedelta(weeks=idx)
                dt_end = dt_start + timedelta(minutes=duration)
                task = Task(
                    description=template_task.description or '',
                    created_at=datetime.now(),
                    start_date=dt_start,
                    end_date=dt_end,
                    author=template_task.author,
                    user_id=template_task.user_id,
                    student_id=template_task.student_id,
                    is_paid=is_paid,
                    payment_date=payment_date,
                    homework_id=None,
                    homework_required=False,
                    status_id=None,
                    task_type_id=series.task_type_id,
                    duration=duration,
                    comment=None,
                    plan_step_id=None,
                    series_id=series.id,
                    series_index=idx,
                    series_exception=False,
                )
                db.session.add(task)

            # Обновляем конец серии и occurrences_count
            series.occurrences_count = new_count
            series.end_date = series.start_date + timedelta(weeks=new_count - 1, minutes=duration)

        db.session.commit()
        return jsonify({'series': series.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/api/lesson-series/<int:series_id>/recalculate-homework-from/<int:task_id>', methods=['POST'])
@login_required
def recalc_series_homework_from(series_id, task_id):
    series = db.get_or_404(LessonSeries, series_id)
    if not user_has_role('admin', 'owner') and not (user_has_role('teacher') and series.teacher_id == current_user.id):
        return jsonify({'error': 'Недостаточно прав'}), 403

    task = db.get_or_404(Task, task_id)
    if task.series_id != series.id:
        return jsonify({'error': 'Урок не принадлежит указанной серии'}), 400

    source_hw_id = task.homework_id
    source_required = bool(task.homework_required)

    # На всякий случай: если у исходного урока нет ДЗ и флаг снят,
    # то следующие тоже должны стать "без ДЗ".
    tasks = Task.query.filter_by(series_id=series.id).order_by(Task.start_date.asc(), Task.series_index.asc(), Task.id.asc()).all()

    found = False
    updated = 0
    missing = 0
    prev_hw_id = source_hw_id
    for t in tasks:
        if not found:
            if t.id == task.id:
                found = True
            continue
        if t.series_exception:
            continue
        if not source_required:
            t.homework_id = None
            t.homework_required = False
            updated += 1
            continue

        next_hw_id, _reason = _find_next_homework_id(t.student_id, from_homework_id=prev_hw_id) if prev_hw_id else (None, 'no_prev')
        prev_hw_id = next_hw_id
        t.homework_id = next_hw_id
        t.homework_required = True
        updated += 1
        if not next_hw_id:
            missing += 1

    db.session.commit()
    return jsonify({'updated': updated, 'missing': missing})


@tasks_bp.route('/api/lesson-series/<int:series_id>', methods=['DELETE'])
@login_required
def delete_lesson_series(series_id):
    series = db.get_or_404(LessonSeries, series_id)
    if not user_has_role('admin', 'owner') and not (user_has_role('teacher') and series.teacher_id == current_user.id):
        return jsonify({'error': 'Недостаточно прав'}), 403

    # Удаляем только уроки, которые НЕ проведены и НЕ отменены
    tasks = Task.query.filter_by(series_id=series.id).all()
    status_ids = {t.status_id for t in tasks if t.status_id}
    status_map = {}
    if status_ids:
        statuses = TaskStatus.query.filter(TaskStatus.id.in_(status_ids)).all()
        status_map = {s.id: s for s in statuses}

    removed = 0
    for t in tasks:
        st = status_map.get(t.status_id) if t.status_id else None
        name = st.name if st else None
        group = (st.group or '').lower() if st and st.group else ''
        if name in ('Проведён', 'Отменён') or group in ('done', 'cancelled'):
            continue
        db.session.delete(t)
        removed += 1

    # Если не осталось ни одного урока серии — удалим и запись серии
    remaining = Task.query.filter_by(series_id=series.id).count()
    if remaining == 0:
        db.session.delete(series)

    db.session.commit()
    return jsonify({'deleted_tasks': removed})


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
        old_homework_id = task.homework_id
        old_homework_required = task.homework_required

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
            if data['homework_id'] and 'status_id' not in data:
                in_progress = TaskStatus.query.filter_by(name='В работе').first()
                if not in_progress:
                    in_progress = TaskStatus.query.filter_by(group='in_progress').order_by(TaskStatus.id).first()
                if in_progress:
                    task.status_id = in_progress.id
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
        if 'plan_step_id' in data:
            task.plan_step_id = data['plan_step_id']

        # Помечаем урок серии как исключение при изменении ДЗ/флага
        if task.series_id:
            homework_changed = ('homework_id' in data and data.get('homework_id') != old_homework_id)
            required_changed = ('homework_required' in data and bool(data.get('homework_required')) != bool(old_homework_required))
            if homework_changed or required_changed:
                task.series_exception = True

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

                    # Обновляем следующий шаг плана (ответ из диалога)
                    if 'advance_plan_step' in data and task.plan_step_id:
                        from models import UserPlan, PlanStep
                        user_plan = UserPlan.query.filter_by(student_id=task.student_id).first()
                        if user_plan:
                            current_step = db.session.get(PlanStep, task.plan_step_id)
                            if current_step:
                                if data['advance_plan_step']:
                                    next_step = PlanStep.query.filter_by(
                                        template_id=current_step.template_id
                                    ).filter(
                                        PlanStep.order_num > current_step.order_num
                                    ).order_by(PlanStep.order_num).first()
                                    user_plan.next_step_id = next_step.id if next_step else current_step.id
                                else:
                                    user_plan.next_step_id = current_step.id
                                db.session.commit()

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


@tasks_bp.route('/api/students/<int:student_id>/next-homework', methods=['GET'])
@login_required
def get_next_homework_for_student(student_id):
    # Teachers/admins can view any; students can view their own
    if not user_has_role('admin', 'owner', 'teacher') and current_user.id != student_id:
        return jsonify({'error': 'Недостаточно прав'}), 403
    from_hw = request.args.get('from_homework_id', type=int)
    hw_id, reason = _find_next_homework_id(student_id, from_homework_id=from_hw)
    return jsonify({'homework_id': hw_id, 'reason': reason})


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


@tasks_bp.route('/api/my-next-lesson', methods=['GET'])
@login_required
def get_my_next_lesson():
    from sqlalchemy import or_
    lesson_type = TaskType.query.filter_by(name='Урок').first()
    if not lesson_type:
        return jsonify({'lesson': None})
    excluded = TaskStatus.query.filter(TaskStatus.name.in_(['Отменён', 'Проведён'])).all()
    excluded_ids = [s.id for s in excluded]
    now = datetime.now()
    q = Task.query.filter(
        Task.student_id == current_user.id,
        Task.task_type_id == lesson_type.id,
        Task.start_date > now,
        or_(Task.status_id.is_(None), ~Task.status_id.in_(excluded_ids))
    ).order_by(Task.start_date.asc())
    task = q.first()
    if not task:
        return jsonify({'lesson': None})
    plan_step_title = None
    if task.plan_step_id:
        from models import PlanStep
        step = db.session.get(PlanStep, task.plan_step_id)
        if step:
            plan_step_title = step.title
    return jsonify({'lesson': {
        'start_date_iso': task.start_date.strftime('%Y-%m-%dT%H:%M:%S'),
        'start_date': task.start_date.strftime('%d.%m.%Y %H:%M') if task.start_date else None,
        'plan_step_title': plan_step_title,
    }})


@tasks_bp.route('/api/my-lessons-month', methods=['GET'])
@login_required
def get_my_lessons_month():
    from sqlalchemy import or_
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    if not year or not month or month < 1 or month > 12:
        return jsonify({'error': 'Некорректные параметры year/month'}), 400

    # Month boundaries
    month_start = datetime(year, month, 1)
    if month == 12:
        month_end = datetime(year + 1, 1, 1)
    else:
        month_end = datetime(year, month + 1, 1)

    lesson_type = TaskType.query.filter_by(name='Урок').first()
    if not lesson_type:
        return jsonify({'lessons': []})

    cancelled = TaskStatus.query.filter(TaskStatus.name == 'Отменён').all()
    cancelled_ids = [s.id for s in cancelled]

    q = Task.query.filter(
        Task.student_id == current_user.id,
        Task.task_type_id == lesson_type.id,
        Task.start_date.isnot(None),
        Task.start_date >= month_start,
        Task.start_date < month_end,
    )
    if cancelled_ids:
        q = q.filter(or_(Task.status_id.is_(None), ~Task.status_id.in_(cancelled_ids)))

    tasks = q.order_by(Task.start_date.asc()).all()
    step_ids = {t.plan_step_id for t in tasks if t.plan_step_id}
    step_map = {}
    if step_ids:
        step_map = {s.id: s.title for s in PlanStep.query.filter(PlanStep.id.in_(step_ids)).all()}

    lessons = []
    for t in tasks:
        duration = t.duration
        if not duration and t.start_date and t.end_date:
            duration = max(1, int((t.end_date - t.start_date).total_seconds() // 60))
        lessons.append({
            'id': t.id,
            'date_iso': t.start_date.strftime('%Y-%m-%d') if t.start_date else None,
            'start_date_iso': t.start_date.strftime('%Y-%m-%dT%H:%M:%S') if t.start_date else None,
            'date': t.start_date.strftime('%d.%m.%Y') if t.start_date else None,
            'time': t.start_date.strftime('%H:%M') if t.start_date else None,
            'duration': duration,
            'topic': step_map.get(t.plan_step_id) or '—',
            'is_paid': bool(t.is_paid),
        })
    return jsonify({'lessons': lessons})


@tasks_bp.route('/api/tasks/<int:task_id>/evidence', methods=['GET'])
@login_required
def get_task_evidence(task_id):
    task = db.get_or_404(Task, task_id)
    if not (task.student_id == current_user.id or _can_teacher_access_task(task)):
        return jsonify({'error': 'Недостаточно прав'}), 403

    files = HomeworkEvidence.query.filter_by(task_id=task.id).order_by(HomeworkEvidence.created_at.desc()).all()
    student_files, teacher_files = _split_evidence_by_uploader(files)
    total_size = sum(f.size_bytes or 0 for f in files)
    student_total = sum(f.get('size_bytes') or 0 for f in student_files)
    teacher_total = sum(f.get('size_bytes') or 0 for f in teacher_files)
    return jsonify({
        'files': _serialize_evidence(files),
        'student_files': student_files,
        'teacher_files': teacher_files,
        'total_size_bytes': total_size,
        'student_total_size_bytes': student_total,
        'teacher_total_size_bytes': teacher_total,
        'limit_bytes': HOMEWORK_FILES_TOTAL_LIMIT,
    })


@tasks_bp.route('/api/tasks/<int:task_id>/evidence', methods=['POST'])
@login_required
def upload_task_evidence(task_id):
    task = db.get_or_404(Task, task_id)
    is_student_upload = task.student_id == current_user.id
    is_teacher_upload = _can_teacher_access_task(task)
    if not (is_student_upload or is_teacher_upload):
        return jsonify({'error': 'Недостаточно прав для загрузки файлов'}), 403
    uploader_role = 'student' if is_student_upload else 'teacher'

    incoming = request.files.getlist('files')
    if not incoming:
        single = request.files.get('file')
        if single:
            incoming = [single]
    if not incoming:
        return jsonify({'error': 'Файлы не найдены'}), 400

    existing = HomeworkEvidence.query.filter_by(task_id=task.id, uploader_role=uploader_role).all()
    existing_total = sum(f.size_bytes or 0 for f in existing)

    upload_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'homework_evidence')
    os.makedirs(upload_dir, exist_ok=True)

    uploaded_total = 0
    saved = []
    for item in incoming:
        data = item.read()
        size = len(data)
        if size == 0:
            continue
        ext = os.path.splitext(item.filename or '')[1].lower()
        if ext not in ALLOWED_HOMEWORK_FILE_EXTENSIONS:
            return jsonify({'error': f'Недопустимый формат файла: {ext or "без расширения"}'}), 400
        uploaded_total += size
        if existing_total + uploaded_total > HOMEWORK_FILES_TOTAL_LIMIT:
            return jsonify({'error': 'Превышен суммарный лимит 5 МБ на это задание'}), 400

        stored = f'{uuid4().hex}{ext}'
        relative_path = f'uploads/homework_evidence/{stored}'
        full_path = os.path.join(upload_dir, stored)
        with open(full_path, 'wb') as out:
            out.write(data)

        file_row = HomeworkEvidence(
            task_id=task.id,
            student_id=task.student_id or current_user.id,
            uploader_user_id=current_user.id,
            uploader_role=uploader_role,
            original_name=(item.filename or stored)[:255],
            stored_name=stored,
            relative_path=relative_path,
            mime_type=(item.mimetype or '')[:120] or None,
            size_bytes=size,
        )
        db.session.add(file_row)
        saved.append(file_row)

    if not saved:
        return jsonify({'error': 'Файлы пустые или не выбраны'}), 400
    db.session.commit()
    return jsonify({'files': _serialize_evidence(saved)}), 201


@tasks_bp.route('/api/tasks/<int:task_id>/evidence/<int:evidence_id>', methods=['DELETE'])
@login_required
def delete_task_evidence(task_id, evidence_id):
    task = db.get_or_404(Task, task_id)
    evidence = HomeworkEvidence.query.filter_by(id=evidence_id, task_id=task.id).first_or_404()

    is_student_own_file = (
        task.student_id == current_user.id and
        (evidence.uploader_role or 'student') == 'student' and
        (evidence.uploader_user_id or evidence.student_id) == current_user.id
    )
    is_teacher_allowed = _can_teacher_access_task(task)
    can_delete = (
        is_student_own_file or is_teacher_allowed
    )
    if not can_delete:
        return jsonify({'error': 'Недостаточно прав'}), 403

    file_path = os.path.join(os.path.dirname(__file__), 'static', evidence.relative_path.replace('/', os.sep))
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass
    db.session.delete(evidence)
    db.session.commit()
    return '', 204


@tasks_bp.route('/api/tasks/<int:task_id>/homework-submit', methods=['POST'])
@login_required
def submit_homework_for_review(task_id):
    task = db.get_or_404(Task, task_id)
    if task.student_id != current_user.id:
        return jsonify({'error': 'Недостаточно прав'}), 403

    files_count = HomeworkEvidence.query.filter_by(task_id=task.id, uploader_role='student').count()
    if files_count == 0:
        return jsonify({'error': 'Сначала загрузите хотя бы один файл'}), 400

    in_review = _get_in_review_status()
    if not in_review:
        return jsonify({'error': 'Статус "На проверке" не найден'}), 500

    task.status_id = in_review.id
    task.homework_submitted_at = datetime.now()
    db.session.commit()
    return jsonify(task.to_dict())


@tasks_bp.route('/api/tasks/<int:task_id>/homework-review', methods=['POST'])
@login_required
def review_homework(task_id):
    task = db.get_or_404(Task, task_id)
    if not _can_teacher_access_task(task):
        return jsonify({'error': 'Недостаточно прав'}), 403

    data = request.get_json(force=True, silent=True) or {}
    action = data.get('action')
    if action not in ('rework', 'approve'):
        return jsonify({'error': 'Неверное действие'}), 400

    old_status_id = task.status_id
    remarks = (data.get('remarks') or '').strip()
    if action == 'rework':
        if not remarks:
            return jsonify({'error': 'Укажите замечания при возврате на доработку'}), 400
        task.homework_teacher_remarks = remarks[:2000]
    else:
        task.homework_teacher_remarks = remarks[:2000] if remarks else None

    target_name = 'В работе' if action == 'rework' else 'Выполнено'
    target_status = TaskStatus.query.filter_by(name=target_name).first()
    if not target_status:
        target_group = 'in_progress' if action == 'rework' else 'done'
        target_status = TaskStatus.query.filter_by(group=target_group).order_by(TaskStatus.id).first()
    if not target_status:
        return jsonify({'error': f'Статус "{target_name}" не найден'}), 400

    _agent_debug_log('H1', 'routes_tasks.review_homework', 'before_commit', {
        'task_id': task.id,
        'action': action,
        'old_status_id': old_status_id,
        'target_status_id': target_status.id,
        'target_status_name': target_status.name,
        'target_status_group': target_status.group,
    })
    task.status_id = target_status.id
    db.session.commit()
    db.session.refresh(task)
    _agent_debug_log('H1', 'routes_tasks.review_homework', 'after_commit', {
        'task_id': task.id,
        'persisted_status_id': task.status_id,
        'remarks_len': len((task.homework_teacher_remarks or '')),
    })
    return jsonify(task.to_dict())


@tasks_bp.route('/api/homework-review', methods=['GET'])
@login_required
def get_homework_review_list():
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    q = Task.query.filter(Task.homework_id.isnot(None))
    if user_has_role('teacher') and not user_has_role('admin', 'owner'):
        q = q.filter(Task.user_id == current_user.id)

    student_id = request.args.get('student_id', type=int)
    if student_id:
        q = q.filter(Task.student_id == student_id)
    status_id = request.args.get('status_id', type=int)
    if status_id:
        q = q.filter(Task.status_id == status_id)
    only_with_files = request.args.get('with_files', '0') == '1'

    tasks = q.order_by(Task.start_date.desc()).limit(200).all()
    task_ids = [t.id for t in tasks]
    homework_ids = {t.homework_id for t in tasks if t.homework_id}
    student_ids = {t.student_id for t in tasks if t.student_id}
    status_ids = {t.status_id for t in tasks if t.status_id}

    homework_map = {h.id: h for h in Homework.query.filter(Homework.id.in_(homework_ids)).all()} if homework_ids else {}
    step_ids = {h.plan_step_id for h in homework_map.values() if h and h.plan_step_id}
    step_map = {s.id: s.title for s in PlanStep.query.filter(PlanStep.id.in_(step_ids)).all()} if step_ids else {}
    student_map = {u.id: u for u in User.query.filter(User.id.in_(student_ids)).all()} if student_ids else {}
    status_map = {s.id: s for s in TaskStatus.query.filter(TaskStatus.id.in_(status_ids)).all()} if status_ids else {}

    files = HomeworkEvidence.query.filter(HomeworkEvidence.task_id.in_(task_ids)).all() if task_ids else []
    files_count = {}
    files_last_at = {}
    student_files_by_task = {}
    teacher_files_by_task = {}
    for f in files:
        files_count[f.task_id] = files_count.get(f.task_id, 0) + 1
        file_item = {
            'id': f.id,
            'name': f.original_name,
            'url': f'/static/{f.relative_path}',
            'size_bytes': f.size_bytes,
            'uploader_role': f.uploader_role or 'student',
        }
        if (f.uploader_role or 'student') == 'teacher':
            teacher_files_by_task.setdefault(f.task_id, []).append(file_item)
        else:
            student_files_by_task.setdefault(f.task_id, []).append(file_item)
        if f.task_id not in files_last_at or ((f.created_at or datetime.min) > (files_last_at[f.task_id] or datetime.min)):
            files_last_at[f.task_id] = f.created_at

    items = []
    for t in tasks:
        count = files_count.get(t.id, 0)
        if only_with_files and count == 0:
            continue
        hw = homework_map.get(t.homework_id)
        st = status_map.get(t.status_id)
        student = student_map.get(t.student_id)
        items.append({
            'task_id': t.id,
            'student_id': t.student_id,
            'student_name': student.display_name if student else '—',
            'homework_name': hw.name if hw else '—',
            'homework_topic': step_map.get(hw.plan_step_id) if hw and hw.plan_step_id else None,
            'homework_comment': hw.comment if hw else None,
            'status_id': t.status_id,
            'status_name': st.name if st else None,
            'status_group': st.group if st else None,
            'lesson_date': t.start_date.strftime('%d.%m.%Y %H:%M') if t.start_date else None,
            'lesson_date_iso': t.start_date.strftime('%Y-%m-%dT%H:%M') if t.start_date else None,
            'files_count': count,
            'files': student_files_by_task.get(t.id, []),
            'student_files': student_files_by_task.get(t.id, []),
            'teacher_files': teacher_files_by_task.get(t.id, []),
            'last_upload_at': files_last_at[t.id].strftime('%d.%m.%Y %H:%M') if files_last_at.get(t.id) else None,
            'submitted_at': t.homework_submitted_at.strftime('%d.%m.%Y %H:%M') if t.homework_submitted_at else None,
            'homework_teacher_remarks': t.homework_teacher_remarks,
        })
    _sample = [{
        'task_id': x['task_id'],
        'status_id': x['status_id'],
        'status_name': x['status_name'],
        'status_group': x['status_group'],
        'has_remarks': bool(x.get('homework_teacher_remarks')),
    } for x in items[:10]]
    _agent_debug_log('H2', 'routes_tasks.get_homework_review_list', 'response_shape', {
        'query_status_filter': status_id,
        'n_items': len(items),
        'sample': _sample,
    })
    return jsonify({'items': items})


@tasks_bp.route('/api/my-homework', methods=['GET'])
@login_required
def get_my_homework():
    """Returns tasks with homework assigned to the current student."""
    from datetime import datetime
    from sqlalchemy import or_
    show_done = request.args.get('show_done', '0') == '1'

    done_status = TaskStatus.query.filter(TaskStatus.group == 'done').all()
    done_ids = [s.id for s in done_status]

    q = Task.query.filter(
        Task.student_id == current_user.id,
        Task.homework_id.isnot(None),
    )
    if not show_done and done_ids:
        q = q.filter(or_(Task.status_id.is_(None), ~Task.status_id.in_(done_ids)))

    tasks = q.order_by(Task.start_date.desc()).limit(20).all()

    homework_ids = {t.homework_id for t in tasks if t.homework_id}
    status_ids = {t.status_id for t in tasks if t.status_id}
    step_ids = {t.plan_step_id for t in tasks if t.plan_step_id}
    homework_map = {hw.id: hw for hw in Homework.query.filter(Homework.id.in_(homework_ids)).all()} if homework_ids else {}
    status_map = {s.id: s for s in TaskStatus.query.filter(TaskStatus.id.in_(status_ids)).all()} if status_ids else {}
    step_map = {s.id: s.title for s in PlanStep.query.filter(PlanStep.id.in_(step_ids)).all()} if step_ids else {}

    now = datetime.now()
    result = []
    for t in tasks:
        hw = homework_map.get(t.homework_id)
        st = status_map.get(t.status_id)
        is_overdue = bool(
            t.start_date and t.start_date < now and
            (not st or (st.group or '').lower() not in ('done', 'completed', 'готово'))
        )
        result.append({
            'task_id': t.id,
            'homework_name': hw.name if hw else None,
            'homework_comment': hw.comment if hw else None,
            'topic_title': step_map.get(t.plan_step_id) if t.plan_step_id else None,
            'status_name': st.name if st else None,
            'status_group': st.group if st else None,
            'lesson_date': t.start_date.strftime('%d.%m.%Y') if t.start_date else None,
            'lesson_date_iso': t.start_date.strftime('%Y-%m-%dT%H:%M') if t.start_date else None,
            'is_overdue': is_overdue,
            'homework_submitted_at': t.homework_submitted_at.strftime('%d.%m.%Y %H:%M') if t.homework_submitted_at else None,
            'homework_submitted_at_iso': t.homework_submitted_at.strftime('%Y-%m-%dT%H:%M') if t.homework_submitted_at else None,
            'homework_teacher_remarks': t.homework_teacher_remarks,
        })
    _rows = []
    for t in tasks[:8]:
        st = status_map.get(t.status_id)
        _rows.append({
            'task_id': t.id,
            'status_id': t.status_id,
            'status_name': st.name if st else None,
            'status_group': st.group if st else None,
            'has_remarks': bool(t.homework_teacher_remarks),
        })
    _agent_debug_log('H5', 'routes_tasks.get_my_homework', 'rows', {
        'student_id': current_user.id,
        'show_done': show_done,
        'rows': _rows,
    })
    return jsonify({'homework': result})

