"""
Telegram integration API routes
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from extensions import db
from models import User
import random
import string

telegram_bp = Blueprint('telegram', __name__)


def generate_binding_code():
    """Generate a unique 6-character binding code"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        # Check if code is unique
        existing = User.query.filter_by(telegram_code=code).first()
        if not existing:
            return code


@telegram_bp.route('/api/telegram/generate-code', methods=['POST'])
@login_required
def generate_code():
    """
    Generate a new binding code for the current user
    Returns: {"code": "ABC123"}
    """
    user = User.query.get(current_user.id)

    if user.telegram_id:
        return jsonify({
            'error': 'Telegram уже привязан к этому аккаунту'
        }), 400

    # Generate new code
    code = generate_binding_code()
    user.telegram_code = code
    db.session.commit()

    return jsonify({
        'code': code
    })


@telegram_bp.route('/api/telegram/bind', methods=['POST'])
def bind_telegram():
    """
    Bind a Telegram account to a user account
    Called by the bot when user enters the code

    Request body:
    {
        "code": "ABC123",
        "telegram_id": "123456789",
        "telegram_username": "username"
    }
    """
    data = request.get_json()
    code = data.get('code', '').strip().upper()
    telegram_id = str(data.get('telegram_id', '')).strip()
    telegram_username = data.get('telegram_username', '').strip()

    if not code or not telegram_id:
        return jsonify({'error': 'Код и Telegram ID обязательны'}), 400

    # Find user by code
    user = User.query.filter_by(telegram_code=code).first()
    if not user:
        return jsonify({'error': 'Неверный код привязки'}), 404

    # Check if this telegram_id is already bound to another user
    existing = User.query.filter_by(telegram_id=telegram_id).first()
    if existing and existing.id != user.id:
        return jsonify({
            'error': 'Этот Telegram аккаунт уже привязан к другому пользователю'
        }), 400

    # Bind the account
    user.telegram_id = telegram_id
    user.telegram_username = telegram_username
    user.telegram_code = None  # Clear the code after successful binding
    user.telegram_notifications = True  # Enable notifications by default
    db.session.commit()

    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'display_name': user.display_name,
            'username': user.username
        }
    })


@telegram_bp.route('/api/telegram/unbind', methods=['DELETE'])
@login_required
def unbind_telegram():
    """
    Unbind Telegram from the current user account
    """
    user = User.query.get(current_user.id)

    if not user.telegram_id:
        return jsonify({'error': 'Telegram не привязан'}), 400

    # Clear all telegram fields
    user.telegram_id = None
    user.telegram_username = None
    user.telegram_code = None
    user.telegram_notifications = True  # Reset to default
    db.session.commit()

    return jsonify({'success': True})


@telegram_bp.route('/api/telegram/notifications', methods=['PATCH'])
@login_required
def toggle_notifications():
    """
    Toggle telegram notifications on/off

    Request body:
    {
        "enabled": true/false
    }
    """
    data = request.get_json()
    enabled = data.get('enabled')

    if enabled is None:
        return jsonify({'error': 'Параметр enabled обязателен'}), 400

    user = User.query.get(current_user.id)

    if not user.telegram_id:
        return jsonify({'error': 'Telegram не привязан'}), 400

    user.telegram_notifications = bool(enabled)
    db.session.commit()

    return jsonify({
        'success': True,
        'enabled': user.telegram_notifications
    })


@telegram_bp.route('/api/telegram/status', methods=['GET'])
@login_required
def get_status():
    """
    Get current Telegram binding status for the user

    Returns:
    {
        "is_bound": true/false,
        "telegram_id": "123456789" or null,
        "telegram_username": "username" or null,
        "notifications_enabled": true/false,
        "pending_code": "ABC123" or null
    }
    """
    user = User.query.get(current_user.id)

    return jsonify({
        'is_bound': user.telegram_id is not None,
        'telegram_id': user.telegram_id,
        'telegram_username': user.telegram_username,
        'notifications_enabled': user.telegram_notifications,
        'pending_code': user.telegram_code
    })
