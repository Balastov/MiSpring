from flask import Blueprint, request, jsonify
from flask_login import login_required
from extensions import db
from models import TaskStatus, TaskType, Role, Homework
from helpers import require_role, sanitize_comment_html

references_bp = Blueprint('references', __name__)


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

@references_bp.route('/api/homework', methods=['GET'])
@login_required
def get_homework():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    paginator = db.paginate(
        db.select(Homework).order_by(Homework.id),
        page=page, per_page=per_page, error_out=False
    )
    max_id_result = db.session.execute(db.select(db.func.max(Homework.id))).scalar()
    next_id = (max_id_result or 0) + 1
    return jsonify({
        'homework': [h.to_dict() for h in paginator.items],
        'total': paginator.total,
        'pages': paginator.pages,
        'current_page': paginator.page,
        'next_id': next_id,
    })


@references_bp.route('/api/homework/all', methods=['GET'])
@login_required
def get_all_homework():
    items = db.session.execute(
        db.select(Homework).order_by(Homework.id)
    ).scalars().all()
    return jsonify({'homework': [h.to_dict() for h in items]})


@references_bp.route('/api/homework', methods=['POST'])
@require_role('admin', 'owner')
def add_homework():
    data = request.get_json()
    name = (data.get('name') or '').strip()
    if not name or len(name) > 100:
        return jsonify({'error': 'Наименование: от 1 до 100 символов'}), 400
    comment = sanitize_comment_html(data.get('comment') or '') or None
    hw = Homework(name=name, comment=comment)
    db.session.add(hw)
    db.session.commit()
    return jsonify(hw.to_dict()), 201


@references_bp.route('/api/homework/<int:hw_id>', methods=['PUT'])
@require_role('admin', 'owner')
def update_homework(hw_id):
    hw = db.get_or_404(Homework, hw_id)
    data = request.get_json()
    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name or len(name) > 100:
            return jsonify({'error': 'Наименование: от 1 до 100 символов'}), 400
        hw.name = name
    if 'comment' in data:
        hw.comment = sanitize_comment_html(data['comment'] or '') or None
    db.session.commit()
    return jsonify(hw.to_dict())


@references_bp.route('/api/homework/<int:hw_id>', methods=['DELETE'])
@require_role('admin', 'owner')
def delete_homework(hw_id):
    hw = db.get_or_404(Homework, hw_id)
    db.session.delete(hw)
    db.session.commit()
    return '', 204
