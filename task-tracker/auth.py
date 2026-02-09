from flask import Blueprint, request, jsonify, redirect, url_for, render_template
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User, Role, UserRole
import os
import requests as http_requests

auth_bp = Blueprint('auth', __name__)


# ========== Auth Routes ==========

@auth_bp.route('/login')
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('login.html')


@auth_bp.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'error': 'Введите логин и пароль'}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Неверный логин или пароль'}), 401

    if not user.is_active:
        return jsonify({'error': 'Учётная запись деактивирована'}), 403

    login_user(user, remember=True)
    return jsonify(user.to_dict())


@auth_bp.route('/api/auth/logout', methods=['POST'])
@login_required
def auth_logout():
    logout_user()
    return jsonify({'ok': True})


@auth_bp.route('/api/auth/me', methods=['GET'])
@login_required
def auth_me():
    return jsonify(current_user.to_dict())


@auth_bp.route('/api/auth/change-password', methods=['POST'])
@login_required
def auth_change_password():
    data = request.get_json()
    old_password = data.get('old_password') or ''
    new_password = data.get('new_password') or ''

    if not old_password or not new_password:
        return jsonify({'error': 'Заполните все поля'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'Минимум 6 символов'}), 400

    if not current_user.check_password(old_password):
        return jsonify({'error': 'Неверный текущий пароль'}), 400

    current_user.set_password(new_password)
    db.session.commit()
    return jsonify({'ok': True})


# ========== OAuth: Yandex ==========

@auth_bp.route('/auth/yandex')
def auth_yandex():
    client_id = os.environ.get('YANDEX_CLIENT_ID')
    if not client_id:
        return 'Yandex OAuth не настроен', 500
    redirect_uri = url_for('auth.auth_yandex_callback', _external=True)
    return redirect(f'https://oauth.yandex.com/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}')


@auth_bp.route('/auth/yandex/callback')
def auth_yandex_callback():
    code = request.args.get('code')
    if not code:
        return redirect(url_for('auth.login_page'))

    client_id = os.environ.get('YANDEX_CLIENT_ID')
    client_secret = os.environ.get('YANDEX_CLIENT_SECRET')
    redirect_uri = url_for('auth.auth_yandex_callback', _external=True)

    token_resp = http_requests.post('https://oauth.yandex.com/token', data={
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
    })
    if token_resp.status_code != 200:
        return redirect(url_for('auth.login_page'))

    access_token = token_resp.json().get('access_token')

    info_resp = http_requests.get('https://login.yandex.ru/info', headers={
        'Authorization': f'OAuth {access_token}'
    })
    if info_resp.status_code != 200:
        return redirect(url_for('auth.login_page'))

    profile = info_resp.json()
    yandex_id = str(profile.get('id'))
    display_name = profile.get('display_name') or profile.get('real_name') or 'Пользователь Яндекс'

    user = User.query.filter_by(yandex_id=yandex_id).first()
    if not user:
        base_username = f'yandex_{yandex_id}'
        user = User(
            username=base_username,
            display_name=display_name,
            yandex_id=yandex_id,
        )
        db.session.add(user)
        db.session.commit()
        student_role = Role.query.filter_by(name='student').first()
        if student_role:
            db.session.add(UserRole(user_id=user.id, role_id=student_role.id))
            db.session.commit()

    if not user.is_active:
        return redirect(url_for('auth.login_page'))

    login_user(user, remember=True)
    return redirect(url_for('index'))


# ========== OAuth: VK ==========

@auth_bp.route('/auth/vk')
def auth_vk():
    client_id = os.environ.get('VK_CLIENT_ID')
    if not client_id:
        return 'VK OAuth не настроен', 500
    redirect_uri = url_for('auth.auth_vk_callback', _external=True)
    return redirect(f'https://oauth.vk.com/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&v=5.131')


@auth_bp.route('/auth/vk/callback')
def auth_vk_callback():
    code = request.args.get('code')
    if not code:
        return redirect(url_for('auth.login_page'))

    client_id = os.environ.get('VK_CLIENT_ID')
    client_secret = os.environ.get('VK_CLIENT_SECRET')
    redirect_uri = url_for('auth.auth_vk_callback', _external=True)

    token_resp = http_requests.get('https://oauth.vk.com/access_token', params={
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'code': code,
    })
    if token_resp.status_code != 200:
        return redirect(url_for('auth.login_page'))

    token_data = token_resp.json()
    if 'error' in token_data:
        return redirect(url_for('auth.login_page'))

    vk_user_id = str(token_data.get('user_id'))
    access_token = token_data.get('access_token')

    display_name = f'VK User {vk_user_id}'
    try:
        profile_resp = http_requests.get('https://api.vk.com/method/users.get', params={
            'access_token': access_token,
            'v': '5.131',
        })
        if profile_resp.status_code == 200:
            users = profile_resp.json().get('response', [])
            if users:
                first_name = users[0].get('first_name', '')
                last_name = users[0].get('last_name', '')
                display_name = f'{first_name} {last_name}'.strip() or display_name
    except Exception:
        pass

    user = User.query.filter_by(vk_id=vk_user_id).first()
    if not user:
        base_username = f'vk_{vk_user_id}'
        user = User(
            username=base_username,
            display_name=display_name,
            vk_id=vk_user_id,
        )
        db.session.add(user)
        db.session.commit()
        student_role = Role.query.filter_by(name='student').first()
        if student_role:
            db.session.add(UserRole(user_id=user.id, role_id=student_role.id))
            db.session.commit()

    if not user.is_active:
        return redirect(url_for('auth.login_page'))

    login_user(user, remember=True)
    return redirect(url_for('index'))
