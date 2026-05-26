from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user, login_required
from extensions import db
from models import User, UserRole, Role
from helpers import require_role, user_has_role, staff_can_view_last_seen, last_seen_for_api
from lesson_price_service import sync_student_lesson_price
import secrets
import os
import re

users_bp = Blueprint('users', __name__)
TZ_PATTERN = re.compile(r'^UTC([+-])(0\d|1[0-4]):([0-5]\d)$')


def _is_admin_like():
    return user_has_role('admin', 'owner')


def _is_teacher():
    return user_has_role('teacher') and not _is_admin_like()


def _is_student_user(user):
    roles = set(user.get_roles() if user else [])
    return 'student' in roles


def _student_role_id():
    role = Role.query.filter_by(name='student').first()
    return role.id if role else None


def _role_ids_include_student(role_ids):
    sid = _student_role_id()
    if not sid or not role_ids:
        return False
    try:
        ids = {int(r) for r in role_ids}
    except (TypeError, ValueError):
        return False
    return sid in ids


def _validate_student_required_fields(data):
    """Обязательные поля ученика: учитель и стоимость урока."""
    teacher_id = data.get('teacher_id')
    if not teacher_id:
        return 'Для ученика необходимо выбрать учителя'

    lesson_price = data.get('lesson_price')
    if lesson_price is None or (isinstance(lesson_price, str) and not str(lesson_price).strip()):
        return 'Для ученика необходимо указать стоимость урока'
    try:
        price = float(lesson_price)
        if price < 0:
            return 'Стоимость урока не может быть отрицательной'
    except (TypeError, ValueError):
        return 'Некорректная стоимость урока'
    return None


def _apply_student_fields(user, data):
    user.teacher_id = int(data['teacher_id'])
    user.lesson_price = float(data['lesson_price'])


def _can_teacher_manage_student(user):
    if not user or not _is_teacher():
        return False
    if not _is_student_user(user):
        return False
    return int(user.teacher_id or 0) == int(current_user.id or 0)


def _can_view_student_credentials(user):
    if not user or not _is_student_user(user):
        return False
    if _is_admin_like():
        return True
    return _can_teacher_manage_student(user)


def _normalize_timezone(raw):
    value = str(raw or '').strip().upper()
    if not value:
        value = 'UTC+03:00'
    m = TZ_PATTERN.match(value)
    if not m:
        return None
    sign = m.group(1)
    hh = int(m.group(2))
    mm = int(m.group(3))
    total = hh * 60 + mm
    if sign == '-':
        total = -total
    if total < -12 * 60 or total > 14 * 60:
        return None
    return value


@users_bp.route('/api/users', methods=['GET'])
@login_required
def get_users():
    if not (_is_admin_like() or _is_teacher()):
        return jsonify({'error': 'Недостаточно прав'}), 403

    page = request.args.get('page', 1, type=int)
    per_page = 50
    query = db.select(User)

    if _is_teacher():
        student_role = Role.query.filter_by(name='student').first()
        if not student_role:
            return jsonify({
                'users': [],
                'total': 0,
                'pages': 0,
                'current_page': 1,
                'next_id': 1,
            })
        query = (
            query.join(UserRole, UserRole.user_id == User.id)
            .where(
                UserRole.role_id == student_role.id,
                User.teacher_id == current_user.id,
            )
        )

    paginator = db.paginate(query.order_by(User.id), page=page, per_page=per_page, error_out=False)
    max_id_result = db.session.execute(db.select(db.func.max(User.id))).scalar()
    next_id = (max_id_result or 0) + 1
    include_last_seen = staff_can_view_last_seen()
    payload = []
    for u in paginator.items:
        item = u.to_dict()
        if include_last_seen:
            item.update(last_seen_for_api(u))
        if _can_view_student_credentials(u):
            item['plain_password'] = u.password_plain or ''
        payload.append(item)

    return jsonify({
        'users': payload,
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
    timezone = _normalize_timezone(data.get('timezone'))
    if timezone is None:
        return jsonify({'error': 'Некорректный часовой пояс'}), 400

    role_ids = data.get('role_ids', [])
    if _role_ids_include_student(role_ids):
        student_err = _validate_student_required_fields(data)
        if student_err:
            return jsonify({'error': student_err}), 400

    user = User(
        username=username,
        display_name=display_name,
        timezone=timezone,
    )
    user.set_password(password)
    user.password_plain = password
    db.session.add(user)
    db.session.commit()

    for role_id in role_ids:
        if Role.query.get(role_id):
            db.session.add(UserRole(user_id=user.id, role_id=role_id))
    if _role_ids_include_student(role_ids):
        _apply_student_fields(user, data)
        err = sync_student_lesson_price(
            user, user.lesson_price, created_by_user_id=current_user.id
        )
        if err:
            return jsonify({'error': err}), 400
    db.session.commit()

    return jsonify(user.to_dict()), 201


@users_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    if not (_is_admin_like() or _is_teacher()):
        return jsonify({'error': 'Недостаточно прав'}), 403
    user = db.get_or_404(User, user_id)
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'Некорректный payload'}), 400

    if _is_teacher():
        if not _can_teacher_manage_student(user):
            return jsonify({'error': 'Недостаточно прав для этого ученика'}), 403
        # Учитель может менять только часовой пояс своих учеников.
        timezone = _normalize_timezone(data.get('timezone'))
        if timezone is None:
            return jsonify({'error': 'Некорректный часовой пояс'}), 400
        user.timezone = timezone
        db.session.commit()
        return jsonify(user.to_dict())

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

    if 'lesson_price' in data:
        lp = data.get('lesson_price')
        price_val = None if lp is None or (isinstance(lp, str) and not str(lp).strip()) else lp
        err = sync_student_lesson_price(
            user,
            price_val,
            effective_from=data.get('lesson_price_effective_from'),
            created_by_user_id=current_user.id,
        )
        if err:
            return jsonify({'error': err}), 400

    if 'timezone' in data:
        timezone = _normalize_timezone(data.get('timezone'))
        if timezone is None:
            return jsonify({'error': 'Некорректный часовой пояс'}), 400
        user.timezone = timezone

    db.session.flush()
    if _is_student_user(user):
        check = {
            'teacher_id': user.teacher_id,
            'lesson_price': user.lesson_price if user.lesson_price is not None else data.get('lesson_price'),
        }
        student_err = _validate_student_required_fields(check)
        if student_err:
            return jsonify({'error': student_err}), 400

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
@login_required
def reset_user_password(user_id):
    if not (_is_admin_like() or _is_teacher()):
        return jsonify({'error': 'Недостаточно прав'}), 403

    user = db.get_or_404(User, user_id)
    if not _is_student_user(user):
        return jsonify({'error': 'Сброс пароля доступен только для учеников'}), 400
    if _is_teacher() and not _can_teacher_manage_student(user):
        return jsonify({'error': 'Недостаточно прав для этого ученика'}), 403

    data = request.get_json(silent=True) or {}
    mode = (data.get('mode') or 'auto').strip().lower()

    def _validate_manual_password(pw: str):
        pw = str(pw or '')
        if len(pw) < 8:
            return 'Пароль должен быть не короче 8 символов'
        if not re.search(r'[A-Za-z]', pw):
            return 'В пароле должна быть хотя бы одна английская буква'
        if not re.search(r'\d', pw):
            return 'В пароле должна быть хотя бы одна цифра'
        return None

    if mode == 'manual':
        manual_pw = data.get('password') or ''
        err = _validate_manual_password(manual_pw)
        if err:
            return jsonify({'error': err}), 400
        new_password = str(manual_pw)
    else:
        # Backward compatible default: auto-generate.
        new_password = secrets.token_urlsafe(12)
    user.set_password(new_password)
    user.password_plain = new_password
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
