from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Task, User, TaskStatus, TaskType, Role, UserRole, Homework, PlanStep, HomeworkEvidence, LessonSeries, LessonHomework
from helpers import parse_datetime, user_has_role
import os
import asyncio
import re
import json
import time
from datetime import datetime, timedelta
from sqlalchemy import or_
import calendar
from uuid import uuid4

tasks_bp = Blueprint('tasks', __name__)


def _agent_debug_log(hypothesis_id, location, message, data):
    # region agent log
    _p = '/Users/aleksejbalastov/My Pet Projects/MiSpring/.cursor/debug-e062f9.log'
    try:
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
    homework_ids упорядочены по справочнику ДЗ, привязанному к плану ученика.
    """
    from models import HomeworkCatalog

    template, steps, up = _get_student_plan_template_and_steps(student_id)
    if not template:
        return None, None, up, 'plan_missing'
    if not steps:
        return None, None, up, 'plan_no_steps'

    step_ids = [s.id for s in steps]

    # Берем только тот справочник, который явно привязан к плану ученика.
    catalog = HomeworkCatalog.query.filter_by(plan_template_id=template.id).first()
    if not catalog:
        return [], step_ids, up, 'plan_catalog_missing'

    items = Homework.query.filter_by(catalog_id=catalog.id).order_by(Homework.id.asc()).all()
    hw_ids = [hw.id for hw in items]
    if not hw_ids:
        return [], step_ids, up, 'plan_catalog_homework_empty'
    return hw_ids, step_ids, up, None


def _find_next_homework_id(student_id, from_homework_id=None):
    """
    Возвращает (homework_id, reason) или (None, reason).
    Логика основана на плане 2-го уровня ученика и справочнике ДЗ, привязанном к этому плану.
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
            if getattr(t, 'homework_unique', False):
                continue
            seq = _task_homework_ids(t.id) or ([t.homework_id] if t.homework_id else [])
            seq = [int(x) for x in seq if x and int(x) in ordered_hw_ids]
            if not seq:
                continue
            last_hw = seq[-1]
            next_hw_id, next_reason = _next_after_homework_id(last_hw)
            if next_reason == 'next_after_from':
                return next_hw_id, 'next_after_last_conducted'
            return None, next_reason

    if up and up.next_step_id and step_ids and up.next_step_id in step_ids:
        for hw_id in ordered_hw_ids:
            hw = db.session.get(Homework, hw_id)
            if hw and hw.plan_step_id == up.next_step_id:
                return hw.id, 'from_userplan_next_step'
    return ordered_hw_ids[0], 'from_first_homework_in_plan'


def _normalize_homework_ids(payload):
    if payload is None:
        return None
    if not isinstance(payload, list):
        return []
    result = []
    for v in payload:
        try:
            hv = int(v)
        except Exception:
            continue
        if hv > 0 and hv not in result:
            result.append(hv)
    return result


def _task_homework_rows(task_id):
    return LessonHomework.query.filter_by(task_id=task_id).order_by(
        LessonHomework.order_index.asc(),
        LessonHomework.id.asc(),
    ).all()


def _task_homework_ids(task_id):
    return [r.homework_id for r in _task_homework_rows(task_id)]


def _set_task_homeworks(task, homework_ids):
    # Keep legacy single-homework fields in sync.
    cleaned = [int(h) for h in (homework_ids or []) if h]
    LessonHomework.query.filter_by(task_id=task.id).delete()
    if not cleaned:
        task.homework_id = None
        task.homework_required = False
        return
    due = (task.start_date + timedelta(days=14)) if task.start_date else (datetime.now() + timedelta(days=14))
    for idx, hw_id in enumerate(cleaned):
        db.session.add(LessonHomework(
            task_id=task.id,
            homework_id=hw_id,
            order_index=idx,
            due_date=due,
            status_id=task.status_id,
            submitted_at=task.homework_submitted_at,
            teacher_remarks=task.homework_teacher_remarks,
        ))
    task.homework_id = cleaned[0]
    task.homework_required = True


def _task_status_terminal(st):
    """Проведён / Отменён (или группы done/cancelled)."""
    if not st:
        return False
    name = st.name or ''
    group = (st.group or '').lower() if st.group else ''
    return name in ('Проведён', 'Отменён') or group in ('done', 'cancelled')


def _recalculate_future_homework_for_student(student_id):
    """
    Назначает ДЗ по цепочке справочника на все будущие уроки ученика (тип «Урок»),
    независимо от серии. Проведённые и отменённые уроки не меняются и задают якорь для цепочки.
    Возвращает число обновлённых задач.
    """
    if not student_id:
        return 0
    lesson_type = TaskType.query.filter_by(name='Урок').first()
    if not lesson_type:
        return 0

    ordered_hw_ids, _step_ids, _up, _reason = _get_ordered_plan_homework_ids(student_id)
    if ordered_hw_ids is None:
        return 0
    catalog_set = set(ordered_hw_ids) if ordered_hw_ids else set()

    now = datetime.now()
    tasks = Task.query.filter_by(
        student_id=student_id,
        task_type_id=lesson_type.id,
    ).filter(
        Task.start_date.isnot(None),
    ).order_by(Task.start_date.asc(), Task.id.asc()).all()

    if not tasks:
        return 0

    status_ids = {t.status_id for t in tasks if t.status_id}
    status_map = {}
    if status_ids:
        status_map = {s.id: s for s in TaskStatus.query.filter(TaskStatus.id.in_(status_ids)).all()}

    lh_rows = LessonHomework.query.join(Task, Task.id == LessonHomework.task_id).filter(
        Task.student_id == student_id,
        Task.task_type_id == lesson_type.id,
    ).order_by(LessonHomework.order_index.asc(), LessonHomework.id.asc()).all()
    hw_by_task = {}
    for r in lh_rows:
        hw_by_task.setdefault(r.task_id, []).append(r)

    chain_prev = None
    updated = 0

    for t in tasks:
        st = status_map.get(t.status_id) if t.status_id else None
        terminal = _task_status_terminal(st)
        is_future = t.start_date >= now

        if not is_future or terminal:
            if not getattr(t, 'homework_unique', False):
                if terminal and st and st.name == 'Проведён':
                    chain = [r.homework_id for r in hw_by_task.get(t.id, []) if r.homework_id in catalog_set]
                    if chain:
                        chain_prev = int(chain[-1])
                    elif t.homework_id and int(t.homework_id) in catalog_set:
                        chain_prev = int(t.homework_id)
                elif not terminal and t.start_date and t.start_date < now:
                    chain = [r.homework_id for r in hw_by_task.get(t.id, []) if r.homework_id in catalog_set]
                    if chain:
                        chain_prev = int(chain[-1])
                    elif t.homework_required and t.homework_id and int(t.homework_id) in catalog_set:
                        chain_prev = int(t.homework_id)
            continue

        if getattr(t, 'homework_unique', False):
            t.homework_required = True
            changed = False
            if t.homework_id is not None:
                t.homework_id = None
                changed = True
            if hw_by_task.get(t.id):
                LessonHomework.query.filter_by(task_id=t.id).delete()
                changed = True
            if changed:
                updated += 1
            continue

        if not catalog_set:
            if t.homework_id is not None or t.homework_required:
                t.homework_id = None
                t.homework_required = False
                if t.series_id:
                    t.series_exception = False
                updated += 1
            continue

        if t.homework_required:
            existing_count = max(1, len(hw_by_task.get(t.id, [])))
            assigned = []
            prev = chain_prev
            for _i in range(existing_count):
                if prev is not None:
                    nh, _reason = _find_next_homework_id(student_id, from_homework_id=prev)
                else:
                    nh, _reason = _find_next_homework_id(student_id, None)
                if nh is None:
                    break
                assigned.append(int(nh))
                prev = int(nh)
            if not assigned:
                t.homework_id = None
                t.homework_required = False
                LessonHomework.query.filter_by(task_id=t.id).delete()
            else:
                _set_task_homeworks(t, assigned)
                chain_prev = assigned[-1]
            if t.series_id:
                t.series_exception = False
            updated += 1
        else:
            if t.homework_id is not None or t.homework_required:
                t.homework_id = None
                t.homework_required = False
                LessonHomework.query.filter_by(task_id=t.id).delete()
                if t.series_id:
                    t.series_exception = False
                updated += 1

    if updated:
        db.session.commit()
    return updated


def _normalize_recurrence_rule(raw):
    value = (raw or '').strip().upper()
    allowed = {'WEEKLY', 'BIWEEKLY', 'MONTHLY'}
    return value if value in allowed else None


def _parse_repeat_until(raw_value):
    """
    Поддерживает yyyy-mm-dd (как конец дня) и yyyy-mm-ddTHH:MM.
    """
    if not raw_value:
        return None
    value = str(raw_value).strip()
    if len(value) == 10:
        try:
            return datetime.strptime(value, '%Y-%m-%d').replace(hour=23, minute=59)
        except ValueError:
            return None
    return parse_datetime(value)


def _validate_repeat_until_limit(repeat_until):
    if not repeat_until:
        return None
    max_allowed_date = (datetime.now() + timedelta(days=365)).date()
    if repeat_until.date() > max_allowed_date:
        return 'Дата окончания серии должна быть не позже, чем через год от текущей даты'
    return None


def _add_months(dt, months):
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _next_series_date(dt, recurrence_rule):
    rule = _normalize_recurrence_rule(recurrence_rule) or 'WEEKLY'
    if rule == 'BIWEEKLY':
        return dt + timedelta(weeks=2)
    if rule == 'MONTHLY':
        return _add_months(dt, 1)
    return dt + timedelta(weeks=1)


def _build_series_starts(start_date, repeat_until, recurrence_rule, max_points=260):
    if not start_date or not repeat_until:
        return []
    result = []
    current = start_date
    for _ in range(max_points):
        if current > repeat_until:
            break
        result.append(current)
        current = _next_series_date(current, recurrence_rule)
    return result


def _clean_html_for_telegram(html):
    """Удаляет атрибуты, неподдерживаемые Telegram HTML-парсером (target, rel и др.)"""
    html = re.sub(r'\s+target=["\'][^"\']*["\']', '', html)
    html = re.sub(r'\s+rel=["\'][^"\']*["\']', '', html)
    html = html.replace('&nbsp;', ' ')
    return html


def _send_homework_notification_for_task(student, task):
    """Отправляет ученику ДЗ после проведённого урока: из справочника или уникальный текст."""
    if not student.telegram_id or not student.telegram_notifications:
        return
    date_str = task.start_date.strftime('%d.%m') if task.start_date else ''
    body = None
    if getattr(task, 'homework_unique', False) and (task.homework_custom_text or '').strip():
        body = _clean_html_for_telegram(task.homework_custom_text)
    else:
        if not task.homework_id:
            return
        homework = db.session.get(Homework, task.homework_id)
        if not homework or not homework.comment:
            return
        body = _clean_html_for_telegram(homework.comment)
    if not body:
        return
    try:
        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not token:
            return

        text = f'📚 Домашнее задание к уроку {date_str}:\n\n{body}'

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
    _agent_debug_log('DBG-TABLE-1', 'routes_tasks.get_tasks', 'request_params', {
        'page': page,
        'student_id': request.args.get('student_id'),
        'task_type_id': request.args.get('task_type_id'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to'),
        'is_paid': request.args.get('is_paid'),
        'user_id': getattr(current_user, 'id', None),
    })

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

    task_ids = [t.id for t in paginator.items]
    lesson_homeworks = LessonHomework.query.filter(LessonHomework.task_id.in_(task_ids)).order_by(
        LessonHomework.task_id.asc(), LessonHomework.order_index.asc(), LessonHomework.id.asc()
    ).all() if task_ids else []
    homework_ids_by_task = {}
    for lh in lesson_homeworks:
        homework_ids_by_task.setdefault(lh.task_id, []).append(lh.homework_id)

    tasks = []
    for t in paginator.items:
        d = t.to_dict()
        d['status_name'] = status_map.get(t.status_id)
        d['student_name'] = student_map.get(t.student_id)
        d['task_type_name'] = type_map.get(t.task_type_id)
        if getattr(t, 'homework_unique', False):
            d['homework_name'] = 'Уникальное ДЗ'
        else:
            d['homework_name'] = homework_map.get(t.homework_id)
        d['homework_ids'] = homework_ids_by_task.get(t.id, ([t.homework_id] if t.homework_id else []))
        tasks.append(d)

    _agent_debug_log('DBG-TABLE-1', 'routes_tasks.get_tasks', 'response_meta', {
        'page': page,
        'returned_count': len(tasks),
        'returned_ids': [t.get('id') for t in tasks[:15]],
        'total': paginator.total,
        'pages': paginator.pages,
        'current_page': paginator.page,
    })

    return jsonify({
        'tasks': tasks,
        'total': paginator.total,
        'pages': paginator.pages,
        'current_page': paginator.page,
        'next_id': next_id,
    })


@tasks_bp.route('/api/tasks/<int:task_id>/homeworks', methods=['GET'])
@login_required
def get_task_homeworks(task_id):
    task = db.get_or_404(Task, task_id)
    if not user_has_role('admin', 'owner') and task.user_id != current_user.id and task.student_id != current_user.id:
        return jsonify({'error': 'Недостаточно прав'}), 403
    if getattr(task, 'homework_unique', False):
        return jsonify({'homework_ids': []})
    rows = _task_homework_rows(task.id)
    ids = [r.homework_id for r in rows]
    if not ids and task.homework_id:
        ids = [task.homework_id]
    return jsonify({'homework_ids': ids})


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

    homework_unique = bool(data.get('homework_unique', False))
    homework_custom_text = (data.get('homework_custom_text') or '').strip() or None
    if homework_custom_text and len(homework_custom_text) > 20000:
        return jsonify({'error': 'Текст уникального ДЗ: не более 20000 символов'}), 400

    homework_required = bool(data.get('homework_required', True))
    homework_ids = _normalize_homework_ids(data.get('homework_ids'))
    if homework_ids is None:
        homework_ids = []
    homework_id = data.get('homework_id')
    if not homework_ids and homework_id:
        try:
            homework_ids = [int(homework_id)]
        except (TypeError, ValueError):
            homework_ids = []

    lesson_type_chk = TaskType.query.filter_by(name='Урок').first()
    is_lesson_create = lesson_type_chk and int(data.get('task_type_id') or 0) == lesson_type_chk.id

    if homework_unique:
        homework_required = True
        homework_ids = []
        if is_lesson_create and not homework_custom_text:
            return jsonify({'error': 'Для уникального ДЗ укажите текст задания'}), 400
    else:
        homework_custom_text = None
        if homework_required and not homework_ids and data.get('student_id'):
            next_hw_id, _reason = _find_next_homework_id(data.get('student_id'))
            if next_hw_id:
                homework_ids = [int(next_hw_id)]

        # Если это урок и ДЗ обязательно, но подобрать/выбрать не получилось — требуем вручную
        if homework_required and not homework_ids and data.get('task_type_id'):
            lesson_type = TaskType.query.filter_by(name='Урок').first()
            if lesson_type and int(data.get('task_type_id') or 0) == lesson_type.id:
                return jsonify({'error': 'Не удалось подобрать следующее ДЗ автоматически — выберите ДЗ вручную'}), 400

    if homework_ids:
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
        homework_id=(homework_ids[0] if homework_ids else None),
        homework_required=homework_required,
        status_id=status_id,
        task_type_id=data.get('task_type_id'),
        duration=data.get('duration'),
        comment=comment,
        closing_date=parse_datetime(data.get('closing_date')),
        plan_step_id=data.get('plan_step_id'),
        homework_unique=homework_unique,
        homework_custom_text=homework_custom_text if homework_unique else None,
    )
    db.session.add(task)
    db.session.flush()
    if homework_unique:
        LessonHomework.query.filter_by(task_id=task.id).delete()
        task.homework_id = None
        task.homework_required = True
    elif homework_required and homework_ids:
        _set_task_homeworks(task, homework_ids)
    db.session.commit()
    lesson_type_row = TaskType.query.filter_by(name='Урок').first()
    if task.student_id and lesson_type_row and task.task_type_id == lesson_type_row.id:
        _recalculate_future_homework_for_student(task.student_id)
        student_obj = db.session.get(User, task.student_id)
        if student_obj:
            from routes_payments import sync_prepaid_marks
            sync_prepaid_marks(student_obj)
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
    homework_ids = _normalize_homework_ids(data.get('homework_ids'))
    if homework_ids is None:
        homework_ids = []
    if not homework_ids and homework_id:
        try:
            homework_ids = [int(homework_id)]
        except (TypeError, ValueError):
            homework_ids = []
    comment = (data.get('comment') or '').strip() or None
    recurrence_rule = _normalize_recurrence_rule(data.get('recurrence_rule')) or 'WEEKLY'
    repeat_until_raw = data.get('repeat_until') or data.get('end_date')

    if not student_id:
        return jsonify({'error': 'Укажите ученика'}), 400
    if not task_type_id:
        return jsonify({'error': 'Укажите тип задачи'}), 400
    start_date = parse_datetime(start_date_raw)
    if not start_date:
        return jsonify({'error': 'Некорректная дата начала'}), 400
    repeat_until = _parse_repeat_until(repeat_until_raw)
    if not repeat_until:
        return jsonify({'error': 'Укажите дату окончания серии'}), 400
    if repeat_until < start_date:
        return jsonify({'error': 'Дата окончания серии должна быть не раньше даты начала'}), 400
    limit_error = _validate_repeat_until_limit(repeat_until)
    if limit_error:
        return jsonify({'error': limit_error}), 400
    if not duration or int(duration) <= 0:
        return jsonify({'error': 'Некорректная продолжительность'}), 400
    duration = int(duration)

    if homework_required and not homework_ids:
        next_hw, _reason = _find_next_homework_id(student_id)
        if next_hw:
            homework_ids = [int(next_hw)]
    if homework_required and not homework_ids:
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
    if homework_ids:
        first_homework = db.session.get(Homework, homework_ids[0])
        if not first_homework:
            return jsonify({'error': 'Домашнее задание не найдено'}), 400

    try:
        starts = _build_series_starts(start_date, repeat_until, recurrence_rule)
        if not starts:
            return jsonify({'error': 'Не удалось построить серию по заданным параметрам'}), 400

        series = LessonSeries(
            student_id=student_id,
            teacher_id=current_user.id,
            task_type_id=task_type_id,
            start_date=start_date,
            end_date=starts[-1],
            recurrence_rule=recurrence_rule,
            occurrences_count=len(starts),
            first_homework_id=(homework_ids[0] if homework_required and homework_ids else None),
            homework_required_default=homework_required,
        )
        db.session.add(series)
        db.session.flush()  # get series.id

        in_progress = None
        if homework_required and homework_ids:
            in_progress = TaskStatus.query.filter_by(name='В работе').first()
            if not in_progress:
                in_progress = TaskStatus.query.filter_by(group='in_progress').order_by(TaskStatus.id).first()

        status_id_first = data.get('status_id')
        if homework_ids and in_progress:
            status_id_first = in_progress.id

        plan_step_id_first = None
        ps_raw = data.get('plan_step_id')
        if ps_raw not in (None, ''):
            try:
                plan_step_id_first = int(ps_raw)
            except (TypeError, ValueError):
                plan_step_id_first = None

        for idx, dt_start in enumerate(starts):
            dt_end = dt_start + timedelta(minutes=duration)
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
                homework_id=((homework_ids[0] if homework_ids else None) if (idx == 0 and homework_required) else None),
                homework_required=homework_required if idx == 0 else homework_required,
                status_id=status_id_first if idx == 0 else None,
                task_type_id=task_type_id,
                duration=duration,
                comment=comment if idx == 0 else None,
                plan_step_id=plan_step_id_first if idx == 0 else None,
                series_id=series.id,
                series_index=idx,
                series_exception=False,
            )
            db.session.add(task)
            db.session.flush()
            if idx == 0 and homework_required and homework_ids:
                _set_task_homeworks(task, homework_ids)

        db.session.commit()
        _recalculate_future_homework_for_student(student_id)

        from routes_payments import sync_prepaid_marks
        sync_prepaid_marks(student)

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
    repeat_until_raw = data.get('repeat_until') or data.get('end_date')
    if not repeat_until_raw:
        return jsonify({'error': 'Не указана дата окончания серии'}), 400
    repeat_until = _parse_repeat_until(repeat_until_raw)
    if not repeat_until:
        return jsonify({'error': 'Некорректная дата окончания серии'}), 400

    if not series.start_date:
        return jsonify({'error': 'Серия не содержит даты начала'}), 400
    if repeat_until < series.start_date:
        return jsonify({'error': 'Дата окончания серии должна быть не раньше даты начала'}), 400
    limit_error = _validate_repeat_until_limit(repeat_until)
    if limit_error:
        return jsonify({'error': limit_error}), 400
    new_rule = _normalize_recurrence_rule(data.get('recurrence_rule')) or _normalize_recurrence_rule(series.recurrence_rule) or 'WEEKLY'

    try:
        desired_starts = _build_series_starts(series.start_date, repeat_until, new_rule)
        if not desired_starts:
            return jsonify({'error': 'Не удалось построить серию по заданным параметрам'}), 400

        existing_tasks = Task.query.filter_by(series_id=series.id).order_by(
            Task.start_date.asc(), Task.series_index.asc(), Task.id.asc()
        ).all()
        if not existing_tasks:
            return jsonify({'error': 'Не найдены уроки этой серии'}), 400

        # Берём первый урок серии как шаблон для добавляемых уроков
        template_task = existing_tasks[0]
        duration = template_task.duration or 60
        is_paid = template_task.is_paid
        payment_date = template_task.payment_date

        desired_keys = {dt.strftime('%Y-%m-%dT%H:%M') for dt in desired_starts}
        existing_by_key = {}
        for t in existing_tasks:
            if t.start_date:
                existing_by_key[t.start_date.strftime('%Y-%m-%dT%H:%M')] = t

        # Добавляем недостающие уроки серии по новой дате окончания
        for dt_start in desired_starts:
            key = dt_start.strftime('%Y-%m-%dT%H:%M')
            if key in existing_by_key:
                continue
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
                series_exception=False,
            )
            db.session.add(task)

        # Удаляем лишние уроки за пределами новой даты (если не проведены/не отменены)
        removable = []
        status_ids = {t.status_id for t in existing_tasks if t.status_id}
        status_map = {}
        if status_ids:
            statuses = TaskStatus.query.filter(TaskStatus.id.in_(status_ids)).all()
            status_map = {s.id: s for s in statuses}
        for t in existing_tasks:
            key = t.start_date.strftime('%Y-%m-%dT%H:%M') if t.start_date else None
            if key in desired_keys:
                continue
            st = status_map.get(t.status_id) if t.status_id else None
            st_name = st.name if st else None
            st_group = (st.group or '').lower() if st and st.group else ''
            if st_name in ('Проведён', 'Отменён') or st_group in ('done', 'cancelled'):
                continue
            removable.append(t)
        for t in removable:
            db.session.delete(t)

        # Обновляем индексы/границы серии
        db.session.flush()
        refreshed = Task.query.filter_by(series_id=series.id).order_by(
            Task.start_date.asc(), Task.id.asc()
        ).all()
        for idx, t in enumerate(refreshed):
            t.series_index = idx
        series.occurrences_count = len(refreshed)
        series.end_date = desired_starts[-1]
        series.recurrence_rule = new_rule

        db.session.commit()
        _recalculate_future_homework_for_student(series.student_id)

        student_obj = db.session.get(User, series.student_id)
        if student_obj:
            from routes_payments import sync_prepaid_marks
            sync_prepaid_marks(student_obj)

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

    updated = _recalculate_future_homework_for_student(task.student_id)
    return jsonify({'updated': updated, 'missing': 0})


@tasks_bp.route('/api/lesson-series/<int:series_id>', methods=['DELETE'])
@login_required
def delete_lesson_series(series_id):
    series = db.get_or_404(LessonSeries, series_id)
    if not user_has_role('admin', 'owner') and not (user_has_role('teacher') and series.teacher_id == current_user.id):
        return jsonify({'error': 'Недостаточно прав'}), 403

    student_id_for_recalc = series.student_id

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
    _recalculate_future_homework_for_student(student_id_for_recalc)
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
        old_homework_ids = _task_homework_ids(task.id)
        old_homework_required = task.homework_required
        old_homework_unique = bool(getattr(task, 'homework_unique', False))
        old_homework_custom_text = (getattr(task, 'homework_custom_text', None) or '').strip() or None
        old_student_id = task.student_id
        old_task_type_id = task.task_type_id
        old_status_id = task.status_id

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
        if 'homework_unique' in data:
            task.homework_unique = bool(data['homework_unique'])
            if not task.homework_unique:
                task.homework_custom_text = None
        if 'homework_custom_text' in data:
            if getattr(task, 'homework_unique', False):
                ct = (data.get('homework_custom_text') or '').strip() or None
                if ct and len(ct) > 20000:
                    return jsonify({'error': 'Текст уникального ДЗ: не более 20000 символов'}), 400
                task.homework_custom_text = ct
        if not getattr(task, 'homework_unique', False):
            if 'homework_ids' in data:
                incoming_ids = _normalize_homework_ids(data.get('homework_ids')) or []
                if incoming_ids:
                    _set_task_homeworks(task, incoming_ids)
                    if 'status_id' not in data:
                        in_progress = TaskStatus.query.filter_by(name='В работе').first()
                        if not in_progress:
                            in_progress = TaskStatus.query.filter_by(group='in_progress').order_by(TaskStatus.id).first()
                        if in_progress:
                            task.status_id = in_progress.id
                else:
                    LessonHomework.query.filter_by(task_id=task.id).delete()
                    task.homework_id = None
            elif 'homework_id' in data:
                task.homework_id = data['homework_id']
                if data['homework_id']:
                    _set_task_homeworks(task, [int(data['homework_id'])])
                else:
                    LessonHomework.query.filter_by(task_id=task.id).delete()
                if data['homework_id'] and 'status_id' not in data:
                    in_progress = TaskStatus.query.filter_by(name='В работе').first()
                    if not in_progress:
                        in_progress = TaskStatus.query.filter_by(group='in_progress').order_by(TaskStatus.id).first()
                    if in_progress:
                        task.status_id = in_progress.id
        if 'homework_required' in data and not getattr(task, 'homework_unique', False):
            task.homework_required = bool(data['homework_required'])
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

        recurrence_rule = _normalize_recurrence_rule(data.get('recurrence_rule'))
        repeat_until = _parse_repeat_until(data.get('repeat_until')) if ('repeat_until' in data or recurrence_rule) else None
        lesson_type_for_recurrence = TaskType.query.filter_by(name='Урок').first()
        if recurrence_rule and not task.series_id:
            if not lesson_type_for_recurrence or task.task_type_id != lesson_type_for_recurrence.id:
                return jsonify({'error': 'Повтор можно включить только для типа задачи "Урок"'}), 400
            if not task.start_date:
                return jsonify({'error': 'Для создания серии укажите дату начала урока'}), 400
            if not repeat_until:
                return jsonify({'error': 'Укажите дату окончания серии'}), 400
            if repeat_until < task.start_date:
                return jsonify({'error': 'Дата окончания серии должна быть не раньше даты начала'}), 400
            limit_error = _validate_repeat_until_limit(repeat_until)
            if limit_error:
                return jsonify({'error': limit_error}), 400

            starts = _build_series_starts(task.start_date, repeat_until, recurrence_rule)
            if not starts:
                return jsonify({'error': 'Не удалось построить серию по заданным параметрам'}), 400

            new_series = LessonSeries(
                student_id=task.student_id,
                teacher_id=task.user_id or current_user.id,
                task_type_id=task.task_type_id,
                start_date=task.start_date,
                end_date=starts[-1],
                recurrence_rule=recurrence_rule,
                occurrences_count=len(starts),
                first_homework_id=(
                    task.homework_id if (task.homework_required and not getattr(task, 'homework_unique', False)) else None
                ),
                homework_required_default=bool(task.homework_required),
            )
            db.session.add(new_series)
            db.session.flush()

            task.series_id = new_series.id
            task.series_index = 0
            task.series_exception = False
            if task.duration:
                task.end_date = task.start_date + timedelta(minutes=task.duration)

            current_hw_id = task.homework_id if task.homework_required else None
            for idx, dt_start in enumerate(starts):
                if idx == 0:
                    continue
                if task.homework_required and current_hw_id:
                    next_hw_id, _reason = _find_next_homework_id(task.student_id, from_homework_id=current_hw_id)
                    current_hw_id = next_hw_id
                dt_end = dt_start + timedelta(minutes=(task.duration or 60))
                new_task = Task(
                    description=task.description or '',
                    created_at=datetime.now(),
                    start_date=dt_start,
                    end_date=dt_end,
                    author=task.author,
                    user_id=task.user_id,
                    student_id=task.student_id,
                    is_paid=task.is_paid,
                    payment_date=task.payment_date,
                    homework_id=current_hw_id if task.homework_required else None,
                    homework_required=task.homework_required if (task.homework_required and current_hw_id) else False,
                    status_id=None,
                    task_type_id=task.task_type_id,
                    duration=task.duration,
                    comment=None,
                    closing_date=None,
                    plan_step_id=None,
                    series_id=new_series.id,
                    series_index=idx,
                    series_exception=False,
                )
                db.session.add(new_task)
                db.session.flush()
                src_ids = _task_homework_ids(task.id)
                if task.homework_required and src_ids:
                    assigned_ids = []
                    prev = current_hw_id
                    for _ in range(len(src_ids)):
                        nh, _r = _find_next_homework_id(task.student_id, from_homework_id=prev) if prev else _find_next_homework_id(task.student_id, None)
                        if not nh:
                            break
                        assigned_ids.append(int(nh))
                        prev = int(nh)
                    if assigned_ids:
                        _set_task_homeworks(new_task, assigned_ids)

        # Помечаем урок серии как исключение при изменении ДЗ/флага
        if task.series_id:
            new_homework_ids = _task_homework_ids(task.id)
            new_ct = (getattr(task, 'homework_custom_text', None) or '').strip() or None
            homework_changed = (
                ('homework_id' in data and data.get('homework_id') != old_homework_id)
                or ('homework_ids' in data and new_homework_ids != old_homework_ids)
                or ('homework_unique' in data and bool(data.get('homework_unique')) != old_homework_unique)
                or ('homework_custom_text' in data and new_ct != old_homework_custom_text)
            )
            required_changed = ('homework_required' in data and bool(data.get('homework_required')) != bool(old_homework_required))
            if homework_changed or required_changed:
                task.series_exception = True

        if getattr(task, 'homework_unique', False):
            task.homework_required = True
            LessonHomework.query.filter_by(task_id=task.id).delete()
            task.homework_id = None

        lesson_row_validate = TaskType.query.filter_by(name='Урок').first()
        if (
            getattr(task, 'homework_unique', False)
            and lesson_row_validate
            and task.task_type_id == lesson_row_validate.id
            and not (task.homework_custom_text or '').strip()
        ):
            return jsonify({'error': 'Укажите текст уникального ДЗ'}), 400

        db.session.commit()

        # Проверяем, стал ли статус "Проведён"
        new_status_id = task.status_id
        if new_status_id and new_status_id != old_status_id:
            cancelled_statuses = TaskStatus.query.filter(
                (TaskStatus.name == 'Отменён') | (TaskStatus.group == 'cancelled')
            ).all()
            cancelled_status_ids = {s.id for s in cancelled_statuses}
            conducted_status = TaskStatus.query.filter_by(name='Проведён').first()
            lesson_type = TaskType.query.filter_by(name='Урок').first()

            # Отмена урока (одиночного или в серии): пересчёт ДЗ на все будущие уроки ученика
            if (lesson_type and task.task_type_id == lesson_type.id
                    and new_status_id in cancelled_status_ids and task.student_id):
                _recalculate_future_homework_for_student(task.student_id)

                # Пересчитать разметку предоплаты (баланс восстановится автоматически)
                from routes_payments import sync_prepaid_marks
                student = db.session.get(User, task.student_id)
                if student:
                    sync_prepaid_marks(student)

            if (conducted_status and conducted_status.id == new_status_id
                    and lesson_type and task.task_type_id == lesson_type.id
                    and task.student_id):
                student = db.session.get(User, task.student_id)
                if student:
                    # Пересчитать разметку предоплаты (баланс, is_paid на будущих)
                    from routes_payments import sync_prepaid_marks
                    sync_prepaid_marks(student)
                    if (student.prepaid_lessons or 0) == 1:
                        _send_prepay_warning(student)

                    # Отправляем домашнее задание ученику
                    _send_homework_notification_for_task(student, task)

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

        lesson_type_row = TaskType.query.filter_by(name='Урок').first()
        if lesson_type_row:
            if (
                'homework_required' in data
                and not bool(data.get('homework_required'))
                and old_homework_required
                and task.task_type_id == lesson_type_row.id
                and task.student_id
            ):
                _recalculate_future_homework_for_student(task.student_id)

            conducted_row = TaskStatus.query.filter_by(name='Проведён').first()
            if (
                conducted_row
                and new_status_id
                and old_status_id != new_status_id
                and conducted_row.id == new_status_id
                and task.task_type_id == lesson_type_row.id
                and task.student_id
            ):
                _recalculate_future_homework_for_student(task.student_id)

            if 'student_id' in data and old_student_id != task.student_id:
                if old_task_type_id == lesson_type_row.id and old_student_id:
                    _recalculate_future_homework_for_student(old_student_id)
                if task.task_type_id == lesson_type_row.id and task.student_id:
                    _recalculate_future_homework_for_student(task.student_id)

            if recurrence_rule and task.task_type_id == lesson_type_row.id and task.student_id:
                _recalculate_future_homework_for_student(task.student_id)

            if (
                task.task_type_id == lesson_type_row.id
                and task.student_id
                and 'homework_unique' in data
                and bool(data.get('homework_unique')) != old_homework_unique
            ):
                _recalculate_future_homework_for_student(task.student_id)

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

    data = request.get_json(force=True, silent=True) or {}
    mode = data.get('mode')  # None | 'only_this' | 'this_and_future'

    sid = task.student_id
    tt_id = task.task_type_id
    series_id = task.series_id

    if mode == 'this_and_future' and series_id:
        cancelled_names = {'Проведён', 'Отменён'}
        cancelled_groups = {'done', 'cancelled'}
        tasks_in_series = Task.query.filter_by(series_id=series_id).all()
        status_ids = {t.status_id for t in tasks_in_series if t.status_id}
        status_map = {}
        if status_ids:
            status_map = {s.id: s for s in TaskStatus.query.filter(TaskStatus.id.in_(status_ids)).all()}

        removed = 0
        for t in tasks_in_series:
            if t.start_date and task.start_date and t.start_date < task.start_date:
                continue
            st = status_map.get(t.status_id) if t.status_id else None
            name = st.name if st else None
            group = (st.group or '').lower() if st and st.group else ''
            if name in cancelled_names or group in cancelled_groups:
                continue
            db.session.delete(t)
            removed += 1

        remaining = Task.query.filter_by(series_id=series_id).count()
        if remaining == 0:
            series_obj = db.session.get(LessonSeries, series_id)
            if series_obj:
                db.session.delete(series_obj)

        db.session.commit()
        lesson_type_row = TaskType.query.filter_by(name='Урок').first()
        if sid and lesson_type_row and tt_id == lesson_type_row.id:
            _recalculate_future_homework_for_student(sid)
            student_obj = db.session.get(User, sid)
            if student_obj:
                from routes_payments import sync_prepaid_marks
                sync_prepaid_marks(student_obj)
        return jsonify({'deleted_tasks': removed})

    db.session.delete(task)
    db.session.commit()
    lesson_type_row = TaskType.query.filter_by(name='Урок').first()
    if sid and lesson_type_row and tt_id == lesson_type_row.id:
        _recalculate_future_homework_for_student(sid)
        student_obj = db.session.get(User, sid)
        if student_obj:
            from routes_payments import sync_prepaid_marks
            sync_prepaid_marks(student_obj)
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
    task_ids = [t.id for t in tasks]
    lh_rows = LessonHomework.query.filter(LessonHomework.task_id.in_(task_ids)).order_by(
        LessonHomework.task_id.asc(), LessonHomework.order_index.asc(), LessonHomework.id.asc()
    ).all() if task_ids else []
    hw_ids_map = {}
    for r in lh_rows:
        hw_ids_map.setdefault(r.task_id, []).append(r.homework_id)
    for t in tasks:
        student_name = student_map.get(t.student_id, '')
        type_name = type_map.get(t.task_type_id, '')
        status_name = status_map.get(t.status_id, '')
        title_parts = [p for p in [student_name, type_name] if p]
        title = ' — '.join(title_parts) or f'Задача #{t.id}'
        if status_name:
            title += f' [{status_name}]'
        props = t.to_dict()
        props['homework_ids'] = hw_ids_map.get(t.id, ([t.homework_id] if t.homework_id else []))
        events.append({
            'id': t.id,
            'title': title,
            'start': t.start_date.strftime('%Y-%m-%dT%H:%M') if t.start_date else None,
            'end': t.end_date.strftime('%Y-%m-%dT%H:%M') if t.end_date else None,
            'color': '#38a169' if t.is_paid else '#1A515F',
            'extendedProps': props,
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
        'is_paid': bool(task.is_paid),
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


@tasks_bp.route('/api/my-lessons-history', methods=['GET'])
@login_required
def get_my_lessons_history():
    offset = request.args.get('offset', type=int) or 0
    limit = request.args.get('limit', type=int) or 5
    flt = (request.args.get('filter') or 'all').strip().lower()
    offset = max(0, offset)
    limit = max(1, min(limit, 50))

    lesson_type = TaskType.query.filter_by(name='Урок').first()
    if not lesson_type:
        return jsonify({'lessons': [], 'has_more': False})

    now = datetime.now()
    q = db.session.query(Task, TaskStatus).outerjoin(TaskStatus, Task.status_id == TaskStatus.id).filter(
        Task.student_id == current_user.id,
        Task.task_type_id == lesson_type.id,
        Task.start_date.isnot(None),
        Task.start_date < now,
    )

    if flt == 'conducted':
        q = q.filter((TaskStatus.name == 'Проведён') | (TaskStatus.group == 'done'))
    elif flt == 'cancelled':
        q = q.filter((TaskStatus.name == 'Отменён') | (TaskStatus.group == 'cancelled'))

    rows = q.order_by(Task.start_date.desc()).offset(offset).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    tasks = [t for (t, _s) in rows]
    step_ids = {t.plan_step_id for t in tasks if t.plan_step_id}
    step_map = {}
    if step_ids:
        step_map = {s.id: s.title for s in PlanStep.query.filter(PlanStep.id.in_(step_ids)).all()}

    lessons = []
    # For homework names: only for conducted lessons that have homework_id.
    homework_ids = set()
    for (t, st) in rows:
        status_name = (st.name if st else None) or '—'
        status_group = st.group if st else None
        is_conducted = bool(status_name == 'Проведён' or status_group == 'done')
        if is_conducted and t.homework_id:
            homework_ids.add(t.homework_id)

    homework_map = {}
    if homework_ids:
        homework_map = {h.id: h.name for h in Homework.query.filter(Homework.id.in_(homework_ids)).all()}

    for (t, st) in rows:
        status_name = (st.name if st else None) or '—'
        status_group = st.group if st else None
        is_conducted = bool(status_name == 'Проведён' or status_group == 'done')
        if is_conducted and getattr(t, 'homework_unique', False):
            homework_name = 'Уникальное ДЗ'
        else:
            homework_name = homework_map.get(t.homework_id) if (is_conducted and t.homework_id) else None
        lessons.append({
            'id': t.id,
            'start_date_iso': t.start_date.strftime('%Y-%m-%dT%H:%M:%S') if t.start_date else None,
            'topic': step_map.get(t.plan_step_id) or '—',
            'status_name': status_name,
            'is_paid': bool(t.is_paid),
            'homework_name': homework_name,
        })

    return jsonify({'lessons': lessons, 'has_more': bool(has_more)})


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

    q = Task.query.filter(
        or_(
            Task.homework_id.isnot(None),
            Task.homework_unique.is_(True),
        ),
    )
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
        hw = homework_map.get(t.homework_id) if t.homework_id else None
        st = status_map.get(t.status_id)
        student = student_map.get(t.student_id)
        is_uq = bool(getattr(t, 'homework_unique', False))
        items.append({
            'task_id': t.id,
            'student_id': t.student_id,
            'student_name': student.display_name if student else '—',
            'homework_name': 'Уникальное ДЗ' if is_uq else (hw.name if hw else '—'),
            'homework_topic': None if is_uq else (step_map.get(hw.plan_step_id) if hw and hw.plan_step_id else None),
            'homework_comment': (t.homework_custom_text if is_uq else (hw.comment if hw else None)),
            'homework_unique': is_uq,
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
    """Returns lesson homeworks assigned to the current student."""
    from datetime import datetime
    show_done = request.args.get('show_done', '0') == '1'

    done_status = TaskStatus.query.filter(TaskStatus.group == 'done').all()
    done_ids = [s.id for s in done_status]

    q = Task.query.filter(
        Task.student_id == current_user.id,
        or_(
            Task.homework_id.isnot(None),
            Task.homework_unique.is_(True),
        ),
    )
    if not show_done and done_ids:
        q = q.filter(or_(Task.status_id.is_(None), ~Task.status_id.in_(done_ids)))

    tasks = q.order_by(Task.start_date.desc()).limit(50).all()
    task_ids = [t.id for t in tasks]
    lesson_homeworks = LessonHomework.query.filter(LessonHomework.task_id.in_(task_ids)).order_by(
        LessonHomework.task_id.desc(), LessonHomework.order_index.asc(), LessonHomework.id.asc()
    ).all() if task_ids else []
    by_task = {}
    for lh in lesson_homeworks:
        by_task.setdefault(lh.task_id, []).append(lh)

    homework_ids = {lh.homework_id for lh in lesson_homeworks if lh.homework_id}
    if not homework_ids:
        homework_ids = {t.homework_id for t in tasks if t.homework_id}
    status_ids = {t.status_id for t in tasks if t.status_id}
    step_ids = {t.plan_step_id for t in tasks if t.plan_step_id}
    homework_map = {hw.id: hw for hw in Homework.query.filter(Homework.id.in_(homework_ids)).all()} if homework_ids else {}
    status_map = {s.id: s for s in TaskStatus.query.filter(TaskStatus.id.in_(status_ids)).all()} if status_ids else {}
    step_map = {s.id: s.title for s in PlanStep.query.filter(PlanStep.id.in_(step_ids)).all()} if step_ids else {}

    now = datetime.now()
    result = []
    for t in tasks:
        st = status_map.get(t.status_id)
        is_overdue = bool(
            t.start_date and (t.start_date + timedelta(days=14)) < now and
            (not st or (st.group or '').lower() not in ('done', 'completed', 'готово'))
        )
        rows = by_task.get(t.id) or []
        if not rows and t.homework_id:
            rows = [type('X', (), {'id': None, 'homework_id': t.homework_id, 'due_date': (t.start_date + timedelta(days=14)) if t.start_date else None})()]
        elif not rows and getattr(t, 'homework_unique', False):
            rows = [type('X', (), {'id': None, 'homework_id': None, 'due_date': (t.start_date + timedelta(days=14)) if t.start_date else None})()]
        for lh in rows:
            hw = homework_map.get(lh.homework_id) if lh.homework_id else None
            due = lh.due_date or ((t.start_date + timedelta(days=14)) if t.start_date else None)
            is_uq = bool(getattr(t, 'homework_unique', False))
            result.append({
                'task_id': t.id,
                'lesson_homework_id': lh.id,
                'homework_name': 'Уникальное ДЗ' if is_uq else (hw.name if hw else None),
                'homework_comment': (t.homework_custom_text if is_uq else (hw.comment if hw else None)),
                'homework_unique': is_uq,
                'topic_title': step_map.get(t.plan_step_id) if t.plan_step_id else None,
                'status_name': st.name if st else None,
                'status_group': st.group if st else None,
                'lesson_date': t.start_date.strftime('%d.%m.%Y') if t.start_date else None,
                'lesson_date_iso': t.start_date.strftime('%Y-%m-%dT%H:%M') if t.start_date else None,
                'due_date': due.strftime('%d.%m.%Y') if due else None,
                'due_date_iso': due.strftime('%Y-%m-%dT%H:%M') if due else None,
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

