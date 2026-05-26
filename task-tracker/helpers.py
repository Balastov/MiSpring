import re
from datetime import datetime
from functools import wraps
from flask import jsonify
from flask_login import login_required, current_user

LAST_SEEN_UPDATE_INTERVAL_SEC = 60


def parse_datetime(value):
    if not value:
        return None
    try:
        s = str(value).strip()
        for fmt, n in (('%Y-%m-%dT%H:%M:%S', 19), ('%Y-%m-%dT%H:%M', 16)):
            if len(s) >= n:
                try:
                    return datetime.strptime(s[:n], fmt)
                except ValueError:
                    continue
        return None
    except (TypeError, ValueError):
        return None


def staff_can_view_last_seen():
    """Учитель, админ и владелец видят время последнего визита пользователей."""
    return user_has_role('admin', 'owner', 'teacher')


def record_user_last_seen(user, force=False):
    """Обновляет last_seen_at (не чаще раза в минуту, если force=False)."""
    if not user or not getattr(user, 'id', None):
        return
    from extensions import db

    now = datetime.now()
    last = user.last_seen_at
    if (
        not force
        and last
        and (now - last).total_seconds() < LAST_SEEN_UPDATE_INTERVAL_SEC
    ):
        return
    user.last_seen_at = now
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def last_seen_for_api(user):
    if not user or not user.last_seen_at:
        return {'last_seen_at': None, 'last_seen_at_display': None}
    return {
        'last_seen_at': user.last_seen_at.isoformat(),
        'last_seen_at_display': user.last_seen_at.strftime('%d.%m.%Y %H:%M'),
    }


def user_has_role(*role_names):
    from models import UserRole, Role
    if not current_user.is_authenticated:
        return False
    user_role_ids = [ur.role_id for ur in UserRole.query.filter_by(user_id=current_user.id).all()]
    if not user_role_ids:
        return False
    allowed_roles = Role.query.filter(Role.name.in_(role_names)).all()
    return any(r.id in user_role_ids for r in allowed_roles)


def sanitize_comment_html(html):
    """Allow only <a> tags with href. Strip all other HTML tags.
    Also auto-detect bare URLs and wrap them in <a> tags."""
    if not html:
        return html
    # Remove all tags except <a ...> and </a>
    clean = re.sub(r'<(?!/?a[\s>])[^>]*>', '', html)
    # Normalize <a> tags: keep only href attribute, add target/rel
    def clean_a_tag(match):
        # Support both single and double quotes
        href_match = re.search(r'href=["\']([^"\']*)["\']', match.group(0))
        if href_match:
            href = href_match.group(1)
            return f'<a href="{href}" target="_blank" rel="noopener">'
        return ''
    clean = re.sub(r'<a\s[^>]*>', clean_a_tag, clean)
    # Remove orphaned </a> tags (from <a> tags that lost their href)
    clean = re.sub(r'</a>', lambda m: '</a>', clean)
    # Auto-link bare URLs that are not already inside <a> tags
    def auto_link(text):
        parts = re.split(r'(<a\s[^>]*>.*?</a>)', text, flags=re.DOTALL)
        result = []
        for part in parts:
            if part.startswith('<a '):
                result.append(part)
            else:
                part = re.sub(
                    r'(https?://[^\s<]+)',
                    r'<a href="\1" target="_blank" rel="noopener">\1</a>',
                    part
                )
                result.append(part)
        return ''.join(result)
    clean = auto_link(clean)
    return clean.strip()


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
