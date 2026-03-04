from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user, login_required
from extensions import db
from models import User, UserRole, Role
from helpers import require_role
import secrets
import os

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

    if 'teacher_id' in data:
        user.teacher_id = data['teacher_id'] or None

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


@users_bp.route('/api/teachers', methods=['GET'])
@login_required
def get_teachers():
    teacher_role = Role.query.filter_by(name='teacher').first()
    if not teacher_role:
        return jsonify({'teachers': []})
    teacher_ids = [ur.user_id for ur in UserRole.query.filter_by(role_id=teacher_role.id).all()]
    teachers = User.query.filter(User.id.in_(teacher_ids)).order_by(User.display_name).all()
    return jsonify({'teachers': [
        {'id': t.id, 'display_name': t.display_name, 'teacher_photo': t.teacher_photo}
        for t in teachers
    ]})


@users_bp.route('/api/users/<int:user_id>/photo', methods=['POST'])
@require_role('admin', 'owner')
def upload_teacher_photo(user_id):
    user = db.get_or_404(User, user_id)
    if 'photo' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400
    file = request.files['photo']
    data = file.read()
    if len(data) > 5 * 1024 * 1024:
        return jsonify({'error': 'Файл слишком большой (макс. 5 МБ)'}), 400
    ext = os.path.splitext(file.filename or '')[1].lower() or '.jpg'
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
        return jsonify({'error': 'Недопустимый формат файла'}), 400
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'teacher_photos')
    os.makedirs(upload_dir, exist_ok=True)
    # Remove old photo if different extension
    if user.teacher_photo:
        old_path = os.path.join(upload_dir, user.teacher_photo)
        if os.path.exists(old_path):
            os.remove(old_path)
    filename = f'teacher_{user_id}{ext}'
    with open(os.path.join(upload_dir, filename), 'wb') as f:
        f.write(data)
    user.teacher_photo = filename
    db.session.commit()
    return jsonify({'teacher_photo': filename})


@users_bp.route('/api/my-teacher', methods=['GET'])
@login_required
def get_my_teacher():
    if not current_user.teacher_id:
        return jsonify({'teacher': None})
    teacher = db.session.get(User, current_user.teacher_id)
    if not teacher:
        return jsonify({'teacher': None})
    photo_url = f'/static/uploads/teacher_photos/{teacher.teacher_photo}' if teacher.teacher_photo else None
    return jsonify({'teacher': {'id': teacher.id, 'display_name': teacher.display_name, 'photo_url': photo_url}})
