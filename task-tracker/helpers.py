from datetime import datetime
from functools import wraps
from flask import jsonify
from flask_login import login_required, current_user


def parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M')
    except (ValueError, TypeError):
        return None


def user_has_role(*role_names):
    from models import UserRole, Role
    if not current_user.is_authenticated:
        return False
    user_role_ids = [ur.role_id for ur in UserRole.query.filter_by(user_id=current_user.id).all()]
    if not user_role_ids:
        return False
    allowed_roles = Role.query.filter(Role.name.in_(role_names)).all()
    return any(r.id in user_role_ids for r in allowed_roles)


def require_role(*role_names):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not user_has_role(*role_names):
                return jsonify({'error': 'Недостаточно прав'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
