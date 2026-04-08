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
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login_page'

from models import User, UserRole, Role, TaskType, StudentPayment, Setting, PlanTemplate, PlanStep, UserPlan, Task, Homework, HomeworkCatalog


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


# ========== Main Routes ==========

@app.route('/')
@login_required
def index():
    from helpers import user_has_role
    if user_has_role('student') and not user_has_role('admin', 'owner', 'teacher'):
        return redirect(url_for('student_dashboard'))
    return render_template('index.html')


@app.route('/student')
@login_required
def student_dashboard():
    from helpers import user_has_role
    if not user_has_role('student') or user_has_role('admin', 'owner', 'teacher'):
        return redirect(url_for('index'))
    return render_template('student_dashboard.html')


# ========== Register Blueprints ==========

from auth import auth_bp
from routes_tasks import tasks_bp
from routes_references import references_bp
from routes_users import users_bp
from routes_telegram import telegram_bp
from routes_payments import payments_bp
from routes_calendar import calendar_bp
from routes_plans import plans_bp

app.register_blueprint(auth_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(references_bp)
app.register_blueprint(users_bp)
app.register_blueprint(telegram_bp)
app.register_blueprint(payments_bp)
app.register_blueprint(calendar_bp)
app.register_blueprint(plans_bp)


# ========== Database Initialization ==========

with app.app_context():
    db.create_all()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Миграция таблицы user
    user_columns = [col[1] for col in cursor.execute('PRAGMA table_info(user)').fetchall()]
    if 'lesson_price' not in user_columns:
        cursor.execute('ALTER TABLE user ADD COLUMN lesson_price REAL')
    if 'prepaid_lessons' not in user_columns:
        cursor.execute('ALTER TABLE user ADD COLUMN prepaid_lessons INTEGER DEFAULT 0')
    if 'prepaid_since' not in user_columns:
        cursor.execute('ALTER TABLE user ADD COLUMN prepaid_since DATETIME')
    if 'calendar_token' not in user_columns:
        cursor.execute('ALTER TABLE user ADD COLUMN calendar_token VARCHAR(64)')
    if 'teacher_id' not in user_columns:
        cursor.execute('ALTER TABLE user ADD COLUMN teacher_id INTEGER')
    if 'teacher_photo' not in user_columns:
        cursor.execute('ALTER TABLE user ADD COLUMN teacher_photo VARCHAR(200)')
    conn.commit()

    # Создаём папку для фото учителей
    import os as _os
    uploads_dir = _os.path.join(_os.path.dirname(db_path), 'static', 'uploads', 'teacher_photos')
    _os.makedirs(uploads_dir, exist_ok=True)

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
    if 'notified_24h' not in existing_columns:
        cursor.execute('ALTER TABLE task ADD COLUMN notified_24h BOOLEAN DEFAULT 0')
    if 'notified_1h' not in existing_columns:
        cursor.execute('ALTER TABLE task ADD COLUMN notified_1h BOOLEAN DEFAULT 0')
    if 'plan_step_id' not in existing_columns:
        cursor.execute('ALTER TABLE task ADD COLUMN plan_step_id INTEGER')
    conn.commit()

    up_cols = [col[1] for col in cursor.execute('PRAGMA table_info(user_plan)').fetchall()]
    if 'next_step_id' not in up_cols:
        cursor.execute('ALTER TABLE user_plan ADD COLUMN next_step_id INTEGER')
        conn.commit()

    # Миграция таблицы setting (создаётся через db.create_all, но на всякий случай)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='setting'")
    if not cursor.fetchone():
        cursor.execute('CREATE TABLE setting (id INTEGER PRIMARY KEY, key VARCHAR(100) UNIQUE NOT NULL, value TEXT)')
        conn.commit()

    # Таблицы плана обучения
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='plan_template'")
    if not cursor.fetchone():
        cursor.execute('CREATE TABLE plan_template (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)')
        conn.commit()
    pt_cols = [col[1] for col in cursor.execute('PRAGMA table_info(plan_template)').fetchall()]
    if 'parent_id' not in pt_cols:
        cursor.execute('ALTER TABLE plan_template ADD COLUMN parent_id INTEGER')
        conn.commit()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='plan_step'")
    if not cursor.fetchone():
        cursor.execute('''CREATE TABLE plan_step (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL REFERENCES plan_template(id),
            order_num INTEGER NOT NULL DEFAULT 0,
            title TEXT NOT NULL)''')
        conn.commit()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_plan'")
    if not cursor.fetchone():
        cursor.execute('''CREATE TABLE user_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL UNIQUE REFERENCES user(id),
            template_id INTEGER NOT NULL REFERENCES plan_template(id))''')
        conn.commit()

    homework_cols = [col[1] for col in cursor.execute('PRAGMA table_info(homework)').fetchall()]
    if 'catalog_id' not in homework_cols:
        cursor.execute('ALTER TABLE homework ADD COLUMN catalog_id INTEGER')
        conn.commit()
    if 'plan_step_id' not in homework_cols:
        cursor.execute('ALTER TABLE homework ADD COLUMN plan_step_id INTEGER')
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

    # Справочники домашних заданий: создаём базовый, если отсутствует.
    if HomeworkCatalog.query.count() == 0:
        db.session.add(HomeworkCatalog(name='Основной справочник'))
        db.session.commit()
    default_catalog = HomeworkCatalog.query.order_by(HomeworkCatalog.id).first()
    if default_catalog:
        Homework.query.filter(Homework.catalog_id.is_(None)).update(
            {Homework.catalog_id: default_catalog.id},
            synchronize_session=False
        )
        db.session.commit()

    # Двухуровневые планы обучения:
    # если планов ещё нет, создаём стартовый 1-й уровень.
    # Дальше 1-й уровень полностью управляется из интерфейса
    # (можно добавлять, менять и удалять без авто-восстановления).
    if PlanTemplate.query.count() == 0:
        for root_name in ['EF', 'Hang Out', 'USMLE', 'ОГЭ']:
            db.session.add(PlanTemplate(name=root_name, parent_id=None))
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

# ========== Lesson Reminder Scheduler ==========

from notifications import start_scheduler
start_scheduler(app)


if __name__ == '__main__':
    app.run(debug=True)
