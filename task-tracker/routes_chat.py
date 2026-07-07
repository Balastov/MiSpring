import json
import os
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from extensions import db
from models import ChatDialog, ChatMessage, ChatPushSubscription, User, UserRole, Role

try:
    from pywebpush import webpush, WebPushException
except Exception:  # pragma: no cover - optional dependency
    webpush = None
    WebPushException = Exception


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


def _is_chat_role_allowed():
    roles = _get_role_names()
    return bool({'student', 'teacher', 'admin', 'owner'} & roles)


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
        allowed = set()

        # Базовый партнёр ученика — назначенный учитель.
        teacher_id = current_user.teacher_id
        if teacher_id:
            teacher = db.session.get(User, teacher_id)
            if teacher and teacher.is_active:
                allowed.add(teacher.id)

        # Дополнительно разрешаем уже существующие диалоги:
        # если первым написал админ/другой пользователь, ученик видит этот диалог.
        dialogs = ChatDialog.query.filter(
            (ChatDialog.user_a_id == current_user.id) | (ChatDialog.user_b_id == current_user.id)
        ).all()
        partner_ids = set()
        for d in dialogs:
            pid = d.user_b_id if d.user_a_id == current_user.id else d.user_a_id
            if pid:
                partner_ids.add(pid)
        if partner_ids:
            active_partners = User.query.filter(User.id.in_(partner_ids), User.is_active == True).all()
            allowed.update(u.id for u in active_partners)

        return allowed

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


def _webpush_config():
    public_key = (os.environ.get('WEBPUSH_PUBLIC_KEY') or '').strip()
    private_key = (os.environ.get('WEBPUSH_PRIVATE_KEY') or '').strip()
    subject = (os.environ.get('WEBPUSH_SUBJECT') or 'mailto:support@mispring.local').strip()
    enabled = bool(webpush and public_key and private_key)
    return {
        'enabled': enabled,
        'public_key': public_key if enabled else '',
        'private_key': private_key if enabled else '',
        'subject': subject,
    }


def _recipient_id_for_dialog(dialog):
    if dialog.user_a_id == current_user.id:
        return dialog.user_b_id
    if dialog.user_b_id == current_user.id:
        return dialog.user_a_id
    return None


def _send_push_to_user(user_id, payload):
    cfg = _webpush_config()
    if not cfg['enabled'] or not user_id:
        return 0

    subscriptions = ChatPushSubscription.query.filter_by(user_id=int(user_id)).all()
    if not subscriptions:
        return 0

    sent = 0
    for sub in subscriptions:
        info = {
            'endpoint': sub.endpoint,
            'keys': {
                'p256dh': sub.p256dh,
                'auth': sub.auth,
            }
        }
        try:
            webpush(
                subscription_info=info,
                data=json.dumps(payload, ensure_ascii=False),
                vapid_private_key=cfg['private_key'],
                vapid_claims={'sub': cfg['subject']},
                ttl=90,
            )
            sub.updated_at = datetime.now()
            sub.last_success_at = datetime.now()
            sub.last_error = None
            sub.last_error_at = None
            sent += 1
        except WebPushException as e:
            sub.updated_at = datetime.now()
            sub.last_error = str(e)[:255]
            sub.last_error_at = datetime.now()
            status_code = getattr(getattr(e, 'response', None), 'status_code', None)
            # Endpoint expired/unregistered in browser.
            if status_code in (404, 410):
                db.session.delete(sub)
        except Exception as e:  # pragma: no cover
            sub.updated_at = datetime.now()
            sub.last_error = str(e)[:255]
            sub.last_error_at = datetime.now()
    db.session.commit()
    return sent


def get_chat_administrator_user():
    """Учётная запись, от имени которой уходят системные сообщения в чат (фиксированно user id=1)."""
    u = db.session.get(User, 1)
    if u and u.is_active:
        return u
    return None


def lesson_reminder_sender_label(teacher_user):
    """Имя для подписи в чате: display_name + «GPT» без пробела между (например «МиладаGPT»)."""
    base = (teacher_user.display_name or 'Учитель').strip()
    if not base:
        base = 'Учитель'
    return f'{base}GPT'


def send_system_chat_message(sender, recipient_id, text, sender_label=None):
    """
    Создаёт диалог при необходимости, сохраняет сообщение от sender, уведомляет получателя (web push).
    Не требует HTTP-контекста (для фоновых задач).
    sender_label — необязательная подпись в интерфейсе (иначе показывается display_name отправителя).
    """
    if not sender:
        return False
    text = (text or '').strip()
    if not text or len(text) > 1000:
        return False
    try:
        recipient_id = int(recipient_id)
    except (TypeError, ValueError):
        return False
    if recipient_id == sender.id:
        return False
    recipient = db.session.get(User, recipient_id)
    if not recipient or not recipient.is_active:
        return False

    user_a_id, user_b_id = _normalize_pair(sender.id, recipient_id)
    dialog = ChatDialog.query.filter_by(user_a_id=user_a_id, user_b_id=user_b_id).first()
    if not dialog:
        now = datetime.now()
        dialog = ChatDialog(
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            created_at=now,
            updated_at=now,
        )
        db.session.add(dialog)
        db.session.flush()

    label = (sender_label or '').strip() or None
    if label and len(label) > 120:
        label = label[:120]

    msg = ChatMessage(
        dialog_id=dialog.id,
        sender_id=sender.id,
        text=text,
        created_at=datetime.now(),
        is_read=False,
        sender_label=label,
    )
    dialog.updated_at = datetime.now()
    db.session.add(msg)
    db.session.commit()

    push_name = label or sender.display_name or 'Сообщение'
    snippet = text if len(text) <= 120 else (text[:117] + '...')
    _send_push_to_user(recipient_id, {
        'title': f'{push_name}: новое сообщение',
        'body': snippet,
        'url': '/',
        'dialog_id': dialog.id,
    })
    return True


@chat_bp.route('/api/chat/dialogs', methods=['GET'])
@login_required
def get_chat_dialogs():
    if not _is_chat_role_allowed():
        return jsonify({'error': 'Чат недоступен для текущей роли'}), 403
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
    if not _is_chat_role_allowed():
        return jsonify({'error': 'Чат недоступен для текущей роли'}), 403
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
    if not _is_chat_role_allowed():
        return jsonify({'error': 'Чат недоступен для текущей роли'}), 403
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
                'sender_name': (m.sender_label or '').strip() or senders.get(m.sender_id),
            }
            for m in msgs
        ]
    })


@chat_bp.route('/api/chat/dialogs/<int:dialog_id>/messages', methods=['POST'])
@login_required
def send_dialog_message(dialog_id):
    if not _is_chat_role_allowed():
        return jsonify({'error': 'Чат недоступен для текущей роли'}), 403
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

    recipient_id = _recipient_id_for_dialog(dialog)
    snippet = text if len(text) <= 120 else (text[:117] + '...')
    _send_push_to_user(recipient_id, {
        'title': f'{current_user.display_name}: новое сообщение',
        'body': snippet,
        'url': '/',
        'dialog_id': dialog.id,
    })
    return jsonify({'message': {**msg.to_dict(), 'sender_name': current_user.display_name}}), 201


@chat_bp.route('/api/chat/dialogs/<int:dialog_id>/read', methods=['POST'])
@login_required
def mark_dialog_read(dialog_id):
    if not _is_chat_role_allowed():
        return jsonify({'error': 'Чат недоступен для текущей роли'}), 403
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
    if not _is_chat_role_allowed():
        return jsonify({'unread_count': 0}), 200
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


@chat_bp.route('/api/chat/push/public-key', methods=['GET'])
@login_required
def get_push_public_key():
    if not _is_chat_role_allowed():
        return jsonify({'enabled': False, 'public_key': ''})
    cfg = _webpush_config()
    return jsonify({'enabled': cfg['enabled'], 'public_key': cfg['public_key']})


@chat_bp.route('/api/chat/push/status', methods=['GET'])
@login_required
def get_push_status():
    if not _is_chat_role_allowed():
        return jsonify({'server_enabled': False, 'subscribed': False, 'subscription_count': 0})
    cfg = _webpush_config()
    count = ChatPushSubscription.query.filter_by(user_id=current_user.id).count()
    return jsonify({
        'server_enabled': cfg['enabled'],
        'subscribed': count > 0,
        'subscription_count': count,
    })


@chat_bp.route('/api/chat/push/unsubscribe-all', methods=['POST'])
@login_required
def unsubscribe_all_push():
    if not _is_chat_role_allowed():
        return jsonify({'error': 'Недоступно для текущей роли'}), 403
    ChatPushSubscription.query.filter_by(user_id=current_user.id).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'ok': True})


@chat_bp.route('/api/chat/push/test', methods=['POST'])
@login_required
def test_push():
    if not _is_chat_role_allowed():
        return jsonify({'error': 'Недоступно для текущей роли'}), 403
    cfg = _webpush_config()
    if not cfg['enabled']:
        return jsonify({'error': 'Push-уведомления не настроены на сервере'}), 400
    sent = _send_push_to_user(current_user.id, {
        'title': 'MiSpring: тестовое уведомление',
        'body': 'Уведомления работают на этом устройстве',
        'url': '/',
        'tag': 'mispring-push-test',
    })
    if sent <= 0:
        return jsonify({'error': 'Не удалось отправить. Включите уведомления на этом устройстве.'}), 400
    return jsonify({'ok': True, 'sent': sent})


@chat_bp.route('/api/chat/push/subscribe', methods=['POST'])
@login_required
def subscribe_push():
    if not _is_chat_role_allowed():
        return jsonify({'error': 'Чат недоступен для текущей роли'}), 403
    data = request.get_json(force=True, silent=True) or {}
    endpoint = (data.get('endpoint') or '').strip()
    keys = data.get('keys') if isinstance(data.get('keys'), dict) else {}
    p256dh = (keys.get('p256dh') or '').strip()
    auth = (keys.get('auth') or '').strip()
    if not endpoint or not p256dh or not auth:
        return jsonify({'error': 'Некорректная push-подписка'}), 400

    sub = ChatPushSubscription.query.filter_by(endpoint=endpoint).first()
    if not sub:
        sub = ChatPushSubscription(
            user_id=current_user.id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            user_agent=(request.headers.get('User-Agent') or '')[:255],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.session.add(sub)
    else:
        sub.user_id = current_user.id
        sub.p256dh = p256dh
        sub.auth = auth
        sub.user_agent = (request.headers.get('User-Agent') or '')[:255]
        sub.updated_at = datetime.now()

    db.session.commit()
    return jsonify({'ok': True})


@chat_bp.route('/api/chat/push/unsubscribe', methods=['POST'])
@login_required
def unsubscribe_push():
    data = request.get_json(force=True, silent=True) or {}
    endpoint = (data.get('endpoint') or '').strip()
    if not endpoint:
        return jsonify({'ok': True})
    ChatPushSubscription.query.filter_by(user_id=current_user.id, endpoint=endpoint).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'ok': True})
