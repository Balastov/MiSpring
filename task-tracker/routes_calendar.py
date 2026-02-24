import secrets
from datetime import datetime, timezone, timedelta

from flask import Blueprint, jsonify, request, Response
from flask_login import login_required, current_user
from icalendar import Calendar, Event

from extensions import db
from models import User, Task, TaskType, TaskStatus, UserRole, Role

calendar_bp = Blueprint('calendar', __name__)


@calendar_bp.route('/api/user/calendar-token', methods=['GET'])
@login_required
def get_calendar_token():
    user = db.session.get(User, current_user.id)
    if not user.calendar_token:
        user.calendar_token = secrets.token_urlsafe(32)
        db.session.commit()
    base_url = request.host_url.rstrip('/')
    return jsonify({
        'token': user.calendar_token,
        'url': f'{base_url}/api/calendar/{user.calendar_token}.ics',
    })


@calendar_bp.route('/api/calendar/<token>.ics', methods=['GET'])
def get_ics_feed(token):
    user = User.query.filter_by(calendar_token=token).first()
    if not user:
        return Response('Not found', status=404)

    lesson_type = TaskType.query.filter_by(name='Урок').first()
    if not lesson_type:
        tasks = []
    else:
        tasks = Task.query.filter(
            Task.user_id == user.id,
            Task.task_type_id == lesson_type.id,
            Task.start_date.isnot(None),
        ).order_by(Task.start_date.desc()).limit(500).all()

    # Build lookup maps
    student_ids = {t.student_id for t in tasks if t.student_id}
    status_ids = {t.status_id for t in tasks if t.status_id}

    student_map = {}
    if student_ids:
        students = User.query.filter(User.id.in_(student_ids)).all()
        student_map = {s.id: s.display_name for s in students}

    status_map = {}
    if status_ids:
        statuses = TaskStatus.query.filter(TaskStatus.id.in_(status_ids)).all()
        status_map = {s.id: s.name for s in statuses}

    cal = Calendar()
    cal.add('prodid', '-//MiSpring//MiSpring//RU')
    cal.add('version', '2.0')
    cal.add('X-WR-CALNAME', f'Уроки — {user.display_name}')
    cal.add('X-WR-TIMEZONE', 'Europe/Moscow')
    cal.add('REFRESH-INTERVAL;VALUE=DURATION', 'PT3H')

    for task in tasks:
        ev = Event()
        ev.add('uid', f'task-{task.id}@mispring')

        student_name = student_map.get(task.student_id, 'Ученик')
        ev.add('summary', f'Урок: {student_name}')

        start = task.start_date
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        ev.add('dtstart', start)

        if task.end_date:
            end = task.end_date
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            ev.add('dtend', end)
        elif task.duration:
            ev.add('dtend', start + timedelta(minutes=task.duration))
        else:
            ev.add('dtend', start + timedelta(hours=1))

        ev.add('dtstamp', datetime.now(timezone.utc))

        desc_parts = []
        status_name = status_map.get(task.status_id)
        if status_name:
            desc_parts.append(f'Статус: {status_name}')
        if task.is_paid:
            desc_parts.append('Оплачено ✓')
        if task.comment:
            desc_parts.append(f'Комментарий: {task.comment}')
        if desc_parts:
            ev.add('description', '\n'.join(desc_parts))

        cal.add_component(ev)

    return Response(
        cal.to_ical(),
        mimetype='text/calendar; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename="mispring.ics"'},
    )
