from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import os
import secrets
import requests as http_requests

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "tasks.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db = SQLAlchemy(app)

# ========== Flask-Login Setup ==========

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Требуется авторизация'}), 401
    return redirect(url_for('login_page'))


@app.context_processor
def inject_cache_bust():
    def cache_bust(filename):
        static_path = os.path.join(app.static_folder, filename)
        if os.path.exists(static_path):
            mtime = os.path.getmtime(static_path)
            return int(mtime)
        return None
    return dict(cache_bust=cache_bust)


# ========== Models ==========

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    display_name = db.Column(db.String(100), nullable=False)
    yandex_id = db.Column(db.String(100), unique=True, nullable=True)
    vk_id = db.Column(db.String(100), unique=True, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def get_roles(self):
        user_roles = UserRole.query.filter_by(user_id=self.id).all()
        role_ids = [ur.role_id for ur in user_roles]
        if not role_ids:
            return []
        roles = Role.query.filter(Role.id.in_(role_ids)).all()
        return [r.name for r in roles]

    def get_auth_source(self):
        if self.yandex_id:
            return 'yandex'
        if self.vk_id:
            return 'vk'
        return 'local'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'display_name': self.display_name,
            'yandex_id': self.yandex_id,
            'vk_id': self.vk_id,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%d.%m.%Y %H:%M') if self.created_at else None,
            'roles': self.get_roles(),
            'auth_source': self.get_auth_source(),
        }


class UserRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'role_id'),)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    author = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.Integer, nullable=True)
    student_id = db.Column(db.Integer, nullable=True)
    is_paid = db.Column(db.Boolean, default=False)
    payment_date = db.Column(db.DateTime, nullable=True)
    homework_id = db.Column(db.Integer, nullable=True)
    status_id = db.Column(db.Integer, nullable=True)
    task_type_id = db.Column(db.Integer, nullable=True)
    duration = db.Column(db.Integer, nullable=True)
    comment = db.Column(db.String(500), nullable=True)
    closing_date = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'created_at': self.created_at.strftime('%d.%m.%Y %H:%M') if self.created_at else None,
            'created_at_iso': self.created_at.strftime('%Y-%m-%dT%H:%M') if self.created_at else None,
            'start_date': self.start_date.strftime('%d.%m.%Y %H:%M') if self.start_date else None,
            'start_date_iso': self.start_date.strftime('%Y-%m-%dT%H:%M') if self.start_date else None,
            'end_date': self.end_date.strftime('%d.%m.%Y %H:%M') if self.end_date else None,
            'end_date_iso': self.end_date.strftime('%Y-%m-%dT%H:%M') if self.end_date else None,
            'author': self.author,
            'user_id': self.user_id,
            'student_id': self.student_id,
            'is_paid': self.is_paid,
            'payment_date': self.payment_date.strftime('%d.%m.%Y %H:%M') if self.payment_date else None,
            'payment_date_iso': self.payment_date.strftime('%Y-%m-%dT%H:%M') if self.payment_date else None,
            'homework_id': self.homework_id,
            'status_id': self.status_id,
            'task_type_id': self.task_type_id,
            'duration': self.duration,
            'comment': self.comment,
            'closing_date': self.closing_date.strftime('%d.%m.%Y %H:%M') if self.closing_date else None,
            'closing_date_iso': self.closing_date.strftime('%Y-%m-%dT%H:%M') if self.closing_date else None,
        }


class TaskStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    group = db.Column(db.String(100), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'group': self.group,
        }


class TaskType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
        }


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
        }


# ========== Helpers ==========

def parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M')
    except (ValueError, TypeError):
        return None


def user_has_role(*role_names):
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


# ========== Auth Routes ==========

@app.route('/login')
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/api/auth/login', methods=['POST'])
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


@app.route('/api/auth/logout', methods=['POST'])
@login_required
def auth_logout():
    logout_user()
    return jsonify({'ok': True})


@app.route('/api/auth/me', methods=['GET'])
@login_required
def auth_me():
    return jsonify(current_user.to_dict())


@app.route('/api/auth/change-password', methods=['POST'])
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

@app.route('/auth/yandex')
def auth_yandex():
    client_id = os.environ.get('YANDEX_CLIENT_ID')
    if not client_id:
        return 'Yandex OAuth не настроен', 500
    redirect_uri = url_for('auth_yandex_callback', _external=True)
    return redirect(f'https://oauth.yandex.com/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}')


@app.route('/auth/yandex/callback')
def auth_yandex_callback():
    code = request.args.get('code')
    if not code:
        return redirect(url_for('login_page'))

    client_id = os.environ.get('YANDEX_CLIENT_ID')
    client_secret = os.environ.get('YANDEX_CLIENT_SECRET')
    redirect_uri = url_for('auth_yandex_callback', _external=True)

    # Exchange code for token
    token_resp = http_requests.post('https://oauth.yandex.com/token', data={
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
    })
    if token_resp.status_code != 200:
        return redirect(url_for('login_page'))

    access_token = token_resp.json().get('access_token')

    # Get user info
    info_resp = http_requests.get('https://login.yandex.ru/info', headers={
        'Authorization': f'OAuth {access_token}'
    })
    if info_resp.status_code != 200:
        return redirect(url_for('login_page'))

    profile = info_resp.json()
    yandex_id = str(profile.get('id'))
    display_name = profile.get('display_name') or profile.get('real_name') or 'Пользователь Яндекс'

    # Find or create user
    user = User.query.filter_by(yandex_id=yandex_id).first()
    if not user:
        # Generate unique username
        base_username = f'yandex_{yandex_id}'
        user = User(
            username=base_username,
            display_name=display_name,
            yandex_id=yandex_id,
        )
        db.session.add(user)
        db.session.commit()
        # Assign default role: student
        student_role = Role.query.filter_by(name='student').first()
        if student_role:
            db.session.add(UserRole(user_id=user.id, role_id=student_role.id))
            db.session.commit()

    if not user.is_active:
        return redirect(url_for('login_page'))

    login_user(user, remember=True)
    return redirect(url_for('index'))


# ========== OAuth: VK ==========

@app.route('/auth/vk')
def auth_vk():
    client_id = os.environ.get('VK_CLIENT_ID')
    if not client_id:
        return 'VK OAuth не настроен', 500
    redirect_uri = url_for('auth_vk_callback', _external=True)
    return redirect(f'https://oauth.vk.com/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&v=5.131')


@app.route('/auth/vk/callback')
def auth_vk_callback():
    code = request.args.get('code')
    if not code:
        return redirect(url_for('login_page'))

    client_id = os.environ.get('VK_CLIENT_ID')
    client_secret = os.environ.get('VK_CLIENT_SECRET')
    redirect_uri = url_for('auth_vk_callback', _external=True)

    # Exchange code for token (VK returns user info with token)
    token_resp = http_requests.get('https://oauth.vk.com/access_token', params={
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'code': code,
    })
    if token_resp.status_code != 200:
        return redirect(url_for('login_page'))

    token_data = token_resp.json()
    if 'error' in token_data:
        return redirect(url_for('login_page'))

    vk_user_id = str(token_data.get('user_id'))
    access_token = token_data.get('access_token')

    # Get user profile for display name
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

    # Find or create user
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
        # Assign default role: student
        student_role = Role.query.filter_by(name='student').first()
        if student_role:
            db.session.add(UserRole(user_id=user.id, role_id=student_role.id))
            db.session.commit()

    if not user.is_active:
        return redirect(url_for('login_page'))

    login_user(user, remember=True)
    return redirect(url_for('index'))


# ========== Task Endpoints ==========

@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    page = request.args.get('page', 1, type=int)
    per_page = 50

    query = db.select(Task).order_by(Task.created_at.desc())
    # RBAC: non-admin/owner users see only their tasks; guest sees none
    if not user_has_role('admin', 'owner'):
        if user_has_role('teacher', 'student'):
            query = query.where(Task.user_id == current_user.id)
        else:
            # guest: no tasks visible
            return jsonify({
                'tasks': [], 'total': 0, 'pages': 0, 'current_page': 1, 'next_id': 1,
            })

    paginator = db.paginate(query, page=page, per_page=per_page, error_out=False)

    # Calculate next task ID
    max_id_result = db.session.execute(db.select(db.func.max(Task.id))).scalar()
    next_id = (max_id_result or 0) + 1

    # Batch lookup names for status_id, student_id, task_type_id
    status_ids = {t.status_id for t in paginator.items if t.status_id}
    student_ids = {t.student_id for t in paginator.items if t.student_id}
    type_ids = {t.task_type_id for t in paginator.items if t.task_type_id}
    status_map = {}
    student_map = {}
    type_map = {}
    if status_ids:
        status_map = {s.id: s.name for s in TaskStatus.query.filter(TaskStatus.id.in_(status_ids)).all()}
    if student_ids:
        student_map = {u.id: u.display_name for u in User.query.filter(User.id.in_(student_ids)).all()}
    if type_ids:
        type_map = {tt.id: tt.name for tt in TaskType.query.filter(TaskType.id.in_(type_ids)).all()}

    tasks = []
    for t in paginator.items:
        d = t.to_dict()
        d['status_name'] = status_map.get(t.status_id)
        d['student_name'] = student_map.get(t.student_id)
        d['task_type_name'] = type_map.get(t.task_type_id)
        tasks.append(d)

    return jsonify({
        'tasks': tasks,
        'total': paginator.total,
        'pages': paginator.pages,
        'current_page': paginator.page,
        'next_id': next_id,
    })


@app.route('/api/tasks', methods=['POST'])
@login_required
def add_task():
    data = request.get_json()
    description = (data.get('description') or '').strip()
    if len(description) > 100:
        return jsonify({'error': 'Описание: не более 100 символов'}), 400

    comment = (data.get('comment') or '').strip() or None
    if comment and len(comment) > 500:
        return jsonify({'error': 'Комментарий: не более 500 символов'}), 400

    task = Task(
        description=description,
        start_date=parse_datetime(data.get('start_date')),
        end_date=parse_datetime(data.get('end_date')),
        author=current_user.display_name,
        user_id=current_user.id,
        student_id=data.get('student_id'),
        is_paid=bool(data.get('is_paid', False)),
        payment_date=parse_datetime(data.get('payment_date')),
        homework_id=data.get('homework_id'),
        status_id=data.get('status_id'),
        task_type_id=data.get('task_type_id'),
        duration=data.get('duration'),
        comment=comment,
        closing_date=parse_datetime(data.get('closing_date')),
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    task = db.get_or_404(Task, task_id)

    # RBAC: non-admin/owner can only edit their own tasks
    if not user_has_role('admin', 'owner') and task.user_id != current_user.id:
        return jsonify({'error': 'Недостаточно прав'}), 403

    data = request.get_json()

    if 'description' in data:
        description = (data['description'] or '').strip()
        if len(description) > 100:
            return jsonify({'error': 'Описание: не более 100 символов'}), 400
        task.description = description
    if 'start_date' in data:
        task.start_date = parse_datetime(data['start_date'])
    if 'end_date' in data:
        task.end_date = parse_datetime(data['end_date'])
    if 'student_id' in data:
        task.student_id = data['student_id']
    if 'is_paid' in data:
        task.is_paid = bool(data['is_paid'])
    if 'payment_date' in data:
        task.payment_date = parse_datetime(data['payment_date'])
    if 'homework_id' in data:
        task.homework_id = data['homework_id']
    if 'status_id' in data:
        task.status_id = data['status_id']
    if 'task_type_id' in data:
        task.task_type_id = data['task_type_id']
    if 'duration' in data:
        task.duration = data['duration']
    if 'comment' in data:
        comment = (data['comment'] or '').strip() or None
        if comment and len(comment) > 500:
            return jsonify({'error': 'Комментарий: не более 500 символов'}), 400
        task.comment = comment
    if 'closing_date' in data:
        task.closing_date = parse_datetime(data['closing_date'])

    db.session.commit()
    return jsonify(task.to_dict())


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    task = db.get_or_404(Task, task_id)

    # RBAC: non-admin/owner can only delete their own tasks
    if not user_has_role('admin', 'owner') and task.user_id != current_user.id:
        return jsonify({'error': 'Недостаточно прав'}), 403

    db.session.delete(task)
    db.session.commit()
    return '', 204


# ========== Students Endpoint ==========

@app.route('/api/students/all', methods=['GET'])
@login_required
def get_all_students():
    """Return users with role 'student' for task form dropdown."""
    student_role = Role.query.filter_by(name='student').first()
    if not student_role:
        return jsonify({'students': []})
    student_user_ids = [ur.user_id for ur in UserRole.query.filter_by(role_id=student_role.id).all()]
    if not student_user_ids:
        return jsonify({'students': []})
    students = User.query.filter(
        User.id.in_(student_user_ids),
        User.is_active == True
    ).order_by(User.display_name).all()
    return jsonify({
        'students': [{'id': u.id, 'display_name': u.display_name} for u in students]
    })


# ========== Task Status Endpoints ==========

@app.route('/api/task-statuses', methods=['GET'])
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


@app.route('/api/task-statuses/all', methods=['GET'])
@login_required
def get_all_task_statuses():
    statuses = db.session.execute(
        db.select(TaskStatus).order_by(TaskStatus.name)
    ).scalars().all()
    return jsonify({'statuses': [s.to_dict() for s in statuses]})


@app.route('/api/task-statuses', methods=['POST'])
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


@app.route('/api/task-statuses/<int:status_id>', methods=['PUT'])
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


@app.route('/api/task-statuses/<int:status_id>', methods=['DELETE'])
@require_role('admin', 'owner')
def delete_task_status(status_id):
    status = db.get_or_404(TaskStatus, status_id)
    db.session.delete(status)
    db.session.commit()
    return '', 204


# ========== Task Type Endpoints ==========

@app.route('/api/task-types', methods=['GET'])
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


@app.route('/api/task-types/all', methods=['GET'])
@login_required
def get_all_task_types():
    task_types = db.session.execute(
        db.select(TaskType).order_by(TaskType.name)
    ).scalars().all()
    return jsonify({'task_types': [tt.to_dict() for tt in task_types]})


@app.route('/api/task-types', methods=['POST'])
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


@app.route('/api/task-types/<int:type_id>', methods=['PUT'])
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


@app.route('/api/task-types/<int:type_id>', methods=['DELETE'])
@require_role('admin', 'owner')
def delete_task_type(type_id):
    task_type = db.get_or_404(TaskType, type_id)
    db.session.delete(task_type)
    db.session.commit()
    return '', 204


# ========== Role Endpoints ==========

@app.route('/api/roles', methods=['GET'])
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


@app.route('/api/roles/all', methods=['GET'])
@login_required
def get_all_roles():
    roles = db.session.execute(
        db.select(Role).order_by(Role.name)
    ).scalars().all()
    return jsonify({'roles': [r.to_dict() for r in roles]})


@app.route('/api/roles', methods=['POST'])
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


@app.route('/api/roles/<int:role_id>', methods=['PUT'])
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


@app.route('/api/roles/<int:role_id>', methods=['DELETE'])
@require_role('admin', 'owner')
def delete_role(role_id):
    role = db.get_or_404(Role, role_id)
    db.session.delete(role)
    db.session.commit()
    return '', 204


# ========== User Management Endpoints ==========

@app.route('/api/users', methods=['GET'])
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


@app.route('/api/users', methods=['POST'])
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

    # Assign roles
    role_ids = data.get('role_ids', [])
    for role_id in role_ids:
        if Role.query.get(role_id):
            db.session.add(UserRole(user_id=user.id, role_id=role_id))
    db.session.commit()

    return jsonify(user.to_dict()), 201


@app.route('/api/users/<int:user_id>', methods=['PUT'])
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
        # Replace all roles
        UserRole.query.filter_by(user_id=user.id).delete()
        for role_id in data['role_ids']:
            if Role.query.get(role_id):
                db.session.add(UserRole(user_id=user.id, role_id=role_id))

    db.session.commit()
    return jsonify(user.to_dict())


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@require_role('admin', 'owner')
def delete_user(user_id):
    user = db.get_or_404(User, user_id)

    # Prevent deleting yourself
    if user.id == current_user.id:
        return jsonify({'error': 'Нельзя удалить свою учётную запись'}), 400

    UserRole.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    return '', 204


@app.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
@require_role('admin', 'owner')
def reset_user_password(user_id):
    user = db.get_or_404(User, user_id)
    new_password = secrets.token_urlsafe(8)
    user.set_password(new_password)
    db.session.commit()
    return jsonify({'new_password': new_password})


# ========== Database Initialization ==========

with app.app_context():
    db.create_all()
    # Add new columns to existing tables if they don't exist
    import sqlite3
    conn = sqlite3.connect(os.path.join(basedir, 'tasks.db'))
    cursor = conn.cursor()
    existing_columns = [col[1] for col in cursor.execute('PRAGMA table_info(task)').fetchall()]
    if 'start_date' not in existing_columns:
        cursor.execute('ALTER TABLE task ADD COLUMN start_date DATETIME')
    if 'end_date' not in existing_columns:
        cursor.execute('ALTER TABLE task ADD COLUMN end_date DATETIME')
    if 'task_type_id' not in existing_columns:
        cursor.execute('ALTER TABLE task ADD COLUMN task_type_id INTEGER')
    if 'duration' not in existing_columns:
        cursor.execute('ALTER TABLE task ADD COLUMN duration INTEGER')
    if 'user_id' not in existing_columns:
        cursor.execute('ALTER TABLE task ADD COLUMN user_id INTEGER')
    # Rename client_id → student_id
    if 'client_id' in existing_columns and 'student_id' not in existing_columns:
        cursor.execute('ALTER TABLE task RENAME COLUMN client_id TO student_id')
    elif 'student_id' not in existing_columns:
        cursor.execute('ALTER TABLE task ADD COLUMN student_id INTEGER')
    conn.commit()
    conn.close()

    # Seed task types if table is empty
    if TaskType.query.count() == 0:
        for name in ['Урок', 'Ошибка', 'Запрос на доработку']:
            db.session.add(TaskType(name=name))
        db.session.commit()

    # Seed roles if table is empty
    if Role.query.count() == 0:
        for name in ['admin', 'owner', 'teacher', 'student', 'guest']:
            db.session.add(Role(name=name))
        db.session.commit()

    # Seed admin user if no users exist
    if User.query.count() == 0:
        admin_user = User(
            username='admin',
            display_name='Администратор',
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role:
            db.session.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))
            db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
