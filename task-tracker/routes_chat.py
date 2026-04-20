from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from extensions import db
from models import ChatDialog, ChatMessage, User, UserRole, Role


chat_bp = Blueprint('chat', __name__)


def _get_role_names():
    return set(current_user.get_roles() if current_user.is_authenticated else [])


def _is_admin_like():
    roles = _get_role_names()
    return 'admin' in roles or 'owner' in roles


def _is_teacher():
    return 'teacher' in _get_role_names()


def _is_student():
    return 'student' in _get_role_names() and not _is_admin_like() and not _is_teacher()


def _normalize_pair(user_1_id, user_2_id):
    a = int(user_1_id)
    b = int(user_2_id)
    return (a, b) if a < b else (b, a)


def _student_role_id():
    role = Role.query.filter_by(name='student').first()
    return role.id if role else None


def _allowed_partner_ids_for_current_user():
    if _is_admin_like():
        users = User.query.filter(User.id != current_user.id, User.is_active == True).all()
        return {u.id for u in users}

    if _is_teacher():
        student_ids = [
            u.id for u in User.query.filter_by(teacher_id=current_user.id, is_active=True).all()
        ]
        if not student_ids:
            return set()
        s_role_id = _student_role_id()
        if not s_role_id:
            return set()
        allowed_student_ids = {
            ur.user_id
            for ur in UserRole.query.filter(UserRole.role_id == s_role_id, UserRole.user_id.in_(student_ids)).all()
        }
        return allowed_student_ids

    if _is_student():
        teacher_id = current_user.teacher_id
        if not teacher_id:
            return set()
        teacher = db.session.get(User, teacher_id)
        if not teacher or not teacher.is_active:
            return set()
        return {teacher.id}

    return set()


def _dialog_partner_id(dialog):
    if dialog.user_a_id == current_user.id:
        return dialog.user_b_id
    if dialog.user_b_id == current_user.id:
        return dialog.user_a_id
    return None


def _can_access_dialog(dialog):
    partner_id = _dialog_partner_id(dialog)
    if partner_id is None:
        return False
    return partner_id in _allowed_partner_ids_for_current_user()


def _dialog_unread_count(dialog_id):
    return ChatMessage.query.filter_by(
        dialog_id=dialog_id,
        is_read=False,
    ).filter(ChatMessage.sender_id != current_user.id).count()


@chat_bp.route('/api/chat/dialogs', methods=['GET'])
@login_required
def get_chat_dialogs():
    allowed_partner_ids = _allowed_partner_ids_for_current_user()

    dialogs = ChatDialog.query.filter(
        (ChatDialog.user_a_id == current_user.id) | (ChatDialog.user_b_id == current_user.id)
    ).order_by(ChatDialog.updated_at.desc(), ChatDialog.id.desc()).all()

    partner_ids = set()
    visible_dialogs = []
    for d in dialogs:
        partner_id = _dialog_partner_id(d)
        if not partner_id or partner_id not in allowed_partner_ids:
            continue
        partner_ids.add(partner_id)
        visible_dialogs.append(d)

    contacts = User.query.filter(User.id.in_(allowed_partner_ids)).order_by(User.display_name.asc()).all() if allowed_partner_ids else []
    users_by_id = {u.id: u for u in contacts}
    # ensure users present for visible dialogs
    if partner_ids:
        missing_ids = [uid for uid in partner_ids if uid not in users_by_id]
        if missing_ids:
            for u in User.query.filter(User.id.in_(missing_ids)).all():
                users_by_id[u.id] = u

    dialogs_payload = []
    for d in visible_dialogs:
        partner_id = _dialog_partner_id(d)
        partner = users_by_id.get(partner_id)
        if not partner:
            continue
        dialogs_payload.append({
            **d.to_dict(),
            'partner': {
                'id': partner.id,
                'display_name': partner.display_name,
            },
            'unread_count': _dialog_unread_count(d.id),
        })

    contacts_payload = [
        {'id': u.id, 'display_name': u.display_name}
        for u in contacts
    ]

    return jsonify({
        'dialogs': dialogs_payload,
        'contacts': contacts_payload,
    })


@chat_bp.route('/api/chat/dialogs', methods=['POST'])
@login_required
def create_or_get_dialog():
    data = request.get_json(force=True, silent=True) or {}
    partner_id = data.get('partner_id')
    try:
        partner_id = int(partner_id)
    except (TypeError, ValueError):
        return jsonify({'error': 'Некорректный собеседник'}), 400

    if partner_id == current_user.id:
        return jsonify({'error': 'Нельзя создать диалог с самим собой'}), 400
    if partner_id not in _allowed_partner_ids_for_current_user():
        return jsonify({'error': 'Недостаточно прав для диалога с этим пользователем'}), 403
    partner = db.session.get(User, partner_id)
    if not partner or not partner.is_active:
        return jsonify({'error': 'Пользователь не найден'}), 404

    user_a_id, user_b_id = _normalize_pair(current_user.id, partner_id)
    dialog = ChatDialog.query.filter_by(user_a_id=user_a_id, user_b_id=user_b_id).first()
    if not dialog:
        dialog = ChatDialog(
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.session.add(dialog)
        db.session.commit()

    return jsonify({
        'dialog': {
            **dialog.to_dict(),
            'partner': {
                'id': partner.id,
                'display_name': partner.display_name,
            },
            'unread_count': _dialog_unread_count(dialog.id),
        }
    })


@chat_bp.route('/api/chat/dialogs/<int:dialog_id>/messages', methods=['GET'])
@login_required
def get_dialog_messages(dialog_id):
    dialog = db.session.get(ChatDialog, dialog_id)
    if not dialog or not _can_access_dialog(dialog):
        return jsonify({'error': 'Диалог не найден или недоступен'}), 404

    before_id = request.args.get('before_id', type=int)
    limit = request.args.get('limit', 50, type=int)
    if limit <= 0:
        limit = 50
    limit = min(limit, 100)

    q = ChatMessage.query.filter_by(dialog_id=dialog.id)
    if before_id:
        q = q.filter(ChatMessage.id < before_id)
    msgs = q.order_by(ChatMessage.id.desc()).limit(limit).all()
    msgs.reverse()

    sender_ids = {m.sender_id for m in msgs}
    senders = {}
    if sender_ids:
        senders = {u.id: u.display_name for u in User.query.filter(User.id.in_(sender_ids)).all()}

    return jsonify({
        'messages': [
            {
                **m.to_dict(),
                'sender_name': senders.get(m.sender_id),
            }
            for m in msgs
        ]
    })


@chat_bp.route('/api/chat/dialogs/<int:dialog_id>/messages', methods=['POST'])
@login_required
def send_dialog_message(dialog_id):
    dialog = db.session.get(ChatDialog, dialog_id)
    if not dialog or not _can_access_dialog(dialog):
        return jsonify({'error': 'Диалог не найден или недоступен'}), 404

    data = request.get_json(force=True, silent=True) or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'Введите сообщение'}), 400
    if len(text) > 1000:
        return jsonify({'error': 'Сообщение: не более 1000 символов'}), 400

    msg = ChatMessage(
        dialog_id=dialog.id,
        sender_id=current_user.id,
        text=text,
        created_at=datetime.now(),
        is_read=False,
    )
    dialog.updated_at = datetime.now()
    db.session.add(msg)
    db.session.commit()
    return jsonify({'message': {**msg.to_dict(), 'sender_name': current_user.display_name}}), 201


@chat_bp.route('/api/chat/dialogs/<int:dialog_id>/read', methods=['POST'])
@login_required
def mark_dialog_read(dialog_id):
    dialog = db.session.get(ChatDialog, dialog_id)
    if not dialog or not _can_access_dialog(dialog):
        return jsonify({'error': 'Диалог не найден или недоступен'}), 404

    updated = ChatMessage.query.filter_by(dialog_id=dialog.id, is_read=False).filter(
        ChatMessage.sender_id != current_user.id
    ).update({ChatMessage.is_read: True}, synchronize_session=False)
    db.session.commit()
    return jsonify({'updated': int(updated or 0)})


@chat_bp.route('/api/chat/unread-count', methods=['GET'])
@login_required
def get_unread_count():
    dialogs = ChatDialog.query.filter(
        (ChatDialog.user_a_id == current_user.id) | (ChatDialog.user_b_id == current_user.id)
    ).all()
    count = 0
    for d in dialogs:
        if not _can_access_dialog(d):
            continue
        count += ChatMessage.query.filter_by(dialog_id=d.id, is_read=False).filter(
            ChatMessage.sender_id != current_user.id
        ).count()
    return jsonify({'unread_count': count})
