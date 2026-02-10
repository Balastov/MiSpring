from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from extensions import db


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


class Homework(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    comment = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'comment': self.comment,
        }


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
        }
