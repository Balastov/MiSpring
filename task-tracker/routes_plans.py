from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import PlanTemplate, PlanStep, UserPlan, Task, TaskStatus, TaskType, User, Role, UserRole
from helpers import user_has_role

plans_bp = Blueprint('plans', __name__)


def _get_progress(student_id, template):
    conducted = db.session.execute(
        db.select(db.func.count(Task.id))
        .join(TaskStatus, Task.status_id == TaskStatus.id)
        .join(TaskType, Task.task_type_id == TaskType.id)
        .where(
            Task.student_id == student_id,
            TaskStatus.name == 'Проведён',
            TaskType.name == 'Урок',
        )
    ).scalar() or 0
    total = len(template.steps)
    percent = min(int(conducted * 100 / total), 100) if total > 0 else 0
    return {'conducted': conducted, 'total': total, 'percent': percent}


# ── Шаблоны ──────────────────────────────────────────────────────────────────

@plans_bp.route('/api/plan-templates', methods=['GET'])
@login_required
def get_plan_templates():
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    templates = PlanTemplate.query.order_by(PlanTemplate.id).all()
    return jsonify({'templates': [t.to_dict() for t in templates]})


@plans_bp.route('/api/plan-templates', methods=['POST'])
@login_required
def create_plan_template():
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    name = (request.json.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Название обязательно'}), 400
    t = PlanTemplate(name=name)
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
    db.session.commit()
    return jsonify(t.to_dict())


@plans_bp.route('/api/plan-templates/<int:tid>', methods=['DELETE'])
@login_required
def delete_plan_template(tid):
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    t = db.get_or_404(PlanTemplate, tid)
    # Удаляем назначения этого шаблона студентам
    UserPlan.query.filter_by(template_id=tid).delete()
    db.session.delete(t)
    db.session.commit()
    return '', 204


# ── Шаги шаблона ─────────────────────────────────────────────────────────────

@plans_bp.route('/api/plan-templates/<int:tid>/steps', methods=['POST'])
@login_required
def add_plan_step(tid):
    if not user_has_role('admin', 'owner', 'teacher'):
        return jsonify({'error': 'Недостаточно прав'}), 403
    db.get_or_404(PlanTemplate, tid)
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
    db.get_or_404(PlanTemplate, tid)
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
    progress = _get_progress(student_id, template)
    return jsonify({'template': {'id': template.id, 'name': template.name},
                    'steps': [s.to_dict() for s in template.steps],
                    'progress': progress,
                    'next_step_id': up.next_step_id})


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
    db.get_or_404(PlanTemplate, template_id)
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
    progress = _get_progress(current_user.id, template)
    return jsonify({'template': {'id': template.id, 'name': template.name},
                    'steps': [s.to_dict() for s in template.steps],
                    'progress': progress})


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
