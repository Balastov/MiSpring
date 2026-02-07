from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import hashlib
import os

app = Flask(__name__, template_folder='templates', static_folder='static')

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "tasks.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

@app.context_processor
def inject_cache_bust():
    def cache_bust(filename):
        # Возвращаем только timestamp для использования с url_for
        static_path = os.path.join(app.static_folder, filename)
        if os.path.exists(static_path):
            mtime = os.path.getmtime(static_path)
            return int(mtime)
        return None
    return dict(cache_bust=cache_bust)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    author = db.Column(db.String(100), nullable=True)
    client_id = db.Column(db.Integer, nullable=True)
    is_paid = db.Column(db.Boolean, default=False)
    payment_date = db.Column(db.DateTime, nullable=True)
    homework_id = db.Column(db.Integer, nullable=True)
    status_id = db.Column(db.Integer, nullable=True)
    task_type_id = db.Column(db.Integer, nullable=True)
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
            'client_id': self.client_id,
            'is_paid': self.is_paid,
            'payment_date': self.payment_date.strftime('%d.%m.%Y %H:%M') if self.payment_date else None,
            'payment_date_iso': self.payment_date.strftime('%Y-%m-%dT%H:%M') if self.payment_date else None,
            'homework_id': self.homework_id,
            'status_id': self.status_id,
            'task_type_id': self.task_type_id,
            'comment': self.comment,
            'closing_date': self.closing_date.strftime('%d.%m.%Y %H:%M') if self.closing_date else None,
            'closing_date_iso': self.closing_date.strftime('%Y-%m-%dT%H:%M') if self.closing_date else None,
        }


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    status_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'status_id': self.status_id,
            'created_at': self.created_at.strftime('%d.%m.%Y %H:%M') if self.created_at else None,
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


class ClientStatus(db.Model):
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


def parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M')
    except (ValueError, TypeError):
        return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    paginator = db.paginate(
        db.select(Task).order_by(Task.created_at.desc()),
        page=page, per_page=per_page, error_out=False
    )

    # Calculate next task ID
    max_id_result = db.session.execute(db.select(db.func.max(Task.id))).scalar()
    next_id = (max_id_result or 0) + 1

    # Batch lookup names for status_id, client_id, task_type_id
    status_ids = {t.status_id for t in paginator.items if t.status_id}
    client_ids = {t.client_id for t in paginator.items if t.client_id}
    type_ids = {t.task_type_id for t in paginator.items if t.task_type_id}
    status_map = {}
    client_map = {}
    type_map = {}
    if status_ids:
        status_map = {s.id: s.name for s in TaskStatus.query.filter(TaskStatus.id.in_(status_ids)).all()}
    if client_ids:
        client_map = {c.id: c.name for c in Client.query.filter(Client.id.in_(client_ids)).all()}
    if type_ids:
        type_map = {tt.id: tt.name for tt in TaskType.query.filter(TaskType.id.in_(type_ids)).all()}

    tasks = []
    for t in paginator.items:
        d = t.to_dict()
        d['status_name'] = status_map.get(t.status_id)
        d['client_name'] = client_map.get(t.client_id)
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
def add_task():
    data = request.get_json()
    description = (data.get('description') or '').strip()
    if not description or len(description) > 100:
        return jsonify({'error': 'Описание: от 1 до 100 символов'}), 400

    comment = (data.get('comment') or '').strip() or None
    if comment and len(comment) > 500:
        return jsonify({'error': 'Комментарий: не более 500 символов'}), 400

    task = Task(
        description=description,
        start_date=parse_datetime(data.get('start_date')),
        end_date=parse_datetime(data.get('end_date')),
        author=data.get('author'),
        client_id=data.get('client_id'),
        is_paid=bool(data.get('is_paid', False)),
        payment_date=parse_datetime(data.get('payment_date')),
        homework_id=data.get('homework_id'),
        status_id=data.get('status_id'),
        task_type_id=data.get('task_type_id'),
        comment=comment,
        closing_date=parse_datetime(data.get('closing_date')),
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = db.get_or_404(Task, task_id)
    data = request.get_json()

    if 'description' in data:
        description = (data['description'] or '').strip()
        if not description or len(description) > 100:
            return jsonify({'error': 'Описание: от 1 до 100 символов'}), 400
        task.description = description
    if 'start_date' in data:
        task.start_date = parse_datetime(data['start_date'])
    if 'end_date' in data:
        task.end_date = parse_datetime(data['end_date'])
    if 'author' in data:
        task.author = data['author']
    if 'client_id' in data:
        task.client_id = data['client_id']
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
def delete_task(task_id):
    task = db.get_or_404(Task, task_id)
    db.session.delete(task)
    db.session.commit()
    return '', 204


@app.route('/api/clients', methods=['GET'])
def get_clients():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    paginator = db.paginate(
        db.select(Client).order_by(Client.created_at.desc()),
        page=page, per_page=per_page, error_out=False
    )

    # Calculate next client ID
    max_id_result = db.session.execute(db.select(db.func.max(Client.id))).scalar()
    next_id = (max_id_result or 0) + 1

    # Batch lookup client status names
    status_ids = {c.status_id for c in paginator.items if c.status_id}
    status_map = {}
    if status_ids:
        status_map = {s.id: s.name for s in ClientStatus.query.filter(ClientStatus.id.in_(status_ids)).all()}

    clients = []
    for c in paginator.items:
        d = c.to_dict()
        d['status_name'] = status_map.get(c.status_id)
        clients.append(d)

    return jsonify({
        'clients': clients,
        'total': paginator.total,
        'pages': paginator.pages,
        'current_page': paginator.page,
        'next_id': next_id,
    })


@app.route('/api/clients/all', methods=['GET'])
def get_all_clients():
    clients = db.session.execute(
        db.select(Client).order_by(Client.name)
    ).scalars().all()
    return jsonify({
        'clients': [c.to_dict() for c in clients]
    })


@app.route('/api/clients', methods=['POST'])
def add_client():
    data = request.get_json()
    name = (data.get('name') or '').strip()
    if not name or len(name) > 100:
        return jsonify({'error': 'Имя: от 1 до 100 символов'}), 400

    client = Client(
        name=name,
        status_id=data.get('status_id'),
    )
    db.session.add(client)
    db.session.commit()
    return jsonify(client.to_dict()), 201


@app.route('/api/clients/<int:client_id>', methods=['PUT'])
def update_client(client_id):
    client = db.get_or_404(Client, client_id)
    data = request.get_json()

    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name or len(name) > 100:
            return jsonify({'error': 'Имя: от 1 до 100 символов'}), 400
        client.name = name
    if 'status_id' in data:
        client.status_id = data['status_id']

    db.session.commit()
    return jsonify(client.to_dict())


@app.route('/api/clients/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    client = db.get_or_404(Client, client_id)
    db.session.delete(client)
    db.session.commit()
    return '', 204


# ========== Task Status Endpoints ==========

@app.route('/api/task-statuses', methods=['GET'])
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
def get_all_task_statuses():
    statuses = db.session.execute(
        db.select(TaskStatus).order_by(TaskStatus.name)
    ).scalars().all()
    return jsonify({'statuses': [s.to_dict() for s in statuses]})


@app.route('/api/task-statuses', methods=['POST'])
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
def delete_task_status(status_id):
    status = db.get_or_404(TaskStatus, status_id)
    db.session.delete(status)
    db.session.commit()
    return '', 204


# ========== Client Status Endpoints ==========

@app.route('/api/client-statuses', methods=['GET'])
def get_client_statuses():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    paginator = db.paginate(
        db.select(ClientStatus).order_by(ClientStatus.id),
        page=page, per_page=per_page, error_out=False
    )
    max_id_result = db.session.execute(db.select(db.func.max(ClientStatus.id))).scalar()
    next_id = (max_id_result or 0) + 1
    return jsonify({
        'statuses': [s.to_dict() for s in paginator.items],
        'total': paginator.total,
        'pages': paginator.pages,
        'current_page': paginator.page,
        'next_id': next_id,
    })


@app.route('/api/client-statuses/all', methods=['GET'])
def get_all_client_statuses():
    statuses = db.session.execute(
        db.select(ClientStatus).order_by(ClientStatus.name)
    ).scalars().all()
    return jsonify({'statuses': [s.to_dict() for s in statuses]})


@app.route('/api/client-statuses', methods=['POST'])
def add_client_status():
    data = request.get_json()
    name = (data.get('name') or '').strip()
    if not name or len(name) > 100:
        return jsonify({'error': 'Имя: от 1 до 100 символов'}), 400
    status = ClientStatus(
        name=name,
        group=(data.get('group') or '').strip() or None,
    )
    db.session.add(status)
    db.session.commit()
    return jsonify(status.to_dict()), 201


@app.route('/api/client-statuses/<int:status_id>', methods=['PUT'])
def update_client_status(status_id):
    status = db.get_or_404(ClientStatus, status_id)
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


@app.route('/api/client-statuses/<int:status_id>', methods=['DELETE'])
def delete_client_status(status_id):
    status = db.get_or_404(ClientStatus, status_id)
    db.session.delete(status)
    db.session.commit()
    return '', 204


# ========== Task Type Endpoints ==========

@app.route('/api/task-types', methods=['GET'])
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
def get_all_task_types():
    task_types = db.session.execute(
        db.select(TaskType).order_by(TaskType.name)
    ).scalars().all()
    return jsonify({'task_types': [tt.to_dict() for tt in task_types]})


@app.route('/api/task-types', methods=['POST'])
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
def delete_task_type(type_id):
    task_type = db.get_or_404(TaskType, type_id)
    db.session.delete(task_type)
    db.session.commit()
    return '', 204


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
    conn.commit()
    conn.close()

    # Seed task types if table is empty
    if TaskType.query.count() == 0:
        for name in ['Урок', 'Ошибка', 'Запрос на доработку']:
            db.session.add(TaskType(name=name))
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
