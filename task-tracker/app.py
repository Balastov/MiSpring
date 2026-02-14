from flask import Flask, request, jsonify, redirect, url_for, render_template
from flask_login import login_required
import os
import sqlite3

from dotenv import load_dotenv
load_dotenv()

from extensions import db, login_manager

app = Flask(__name__, template_folder='templates', static_folder='static')

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.environ.get('DATABASE_PATH', os.path.join(basedir, 'tasks.db'))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login_page'

from models import User, UserRole, Role, TaskType


# ========== Flask-Login Callbacks ==========

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Требуется авторизация'}), 401
    return redirect(url_for('auth.login_page'))


# ========== Context Processor ==========

@app.context_processor
def inject_cache_bust():
    def cache_bust(filename):
        static_path = os.path.join(app.static_folder, filename)
        if os.path.exists(static_path):
            mtime = os.path.getmtime(static_path)
            return int(mtime)
        return None
    return dict(cache_bust=cache_bust)


# ========== Main Route ==========

@app.route('/')
@login_required
def index():
    return render_template('index.html')


# ========== Register Blueprints ==========

from auth import auth_bp
from routes_tasks import tasks_bp
from routes_references import references_bp
from routes_users import users_bp
from routes_telegram import telegram_bp

app.register_blueprint(auth_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(references_bp)
app.register_blueprint(users_bp)
app.register_blueprint(telegram_bp)


# ========== Database Initialization ==========

with app.app_context():
    db.create_all()

    conn = sqlite3.connect(db_path)
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
    # Переименует client_id в student_id, если такого столбца нет, но есть client_id
    if 'client_id' in existing_columns and 'student_id' not in existing_columns:
        cursor.execute('ALTER TABLE task RENAME COLUMN client_id TO student_id')
    elif 'student_id' not in existing_columns:
        cursor.execute('ALTER TABLE task ADD COLUMN student_id INTEGER')
    conn.commit()
    conn.close()

    # Запилит типы задач, если их нет
    if TaskType.query.count() == 0:
        for name in ['Урок', 'Ошибка', 'Запрос на доработку']:
            db.session.add(TaskType(name=name))
        db.session.commit()

    # Запилит роли, если их нет
    if Role.query.count() == 0:
        for name in ['admin', 'owner', 'teacher', 'student', 'guest']:
            db.session.add(Role(name=name))
        db.session.commit()

    # Запилит учётку одмина, если юзеров нет. И выдаст ей роль админа
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
