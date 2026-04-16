from flask import Blueprint, request, jsonify
from flask_login import login_required
from extensions import db
from models import TaskStatus, TaskType, Role, Homework, Setting, HomeworkCatalog, PlanTemplate, PlanStep
from helpers import require_role, sanitize_comment_html
import os
import json
import time

references_bp = Blueprint('references', __name__)


def _agent_debug_log(hypothesis_id, location, message, data):
    # region agent log
    _p = '/Users/aleksejbalastov/My Pet Projects/MiSpring/.cursor/debug-e062f9.log'
    try:
        os.makedirs(os.path.dirname(_p), exist_ok=True)
        with open(_p, 'a', encoding='utf-8') as _f:
            _f.write(json.dumps({
                'sessionId': 'e062f9',
                'runId': 'pre-fix',
                'hypothesisId': hypothesis_id,
                'location': location,
                'message': message,
                'data': data,
                'timestamp': int(time.time() * 1000),
            }, ensure_ascii=False) + '\n')
    except Exception:
        pass
    # endregion


# ========== Task Status Endpoints ==========

@references_bp.route('/api/task-statuses', methods=['GET'])
@login_required
def get_task_statuses():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    paginator = db.paginate(
        db.select(TaskStatus).order_by(TaskStatus.id),
        page=page, per_page=per_page, error_out=False
    )
    max_id_result = db.session.execute(db.select(db.func.max(TaskStatus.id))).scalar()
    next_id = (max_id_result or 0) + 1
    return jsonify({
        'statuses': [s.to_dict() for s in paginator.items],
        'total': paginator.total,
        'pages': paginator.pages,
        'current_page': paginator.page,
        'next_id': next_id,
    })


@references_bp.route('/api/task-statuses/all', methods=['GET'])
@login_required
def get_all_task_statuses():
    statuses = db.session.execute(
        db.select(TaskStatus).order_by(TaskStatus.name)
    ).scalars().all()
    return jsonify({'statuses': [s.to_dict() for s in statuses]})


@references_bp.route('/api/task-statuses', methods=['POST'])
@require_role('admin', 'owner')
def add_task_status():
    data = request.get_json()
    name = (data.get('name') or '').strip()
    if not name or len(name) > 100:
        return jsonify({'error': 'Имя: от 1 до 100 символов'}), 400
    status = TaskStatus(
        name=name,
        group=(data.get('group') or '').strip() or None,
    )
    db.session.add(status)
    db.session.commit()
    return jsonify(status.to_dict()), 201


@references_bp.route('/api/task-statuses/<int:status_id>', methods=['PUT'])
@require_role('admin', 'owner')
def update_task_status(status_id):
    status = db.get_or_404(TaskStatus, status_id)
    data = request.get_json()
    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name or len(name) > 100:
            return jsonify({'error': 'Имя: от 1 до 100 символов'}), 400
        status.name = name
    if 'group' in data:
        status.group = (data['group'] or '').strip() or None
    db.session.commit()
    return jsonify(status.to_dict())


@references_bp.route('/api/task-statuses/<int:status_id>', methods=['DELETE'])
@require_role('admin', 'owner')
def delete_task_status(status_id):
    status = db.get_or_404(TaskStatus, status_id)
    db.session.delete(status)
    db.session.commit()
    return '', 204


# ========== Task Type Endpoints ==========

@references_bp.route('/api/task-types', methods=['GET'])
@login_required
def get_task_types():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    paginator = db.paginate(
        db.select(TaskType).order_by(TaskType.id),
        page=page, per_page=per_page, error_out=False
    )
    max_id_result = db.session.execute(db.select(db.func.max(TaskType.id))).scalar()
    next_id = (max_id_result or 0) + 1
    return jsonify({
        'task_types': [tt.to_dict() for tt in paginator.items],
        'total': paginator.total,
        'pages': paginator.pages,
        'current_page': paginator.page,
        'next_id': next_id,
    })


@references_bp.route('/api/task-types/all', methods=['GET'])
@login_required
def get_all_task_types():
    task_types = db.session.execute(
        db.select(TaskType).order_by(TaskType.name)
    ).scalars().all()
    return jsonify({'task_types': [tt.to_dict() for tt in task_types]})


@references_bp.route('/api/task-types', methods=['POST'])
@require_role('admin', 'owner')
def add_task_type():
    data = request.get_json()
    name = (data.get('name') or '').strip()
    if not name or len(name) > 100:
        return jsonify({'error': 'Наименование: от 1 до 100 символов'}), 400
    task_type = TaskType(name=name)
    db.session.add(task_type)
    db.session.commit()
    return jsonify(task_type.to_dict()), 201


@references_bp.route('/api/task-types/<int:type_id>', methods=['PUT'])
@require_role('admin', 'owner')
def update_task_type(type_id):
    task_type = db.get_or_404(TaskType, type_id)
    data = request.get_json()
    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name or len(name) > 100:
            return jsonify({'error': 'Наименование: от 1 до 100 символов'}), 400
        task_type.name = name
    db.session.commit()
    return jsonify(task_type.to_dict())


@references_bp.route('/api/task-types/<int:type_id>', methods=['DELETE'])
@require_role('admin', 'owner')
def delete_task_type(type_id):
    task_type = db.get_or_404(TaskType, type_id)
    db.session.delete(task_type)
    db.session.commit()
    return '', 204


# ========== Role Endpoints ==========

@references_bp.route('/api/roles', methods=['GET'])
@login_required
def get_roles():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    paginator = db.paginate(
        db.select(Role).order_by(Role.id),
        page=page, per_page=per_page, error_out=False
    )
    max_id_result = db.session.execute(db.select(db.func.max(Role.id))).scalar()
    next_id = (max_id_result or 0) + 1
    return jsonify({
        'roles': [r.to_dict() for r in paginator.items],
        'total': paginator.total,
        'pages': paginator.pages,
        'current_page': paginator.page,
        'next_id': next_id,
    })


@references_bp.route('/api/roles/all', methods=['GET'])
@login_required
def get_all_roles():
    roles = db.session.execute(
        db.select(Role).order_by(Role.name)
    ).scalars().all()
    return jsonify({'roles': [r.to_dict() for r in roles]})


@references_bp.route('/api/roles', methods=['POST'])
@require_role('admin', 'owner')
def add_role():
    data = request.get_json()
    name = (data.get('name') or '').strip()
    if not name or len(name) > 100:
        return jsonify({'error': 'Наименование: от 1 до 100 символов'}), 400
    role = Role(name=name)
    db.session.add(role)
    db.session.commit()
    return jsonify(role.to_dict()), 201


@references_bp.route('/api/roles/<int:role_id>', methods=['PUT'])
@require_role('admin', 'owner')
def update_role(role_id):
    role = db.get_or_404(Role, role_id)
    data = request.get_json()
    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name or len(name) > 100:
            return jsonify({'error': 'Наименование: от 1 до 100 символов'}), 400
        role.name = name
    db.session.commit()
    return jsonify(role.to_dict())


@references_bp.route('/api/roles/<int:role_id>', methods=['DELETE'])
@require_role('admin', 'owner')
def delete_role(role_id):
    role = db.get_or_404(Role, role_id)
    db.session.delete(role)
    db.session.commit()
    return '', 204


# ========== Homework Endpoints ==========

def _template_full_name(template):
    if not template:
        return None
    if template.parent_id and template.parent:
        return f'{template.parent.name} / {template.name}'
    return template.name


@references_bp.route('/api/homework-catalogs', methods=['GET'])
@login_required
def get_homework_catalogs():
    catalogs = HomeworkCatalog.query.order_by(HomeworkCatalog.id).all()
    template_ids = [c.plan_template_id for c in catalogs if c.plan_template_id]
    templates = {}
    if template_ids:
        templates = {
            t.id: t for t in PlanTemplate.query.filter(PlanTemplate.id.in_(template_ids)).all()
        }
    return jsonify({
        'catalogs': [{
            'id': c.id,
            'name': c.name,
            'plan_template_id': c.plan_template_id,
            'plan_template_name': _template_full_name(templates.get(c.plan_template_id)),
        } for c in catalogs]
    })


@references_bp.route('/api/homework-catalogs', methods=['POST'])
@require_role('admin', 'owner', 'teacher')
def add_homework_catalog():
    data = request.get_json()
    name = (data.get('name') or '').strip()
    if not name or len(name) > 120:
        return jsonify({'error': 'Название справочника: от 1 до 120 символов'}), 400
    c = HomeworkCatalog(name=name)
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()), 201


@references_bp.route('/api/homework-catalogs/<int:catalog_id>', methods=['PUT'])
@require_role('admin', 'owner', 'teacher')
def update_homework_catalog(catalog_id):
    c = db.get_or_404(HomeworkCatalog, catalog_id)
    data = request.get_json()
    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name or len(name) > 120:
            return jsonify({'error': 'Название справочника: от 1 до 120 символов'}), 400
        c.name = name
    db.session.commit()
    return jsonify(c.to_dict())


@references_bp.route('/api/homework-catalogs/<int:catalog_id>', methods=['DELETE'])
@require_role('admin', 'owner', 'teacher')
def delete_homework_catalog(catalog_id):
    c = db.get_or_404(HomeworkCatalog, catalog_id)
    homework_ids = [h.id for h in Homework.query.filter_by(catalog_id=c.id).all()]
    if homework_ids:
        from models import Task
        Task.query.filter(Task.homework_id.in_(homework_ids)).update(
            {Task.homework_id: None},
            synchronize_session=False
        )
        Homework.query.filter(Homework.catalog_id == c.id).delete(synchronize_session=False)
    db.session.delete(c)
    db.session.commit()
    return '', 204


@references_bp.route('/api/homework-catalogs/<int:catalog_id>/binding', methods=['PUT'])
@require_role('admin', 'owner', 'teacher')
def bind_catalog_to_plan(catalog_id):
    c = db.get_or_404(HomeworkCatalog, catalog_id)
    data = request.get_json()
    template_id = data.get('plan_template_id')
    if template_id is None:
        c.plan_template_id = None
        Homework.query.filter_by(catalog_id=c.id).update({Homework.plan_step_id: None}, synchronize_session=False)
        db.session.commit()
        return jsonify(c.to_dict())

    t = db.session.get(PlanTemplate, template_id)
    if not t:
        return jsonify({'error': 'План 2-го уровня не найден'}), 404
    if t.parent_id is None:
        return jsonify({'error': 'Можно привязать только план 2-го уровня'}), 400
    exists = HomeworkCatalog.query.filter_by(plan_template_id=t.id).first()
    if exists and exists.id != c.id:
        return jsonify({'error': f'Этот план уже привязан к справочнику "{exists.name}"'}), 400
    c.plan_template_id = t.id
    Homework.query.filter(
        Homework.catalog_id == c.id,
        Homework.plan_step_id.isnot(None),
        ~Homework.plan_step_id.in_(db.select(PlanStep.id).where(PlanStep.template_id == t.id))
    ).update({Homework.plan_step_id: None}, synchronize_session=False)
    db.session.commit()
    return jsonify(c.to_dict())


@references_bp.route('/api/homework-catalogs/<int:catalog_id>/plan-steps', methods=['GET'])
@login_required
def get_catalog_plan_steps(catalog_id):
    c = db.get_or_404(HomeworkCatalog, catalog_id)
    if not c.plan_template_id:
        return jsonify({'steps': [], 'plan_template_id': None})
    steps = PlanStep.query.filter_by(template_id=c.plan_template_id).order_by(PlanStep.order_num, PlanStep.id).all()
    return jsonify({'steps': [s.to_dict() for s in steps], 'plan_template_id': c.plan_template_id})


@references_bp.route('/api/homework', methods=['GET'])
@login_required
def get_homework():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    catalog_id = request.args.get('catalog_id', type=int)
    q = db.select(Homework).order_by(Homework.id)
    if catalog_id:
        q = q.where(Homework.catalog_id == catalog_id)
    paginator = db.paginate(
        q,
        page=page, per_page=per_page, error_out=False
    )
    max_id_result = db.session.execute(db.select(db.func.max(Homework.id))).scalar()
    next_id = (max_id_result or 0) + 1
    step_ids = {h.plan_step_id for h in paginator.items if h.plan_step_id}
    steps_map = {}
    if step_ids:
        steps_map = {s.id: s.title for s in PlanStep.query.filter(PlanStep.id.in_(step_ids)).all()}
    return jsonify({
        'homework': [{
            **h.to_dict(),
            'topic_title': steps_map.get(h.plan_step_id),
        } for h in paginator.items],
        'total': paginator.total,
        'pages': paginator.pages,
        'current_page': paginator.page,
        'next_id': next_id,
    })


@references_bp.route('/api/homework/all', methods=['GET'])
@login_required
def get_all_homework():
    catalog_id = request.args.get('catalog_id', type=int)
    q = db.select(Homework).order_by(Homework.id)
    if catalog_id:
        q = q.where(Homework.catalog_id == catalog_id)
    items = db.session.execute(
        q
    ).scalars().all()
    # region agent log
    _agent_debug_log('H2', 'routes_references.py:get_all_homework', 'all homework fetched', {
        'catalogId': catalog_id,
        'total': len(items),
        'withPlanStep': sum(1 for h in items if h.plan_step_id),
    })
    # endregion
    step_ids = {h.plan_step_id for h in items if h.plan_step_id}
    steps_map = {}
    if step_ids:
        steps_map = {s.id: s.title for s in PlanStep.query.filter(PlanStep.id.in_(step_ids)).all()}
    return jsonify({'homework': [{**h.to_dict(), 'topic_title': steps_map.get(h.plan_step_id)} for h in items]})


@references_bp.route('/api/homework', methods=['POST'])
@require_role('admin', 'owner', 'teacher')
def add_homework():
    data = request.get_json()
    name = (data.get('name') or '').strip()
    if not name or len(name) > 100:
        return jsonify({'error': 'Наименование: от 1 до 100 символов'}), 400
    catalog_id = data.get('catalog_id')
    if not catalog_id:
        return jsonify({'error': 'Выберите справочник домашних заданий'}), 400
    catalog = db.session.get(HomeworkCatalog, catalog_id)
    if not catalog:
        return jsonify({'error': 'Справочник не найден'}), 404
    plan_step_id = data.get('plan_step_id')
    if plan_step_id:
        if not catalog.plan_template_id:
            return jsonify({'error': 'Справочник не привязан к плану обучения'}), 400
        step = db.session.get(PlanStep, plan_step_id)
        if not step or step.template_id != catalog.plan_template_id:
            return jsonify({'error': 'Тема должна быть шагом из привязанного плана'}), 400
    comment = sanitize_comment_html(data.get('comment') or '') or None
    hw = Homework(
        name=name,
        comment=comment,
        catalog_id=catalog.id,
        plan_step_id=plan_step_id or None,
    )
    db.session.add(hw)
    db.session.commit()
    return jsonify(hw.to_dict()), 201


@references_bp.route('/api/homework/<int:hw_id>', methods=['PUT'])
@require_role('admin', 'owner', 'teacher')
def update_homework(hw_id):
    hw = db.get_or_404(Homework, hw_id)
    data = request.get_json()
    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name or len(name) > 100:
            return jsonify({'error': 'Наименование: от 1 до 100 символов'}), 400
        hw.name = name
    if 'catalog_id' in data:
        catalog = db.session.get(HomeworkCatalog, data.get('catalog_id'))
        if not catalog:
            return jsonify({'error': 'Справочник не найден'}), 404
        hw.catalog_id = catalog.id
    if 'comment' in data:
        hw.comment = sanitize_comment_html(data['comment'] or '') or None
    if 'plan_step_id' in data:
        plan_step_id = data.get('plan_step_id')
        if not plan_step_id:
            hw.plan_step_id = None
        else:
            catalog = db.session.get(HomeworkCatalog, hw.catalog_id) if hw.catalog_id else None
            if not catalog or not catalog.plan_template_id:
                return jsonify({'error': 'Справочник не привязан к плану обучения'}), 400
            step = db.session.get(PlanStep, plan_step_id)
            if not step or step.template_id != catalog.plan_template_id:
                return jsonify({'error': 'Тема должна быть шагом из привязанного плана'}), 400
            hw.plan_step_id = plan_step_id
    # Если справочник сменился и тема перестала соответствовать — очищаем тему.
    if hw.plan_step_id and hw.catalog_id:
        catalog = db.session.get(HomeworkCatalog, hw.catalog_id)
        step = db.session.get(PlanStep, hw.plan_step_id)
        if not catalog or not catalog.plan_template_id or not step or step.template_id != catalog.plan_template_id:
            hw.plan_step_id = None
    db.session.commit()
    return jsonify(hw.to_dict())


@references_bp.route('/api/homework/<int:hw_id>', methods=['DELETE'])
@require_role('admin', 'owner', 'teacher')
def delete_homework(hw_id):
    hw = db.get_or_404(Homework, hw_id)
    db.session.delete(hw)
    db.session.commit()
    return '', 204


# ========== App Settings Endpoints ==========

@references_bp.route('/api/settings/<key>', methods=['GET'])
@login_required
def get_setting(key):
    return jsonify({'key': key, 'value': Setting.get(key, '')})


@references_bp.route('/api/settings/<key>', methods=['PUT'])
@login_required
@require_role('admin', 'owner')
def set_setting(key):
    value = request.json.get('value', '')
    Setting.set(key, value)
    return jsonify({'key': key, 'value': value})
