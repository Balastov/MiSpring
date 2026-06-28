from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import PlanTemplate, PlanStep, UserPlan, Task, TaskStatus, TaskType, User, Role, UserRole
from helpers import user_has_role

plans_bp = Blueprint('plans', __name__)


def _annotate_plan_steps(template, next_step_id=None):
    """Статусы шагов плана: completed (изучено), current (текущая), upcoming (впереди)."""
    if not template:
        return []
    steps = sorted(template.steps, key=lambda s: (s.order_num, s.id))
    if not steps:
        return []

    next_order = None
    next_id = None
    if next_step_id:
        ns = db.session.get(PlanStep, next_step_id)
        if ns and ns.template_id == template.id:
            next_order = ns.order_num
            next_id = ns.id

    annotated = []
    for i, step in enumerate(steps):
        if next_order is None:
            status = 'current' if i == 0 else 'upcoming'
        elif step.order_num < next_order:
            status = 'completed'
        elif step.id == next_id:
            status = 'current'
        else:
            status = 'upcoming'
        row = step.to_dict()
        row['status'] = status
        annotated.append(row)
    return annotated


def _progress_from_steps(steps_with_status):
    total = len(steps_with_status)
    completed = sum(1 for s in steps_with_status if s.get('status') == 'completed')
    percent = int(completed * 100 / total) if total > 0 else 0
    current = next((s for s in steps_with_status if s.get('status') == 'current'), None)
    return {
        'conducted': completed,
        'completed': completed,
        'total': total,
        'percent': percent,
        'current_step_id': current.get('id') if current else None,
        'current_step_title': current.get('title') if current else None,
    }


def _get_progress(student_id, template, next_step_id=None):
    if not template:
        return _progress_from_steps([])
    steps = _annotate_plan_steps(template, next_step_id)
    return _progress_from_steps(steps)


def _template_full_name(template):
    if not template:
        return None
    if template.parent_id and template.parent:
        return f'{template.parent.name} / {template.name}'
    return template.name


def _next_scheduled_lesson_plan_step_id(student_id, template):
    """
    Тема ближайшего предстоящего урока — источник правды для «текущей» темы плана.
    Совпадает с логикой GET /api/my-next-lesson.
    """
    from sqlalchemy import or_
    from datetime import datetime

    if not student_id or not template:
        return None

    lesson_type = TaskType.query.filter_by(name='Урок').first()
    if not lesson_type:
        return None

    excluded = TaskStatus.query.filter(
        or_(
            TaskStatus.name.in_(['Отменён', 'Проведён', 'Неявка']),
            TaskStatus.group.in_(['cancelled', 'no_show', 'done']),
        )
    ).all()
    excluded_ids = [s.id for s in excluded]
    now = datetime.now()

    task = Task.query.filter(
        Task.student_id == student_id,
        Task.task_type_id == lesson_type.id,
        Task.start_date > now,
        Task.plan_step_id.isnot(None),
        or_(Task.status_id.is_(None), ~Task.status_id.in_(excluded_ids)),
    ).order_by(Task.start_date.asc(), Task.id.asc()).first()

    if not task or not task.plan_step_id:
        return None

    step = db.session.get(PlanStep, task.plan_step_id)
    if step and step.template_id == template.id:
        return step.id
    return None


def _effective_plan_next_step_id(student_id, template, user_plan):
    """Текущий шаг плана: сначала тема ближайшего урока, иначе сохранённый next_step_id."""
    from_lesson = _next_scheduled_lesson_plan_step_id(student_id, template)
    if from_lesson:
        return from_lesson
    if user_plan and user_plan.next_step_id:
        step = db.session.get(PlanStep, user_plan.next_step_id)
        if step and step.template_id == template.id:
            return user_plan.next_step_id
    return None


def _lesson_excluded_status_ids():
    from sqlalchemy import or_
    rows = TaskStatus.query.filter(
        or_(
            TaskStatus.name.in_(['Отменён', 'Проведён', 'Неявка']),
            TaskStatus.group.in_(['cancelled', 'no_show', 'done']),
        )
    ).all()
    return {s.id for s in rows}


def _students_for_plan_reports():
    student_role = Role.query.filter_by(name='student').first()
    if not student_role:
        return []
    student_ids = [ur.user_id for ur in UserRole.query.filter_by(role_id=student_role.id).all()]
    if not student_ids:
        return []
    q = User.query.filter(User.id.in_(student_ids), User.is_active == True)
    if user_has_role('teacher') and not user_has_role('admin', 'owner'):
        q = q.filter(User.teacher_id == current_user.id)
    return q.order_by(User.display_name).all()


def _student_plan_context(student):
    up = UserPlan.query.filter_by(student_id=student.id).first()
    if not up:
        return None
    template = db.session.get(PlanTemplate, up.template_id)
    if not template or template.parent_id is None:
        return None
    steps = sorted(template.steps, key=lambda s: (s.order_num, s.id))
    effective_next = _effective_plan_next_step_id(student.id, template, up)
    annotated = _annotate_plan_steps(template, effective_next)
    progress = _progress_from_steps(annotated)
    current_step = next((s for s in annotated if s.get('status') == 'current'), None)
    return {
        'user_plan': up,
        'template': template,
        'steps': steps,
        'effective_next_step_id': effective_next,
        'progress': progress,
        'current_step': current_step,
    }


def _future_student_lessons(student_id, lesson_type_id, excluded_ids):
    from sqlalchemy import or_
    from datetime import datetime

    excluded_list = list(excluded_ids) if excluded_ids else [-1]
    return Task.query.filter(
        Task.student_id == student_id,
        Task.task_type_id == lesson_type_id,
        Task.start_date.isnot(None),
        Task.start_date > datetime.now(),
        or_(Task.status_id.is_(None), ~Task.status_id.in_(excluded_list)),
    ).order_by(Task.start_date.asc(), Task.id.asc()).all()


# ── Шаблоны ──────────────────────────────────────────────────────────────────

@plans_bp.route('/api/plan-templates', methods=['GET'])
@login_required
def get_plan_templates():
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    roots = PlanTemplate.query.filter_by(parent_id=None).order_by(PlanTemplate.id).all()
    return jsonify({'templates': [t.to_dict(include_children=True) for t in roots]})


@plans_bp.route('/api/plan-templates', methods=['POST'])
@login_required
def create_plan_template():
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    name = (request.json.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Название обязательно'}), 400
    parent_id = request.json.get('parent_id')
    parent = None
    if parent_id is not None:
        parent = db.session.get(PlanTemplate, parent_id)
        if not parent:
            return jsonify({'error': 'Родительский уровень не найден'}), 404
        if parent.parent_id is not None:
            return jsonify({'error': 'Разрешено только 2 уровня'}), 400
    t = PlanTemplate(name=name, parent_id=parent.id if parent else None)
    db.session.add(t)
    db.session.commit()
    return jsonify(t.to_dict()), 201


@plans_bp.route('/api/plan-templates/<int:tid>', methods=['PUT'])
@login_required
def update_plan_template(tid):
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    t = db.get_or_404(PlanTemplate, tid)
    name = (request.json.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Название обязательно'}), 400
    t.name = name
    if 'parent_id' in request.json:
        parent_id = request.json.get('parent_id')
        if parent_id is None:
            t.parent_id = None
        else:
            parent = db.session.get(PlanTemplate, parent_id)
            if not parent:
                return jsonify({'error': 'Родительский уровень не найден'}), 404
            if parent.id == t.id or parent.parent_id is not None:
                return jsonify({'error': 'Разрешено только 2 уровня'}), 400
            t.parent_id = parent.id
    db.session.commit()
    return jsonify(t.to_dict())


@plans_bp.route('/api/plan-templates/<int:tid>', methods=['DELETE'])
@login_required
def delete_plan_template(tid):
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    t = db.get_or_404(PlanTemplate, tid)
    # Удаляем назначения этого шаблона и его подуровней
    template_ids = [t.id] + [c.id for c in t.children]
    UserPlan.query.filter(UserPlan.template_id.in_(template_ids)).delete(synchronize_session=False)
    db.session.delete(t)
    db.session.commit()
    return '', 204


@plans_bp.route('/api/plan-templates/<int:tid>/copy', methods=['POST'])
@login_required
def copy_second_level_template(tid):
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    source = db.get_or_404(PlanTemplate, tid)
    if source.parent_id is None:
        return jsonify({'error': 'Копировать можно только план 2-го уровня'}), 400

    parent_id = request.json.get('parent_id')
    if parent_id is None:
        return jsonify({'error': 'Нужно выбрать план 1-го уровня'}), 400

    parent = db.session.get(PlanTemplate, parent_id)
    if not parent:
        return jsonify({'error': 'План 1-го уровня не найден'}), 404
    if parent.parent_id is not None:
        return jsonify({'error': 'Копию можно создавать только в плане 1-го уровня'}), 400

    name = (request.json.get('name') or f'Копия {source.name}').strip()
    if not name:
        return jsonify({'error': 'Название обязательно'}), 400

    copied_template = PlanTemplate(name=name, parent_id=parent.id)
    db.session.add(copied_template)
    db.session.flush()

    # Копируем все поля шагов (на текущий момент: title, order_num) в новый шаблон.
    for step in source.steps:
        db.session.add(PlanStep(
            template_id=copied_template.id,
            title=step.title,
            order_num=step.order_num,
        ))

    db.session.commit()
    return jsonify(copied_template.to_dict()), 201


# ── Шаги шаблона ─────────────────────────────────────────────────────────────

@plans_bp.route('/api/plan-templates/<int:tid>/steps', methods=['POST'])
@login_required
def add_plan_step(tid):
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    template = db.get_or_404(PlanTemplate, tid)
    if template.parent_id is None:
        return jsonify({'error': 'Шаги добавляются только во 2-й уровень'}), 400
    title = (request.json.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Заголовок обязателен'}), 400
    max_order = db.session.execute(
        db.select(db.func.max(PlanStep.order_num)).where(PlanStep.template_id == tid)
    ).scalar() or -1
    step = PlanStep(template_id=tid, title=title, order_num=max_order + 1)
    db.session.add(step)
    db.session.commit()
    return jsonify(step.to_dict()), 201


@plans_bp.route('/api/plan-steps/<int:sid>', methods=['PUT'])
@login_required
def update_plan_step(sid):
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    step = db.get_or_404(PlanStep, sid)
    title = (request.json.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Заголовок обязателен'}), 400
    step.title = title
    db.session.commit()
    return jsonify(step.to_dict())


@plans_bp.route('/api/plan-steps/<int:sid>', methods=['DELETE'])
@login_required
def delete_plan_step(sid):
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    step = db.get_or_404(PlanStep, sid)
    db.session.delete(step)
    db.session.commit()
    return '', 204


@plans_bp.route('/api/plan-templates/<int:tid>/steps/reorder', methods=['PUT'])
@login_required
def reorder_plan_steps(tid):
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    template = db.get_or_404(PlanTemplate, tid)
    if template.parent_id is None:
        return jsonify({'error': 'Шаги добавляются только во 2-й уровень'}), 400
    step_ids = request.json.get('step_ids', [])
    for i, sid in enumerate(step_ids):
        step = db.session.get(PlanStep, sid)
        if step and step.template_id == tid:
            step.order_num = i
    db.session.commit()
    return jsonify({'ok': True})


# ── Назначение плана студенту ─────────────────────────────────────────────────

@plans_bp.route('/api/students/<int:student_id>/plan', methods=['GET'])
@login_required
def get_student_plan(student_id):
    # Teachers/admins can view any student's plan; students can view their own
    if not user_has_role('admin', 'owner', 'teacher') and current_user.id != student_id:
        return jsonify({'error': 'Недостаточно прав'}), 403
    up = UserPlan.query.filter_by(student_id=student_id).first()
    if not up:
        return jsonify({'error': 'План не назначен', 'template': None, 'steps': [], 'progress': None})
    template = db.session.get(PlanTemplate, up.template_id)
    if not template:
        return jsonify({'error': 'План не найден', 'template': None, 'steps': [], 'progress': None})
    if template.parent_id is None:
        return jsonify({'error': 'Назначен только 1-й уровень плана. Назначьте 2-й уровень.', 'template': None, 'steps': [], 'progress': None})
    effective_next = _effective_plan_next_step_id(student_id, template, up)
    steps = _annotate_plan_steps(template, effective_next)
    progress = _progress_from_steps(steps)
    return jsonify({'template': {'id': template.id, 'name': template.name, 'full_name': _template_full_name(template)},
                    'steps': steps,
                    'progress': progress,
                    'next_step_id': effective_next})


@plans_bp.route('/api/students/<int:student_id>/plan', methods=['PUT'])
@login_required
def set_student_plan(student_id):
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    template_id = request.json.get('template_id')
    up = UserPlan.query.filter_by(student_id=student_id).first()
    if template_id is None:
        if up:
            db.session.delete(up)
            db.session.commit()
        return jsonify({'ok': True})
    template = db.get_or_404(PlanTemplate, template_id)
    if template.parent_id is None:
        return jsonify({'error': 'Назначать можно только план 2-го уровня'}), 400
    if up:
        up.template_id = template_id
    else:
        db.session.add(UserPlan(student_id=student_id, template_id=template_id))
    db.session.commit()
    return jsonify({'ok': True})


# ── Просмотр своего плана (студент) ──────────────────────────────────────────

@plans_bp.route('/api/my-plan', methods=['GET'])
@login_required
def my_plan():
    up = UserPlan.query.filter_by(student_id=current_user.id).first()
    if not up:
        return jsonify({'error': 'План не назначен'}), 404
    template = db.session.get(PlanTemplate, up.template_id)
    if not template:
        return jsonify({'error': 'План не найден'}), 404
    if template.parent_id is None:
        return jsonify({'error': 'Назначен только 1-й уровень плана. Обратитесь к учителю для назначения 2-го уровня.'}), 400
    effective_next = _effective_plan_next_step_id(current_user.id, template, up)
    steps = _annotate_plan_steps(template, effective_next)
    progress = _progress_from_steps(steps)
    return jsonify({'template': {'id': template.id, 'name': template.name, 'full_name': _template_full_name(template)},
                    'steps': steps,
                    'progress': progress,
                    'next_step_id': effective_next})


# ── Список студентов с назначенными планами (для страницы управления) ─────────

@plans_bp.route('/api/students-with-plans', methods=['GET'])
@login_required
def students_with_plans():
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    student_role = Role.query.filter_by(name='student').first()
    if not student_role:
        return jsonify({'students': []})
    student_ids = [ur.user_id for ur in UserRole.query.filter_by(role_id=student_role.id).all()]
    students = User.query.filter(User.id.in_(student_ids), User.is_active == True).order_by(User.display_name).all()
    assignments = {up.student_id: up.template_id for up in UserPlan.query.all()}
    return jsonify({'students': [
        {'id': s.id, 'display_name': s.display_name, 'template_id': assignments.get(s.id)}
        for s in students
    ]})


@plans_bp.route('/api/reports/plan-current-topics', methods=['GET'])
@login_required
def report_plan_current_topics():
    """Сводка: на какой теме курса сейчас каждый ученик."""
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    rows = []
    for student in _students_for_plan_reports():
        ctx = _student_plan_context(student)
        if not ctx:
            rows.append({
                'student_id': student.id,
                'student_name': student.display_name,
                'plan_name': None,
                'current_topic': None,
                'current_topic_order': None,
                'completed_topics': 0,
                'total_topics': 0,
                'progress_percent': 0,
                'status': 'no_plan',
            })
            continue

        progress = ctx['progress']
        current = ctx['current_step']
        rows.append({
            'student_id': student.id,
            'student_name': student.display_name,
            'plan_name': _template_full_name(ctx['template']),
            'current_topic': current.get('title') if current else None,
            'current_topic_order': (current.get('order_num') + 1) if current else None,
            'completed_topics': progress.get('completed') or 0,
            'total_topics': progress.get('total') or 0,
            'progress_percent': progress.get('percent') or 0,
            'status': 'ok',
        })

    by_topic = {}
    for row in rows:
        if row['status'] != 'ok' or not row['current_topic']:
            key = '— План не назначен или тема не определена'
        else:
            key = row['current_topic']
        by_topic.setdefault(key, []).append(row['student_name'])

    grouped = [
        {'topic': topic, 'students': sorted(names)}
        for topic, names in sorted(by_topic.items(), key=lambda x: x[0])
    ]

    return jsonify({'students': rows, 'by_topic': grouped})


@plans_bp.route('/api/reports/plan-topic-schedule', methods=['GET'])
@login_required
def report_plan_topic_schedule():
    """По каждому ученику — даты будущих уроков и темы; темы без уроков в расписании."""
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403

    lesson_type = TaskType.query.filter_by(name='Урок').first()
    excluded_ids = _lesson_excluded_status_ids()
    students_data = []

    for student in _students_for_plan_reports():
        ctx = _student_plan_context(student)
        if not ctx:
            students_data.append({
                'student_id': student.id,
                'student_name': student.display_name,
                'plan_name': None,
                'schedule': [],
                'unscheduled_topics': [],
                'status': 'no_plan',
            })
            continue

        template = ctx['template']
        steps = ctx['steps']
        step_by_id = {s.id: s for s in steps}
        current = ctx['current_step']
        current_order = current.get('order_num') if current else None

        schedule = []
        scheduled_step_ids = set()
        if lesson_type:
            for lesson in _future_student_lessons(student.id, lesson_type.id, excluded_ids):
                step = step_by_id.get(lesson.plan_step_id) if lesson.plan_step_id else None
                if lesson.plan_step_id and step:
                    scheduled_step_ids.add(step.id)
                schedule.append({
                    'lesson_id': lesson.id,
                    'lesson_date_iso': lesson.start_date.strftime('%Y-%m-%dT%H:%M:%S'),
                    'lesson_date': lesson.start_date.strftime('%d.%m.%Y %H:%M'),
                    'step_id': step.id if step else None,
                    'step_title': step.title if step else '—',
                    'step_order': (step.order_num + 1) if step else None,
                })

        unscheduled = []
        for step in steps:
            if current_order is not None and step.order_num < current_order:
                continue
            if step.id in scheduled_step_ids:
                continue
            unscheduled.append({
                'step_id': step.id,
                'step_title': step.title,
                'step_order': step.order_num + 1,
            })

        students_data.append({
            'student_id': student.id,
            'student_name': student.display_name,
            'plan_name': _template_full_name(template),
            'schedule': schedule,
            'unscheduled_topics': unscheduled,
            'status': 'ok',
        })

    return jsonify({'students': students_data})
