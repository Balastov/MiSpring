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
    comment = db.Column(db.String(500), nullable=True)
    closing_date = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'created_at': self.created_at.strftime('%d.%m.%Y %H:%M') if self.created_at else None,
            'start_date': self.start_date.strftime('%d.%m.%Y %H:%M') if self.start_date else None,
            'end_date': self.end_date.strftime('%d.%m.%Y %H:%M') if self.end_date else None,
            'author': self.author,
            'client_id': self.client_id,
            'is_paid': self.is_paid,
            'payment_date': self.payment_date.strftime('%d.%m.%Y %H:%M') if self.payment_date else None,
            'homework_id': self.homework_id,
            'status_id': self.status_id,
            'comment': self.comment,
            'closing_date': self.closing_date.strftime('%d.%m.%Y %H:%M') if self.closing_date else None,
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

    return jsonify({
        'tasks': [t.to_dict() for t in paginator.items],
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

    return jsonify({
        'clients': [c.to_dict() for c in paginator.items],
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
    conn.commit()
    conn.close()

if __name__ == '__main__':
    app.run(debug=True)
