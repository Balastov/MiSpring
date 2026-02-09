from flask import Blueprint, request, jsonify
from flask_login import current_user
from extensions import db
from models import User, UserRole, Role
from helpers import require_role
import secrets

users_bp = Blueprint('users', __name__)


@users_bp.route('/api/users', methods=['GET'])
@require_role('admin', 'owner')
def get_users():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    paginator = db.paginate(
        db.select(User).order_by(User.id),
        page=page, per_page=per_page, error_out=False
    )
    max_id_result = db.session.execute(db.select(db.func.max(User.id))).scalar()
    next_id = (max_id_result or 0) + 1
    return jsonify({
        'users': [u.to_dict() for u in paginator.items],
        'total': paginator.total,
        'pages': paginator.pages,
        'current_page': paginator.page,
        'next_id': next_id,
    })


@users_bp.route('/api/users', methods=['POST'])
@require_role('admin', 'owner')
def add_user():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    if not username or len(username) > 80:
        return jsonify({'error': 'Логин: от 1 до 80 символов'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Пользователь с таким логином уже существует'}), 400

    display_name = (data.get('display_name') or '').strip()
    if not display_name or len(display_name) > 100:
        return jsonify({'error': 'Имя: от 1 до 100 символов'}), 400

    password = data.get('password') or ''
    if len(password) < 6:
        return jsonify({'error': 'Пароль: минимум 6 символов'}), 400

    user = User(
        username=username,
        display_name=display_name,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    role_ids = data.get('role_ids', [])
    for role_id in role_ids:
        if Role.query.get(role_id):
            db.session.add(UserRole(user_id=user.id, role_id=role_id))
    db.session.commit()

    return jsonify(user.to_dict()), 201


@users_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@require_role('admin', 'owner')
def update_user(user_id):
    user = db.get_or_404(User, user_id)
    data = request.get_json()

    if 'display_name' in data:
        display_name = (data['display_name'] or '').strip()
        if not display_name or len(display_name) > 100:
            return jsonify({'error': 'Имя: от 1 до 100 символов'}), 400
        user.display_name = display_name

    if 'is_active' in data:
        user.is_active = bool(data['is_active'])

    if 'role_ids' in data:
        UserRole.query.filter_by(user_id=user.id).delete()
        for role_id in data['role_ids']:
            if Role.query.get(role_id):
                db.session.add(UserRole(user_id=user.id, role_id=role_id))

    db.session.commit()
    return jsonify(user.to_dict())


@users_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@require_role('admin', 'owner')
def delete_user(user_id):
    user = db.get_or_404(User, user_id)

    if user.id == current_user.id:
        return jsonify({'error': 'Нельзя удалить свою учётную запись'}), 400

    UserRole.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    return '', 204


@users_bp.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
@require_role('admin', 'owner')
def reset_user_password(user_id):
    user = db.get_or_404(User, user_id)
    new_password = secrets.token_urlsafe(8)
    user.set_password(new_password)
    db.session.commit()
    return jsonify({'new_password': new_password})
