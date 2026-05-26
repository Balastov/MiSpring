from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    password_plain = db.Column(db.String(255), nullable=True)
    display_name = db.Column(db.String(100), nullable=False)
    yandex_id = db.Column(db.String(100), unique=True, nullable=True)
    vk_id = db.Column(db.String(100), unique=True, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    timezone = db.Column(db.String(16), nullable=False, default='UTC+03:00')
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Telegram integration
    telegram_id = db.Column(db.String(50), unique=True, nullable=True)
    telegram_username = db.Column(db.String(100), nullable=True)
    telegram_code = db.Column(db.String(10), unique=True, nullable=True)
    telegram_notifications = db.Column(db.Boolean, default=True)

    # Calendar sync
    calendar_token = db.Column(db.String(64), unique=True, nullable=True)

    # Prepayment balance
    lesson_price = db.Column(db.Float, nullable=True)
    prepaid_lessons = db.Column(db.Integer, default=0, nullable=False)
    prepaid_since = db.Column(db.DateTime, nullable=True)

    # Teacher assignment (for students) and photo (for teachers)
    teacher_id = db.Column(db.Integer, nullable=True)
    teacher_photo = db.Column(db.String(200), nullable=True)

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
            'timezone': self.timezone or 'UTC+03:00',
            'created_at': self.created_at.strftime('%d.%m.%Y %H:%M') if self.created_at else None,
            'roles': self.get_roles(),
            'auth_source': self.get_auth_source(),
            'telegram_id': self.telegram_id,
            'telegram_username': self.telegram_username,
            'telegram_notifications': self.telegram_notifications,
            'lesson_price': self.lesson_price,
            'prepaid_lessons': self.prepaid_lessons or 0,
            'prepaid_since': self.prepaid_since.strftime('%d.%m.%Y') if self.prepaid_since else None,
            'prepaid_since_iso': self.prepaid_since.strftime('%Y-%m-%d') if self.prepaid_since else None,
            'teacher_id': self.teacher_id,
            'teacher_photo': self.teacher_photo,
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
    is_paid_manual = db.Column(db.Boolean, default=False, nullable=False)
    payment_date = db.Column(db.DateTime, nullable=True)
    homework_id = db.Column(db.Integer, nullable=True)
    homework_required = db.Column(db.Boolean, default=True)
    status_id = db.Column(db.Integer, nullable=True)
    task_type_id = db.Column(db.Integer, nullable=True)
    duration = db.Column(db.Integer, nullable=True)
    comment = db.Column(db.String(500), nullable=True)
    closing_date = db.Column(db.DateTime, nullable=True)
    student_confirmed = db.Column(db.Boolean, default=False)
    notified_24h = db.Column(db.Boolean, default=False)
    notified_1h = db.Column(db.Boolean, default=False)
    notified_chat_24h = db.Column(db.Boolean, default=False)
    notified_chat_30m = db.Column(db.Boolean, default=False)
    plan_step_id = db.Column(db.Integer, nullable=True)
    homework_submitted_at = db.Column(db.DateTime, nullable=True)
    homework_teacher_remarks = db.Column(db.Text, nullable=True)
    series_id = db.Column(db.Integer, nullable=True, index=True)
    series_index = db.Column(db.Integer, nullable=True)
    series_exception = db.Column(db.Boolean, default=False, nullable=False)
    homework_unique = db.Column(db.Boolean, default=False, nullable=False)
    homework_custom_text = db.Column(db.Text, nullable=True)

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
            'is_paid_manual': bool(self.is_paid_manual),
            'payment_date': self.payment_date.strftime('%d.%m.%Y %H:%M') if self.payment_date else None,
            'payment_date_iso': self.payment_date.strftime('%Y-%m-%dT%H:%M') if self.payment_date else None,
            'homework_id': self.homework_id,
            'homework_required': self.homework_required,
            'status_id': self.status_id,
            'task_type_id': self.task_type_id,
            'duration': self.duration,
            'comment': self.comment,
            'closing_date': self.closing_date.strftime('%d.%m.%Y %H:%M') if self.closing_date else None,
            'closing_date_iso': self.closing_date.strftime('%Y-%m-%dT%H:%M') if self.closing_date else None,
            'student_confirmed': self.student_confirmed,
            'plan_step_id': self.plan_step_id,
            'homework_submitted_at': self.homework_submitted_at.strftime('%d.%m.%Y %H:%M') if self.homework_submitted_at else None,
            'homework_submitted_at_iso': self.homework_submitted_at.strftime('%Y-%m-%dT%H:%M') if self.homework_submitted_at else None,
            'homework_teacher_remarks': self.homework_teacher_remarks,
            'series_id': self.series_id,
            'series_index': self.series_index,
            'series_exception': self.series_exception,
            'homework_unique': bool(self.homework_unique),
            'homework_custom_text': self.homework_custom_text,
        }


class LessonHomework(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, nullable=False, index=True)
    homework_id = db.Column(db.Integer, nullable=False, index=True)
    order_index = db.Column(db.Integer, nullable=False, default=0, index=True)
    due_date = db.Column(db.DateTime, nullable=True)
    status_id = db.Column(db.Integer, nullable=True, index=True)
    submitted_at = db.Column(db.DateTime, nullable=True)
    teacher_remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'homework_id': self.homework_id,
            'order_index': self.order_index,
            'due_date': self.due_date.strftime('%d.%m.%Y %H:%M') if self.due_date else None,
            'due_date_iso': self.due_date.strftime('%Y-%m-%dT%H:%M') if self.due_date else None,
            'status_id': self.status_id,
            'submitted_at': self.submitted_at.strftime('%d.%m.%Y %H:%M') if self.submitted_at else None,
            'submitted_at_iso': self.submitted_at.strftime('%Y-%m-%dT%H:%M') if self.submitted_at else None,
            'teacher_remarks': self.teacher_remarks,
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


class Homework(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    comment = db.Column(db.Text, nullable=True)
    catalog_id = db.Column(db.Integer, nullable=True)
    plan_step_id = db.Column(db.Integer, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'comment': self.comment,
            'catalog_id': self.catalog_id,
            'plan_step_id': self.plan_step_id,
        }


class HomeworkCatalog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    plan_template_id = db.Column(db.Integer, db.ForeignKey('plan_template.id'), nullable=True, unique=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'plan_template_id': self.plan_template_id,
        }


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
        }


class Setting(db.Model):
    """Глобальные настройки приложения (key-value)."""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)

    @staticmethod
    def get(key, default=None):
        row = Setting.query.filter_by(key=key).first()
        return row.value if row else default

    @staticmethod
    def set(key, value):
        from extensions import db as _db
        row = Setting.query.filter_by(key=key).first()
        if row:
            row.value = value
        else:
            _db.session.add(Setting(key=key, value=value))
        _db.session.commit()


class PlanTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('plan_template.id'), nullable=True)
    children = db.relationship(
        'PlanTemplate',
        backref=db.backref('parent', remote_side=[id]),
        cascade='all, delete-orphan',
        order_by='PlanTemplate.id'
    )
    steps = db.relationship('PlanStep', backref='template',
                            cascade='all, delete-orphan', order_by='PlanStep.order_num')

    def to_dict(self, include_children=True):
        data = {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'steps': [s.to_dict() for s in self.steps],
        }
        if include_children:
            data['children'] = [c.to_dict(include_children=False) for c in self.children]
        return data


class PlanStep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('plan_template.id'), nullable=False)
    order_num = db.Column(db.Integer, nullable=False, default=0)
    title = db.Column(db.String(300), nullable=False)

    def to_dict(self):
        return {'id': self.id, 'template_id': self.template_id,
                'order_num': self.order_num, 'title': self.title}


class UserPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    template_id = db.Column(db.Integer, db.ForeignKey('plan_template.id'), nullable=False)
    next_step_id = db.Column(db.Integer, nullable=True)


class LessonSeries(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_type_id = db.Column(db.Integer, db.ForeignKey('task_type.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    recurrence_rule = db.Column(db.String(200), nullable=True)
    occurrences_count = db.Column(db.Integer, nullable=True)
    first_homework_id = db.Column(db.Integer, db.ForeignKey('homework.id'), nullable=True)
    homework_required_default = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'teacher_id': self.teacher_id,
            'task_type_id': self.task_type_id,
            'start_date_iso': self.start_date.strftime('%Y-%m-%dT%H:%M') if self.start_date else None,
            'end_date_iso': self.end_date.strftime('%Y-%m-%dT%H:%M') if self.end_date else None,
            'recurrence_rule': self.recurrence_rule,
            'occurrences_count': self.occurrences_count,
            'first_homework_id': self.first_homework_id,
            'homework_required_default': self.homework_required_default,
            'created_at_iso': self.created_at.strftime('%Y-%m-%dT%H:%M') if self.created_at else None,
        }


class ChatDialog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_a_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    user_b_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)

    __table_args__ = (
        db.UniqueConstraint('user_a_id', 'user_b_id', name='uq_chat_dialog_pair'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_a_id': self.user_a_id,
            'user_b_id': self.user_b_id,
            'created_at_iso': self.created_at.strftime('%Y-%m-%dT%H:%M:%S') if self.created_at else None,
            'updated_at_iso': self.updated_at.strftime('%Y-%m-%dT%H:%M:%S') if self.updated_at else None,
        }


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dialog_id = db.Column(db.Integer, db.ForeignKey('chat_dialog.id'), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    # Подпись в UI (например «ИмяGPT» для напоминаний об уроках); если NULL — показывается display_name отправителя.
    sender_label = db.Column(db.String(120), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'dialog_id': self.dialog_id,
            'sender_id': self.sender_id,
            'text': self.text,
            'created_at_iso': self.created_at.strftime('%Y-%m-%dT%H:%M:%S') if self.created_at else None,
            'is_read': self.is_read,
            'sender_label': self.sender_label,
        }


class ChatPushSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    endpoint = db.Column(db.Text, nullable=False, unique=True)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)
    last_success_at = db.Column(db.DateTime, nullable=True)
    last_error = db.Column(db.String(255), nullable=True)
    last_error_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'endpoint': self.endpoint,
            'created_at_iso': self.created_at.strftime('%Y-%m-%dT%H:%M:%S') if self.created_at else None,
            'updated_at_iso': self.updated_at.strftime('%Y-%m-%dT%H:%M:%S') if self.updated_at else None,
        }


class HomeworkEvidence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, nullable=False, index=True)
    lesson_homework_id = db.Column(db.Integer, db.ForeignKey('lesson_homework.id'), nullable=True, index=True)
    student_id = db.Column(db.Integer, nullable=False, index=True)
    uploader_user_id = db.Column(db.Integer, nullable=True, index=True)
    uploader_role = db.Column(db.String(20), nullable=False, default='student', index=True)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False, unique=True)
    relative_path = db.Column(db.String(400), nullable=False)
    mime_type = db.Column(db.String(120), nullable=True)
    size_bytes = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'lesson_homework_id': self.lesson_homework_id,
            'student_id': self.student_id,
            'uploader_user_id': self.uploader_user_id,
            'uploader_role': self.uploader_role,
            'original_name': self.original_name,
            'mime_type': self.mime_type,
            'size_bytes': self.size_bytes,
            'created_at': self.created_at.strftime('%d.%m.%Y %H:%M') if self.created_at else None,
            'created_at_iso': self.created_at.strftime('%Y-%m-%dT%H:%M:%S') if self.created_at else None,
            'url': f'/static/{self.relative_path}',
        }


class StudentLessonPrice(db.Model):
    """История стоимости урока ученика. effective_from=NULL — начальная цена без даты."""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    price = db.Column(db.Float, nullable=False)
    effective_from = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'price': self.price,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_from_display': self.effective_from.strftime('%d.%m.%Y') if self.effective_from else None,
            'is_initial': self.effective_from is None,
            'created_at': self.created_at.strftime('%d.%m.%Y %H:%M') if self.created_at else None,
        }


class StudentPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lessons_count = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=True)
    payment_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    notes = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'lessons_count': self.lessons_count,
            'amount': self.amount,
            'payment_date': self.payment_date.strftime('%d.%m.%Y') if self.payment_date else None,
            'payment_date_iso': self.payment_date.strftime('%Y-%m-%d') if self.payment_date else None,
            'notes': self.notes,
            'created_at': self.created_at.strftime('%d.%m.%Y %H:%M') if self.created_at else None,
        }
