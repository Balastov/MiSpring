from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__, template_folder='templates', static_folder='static')

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "tasks.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
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
            'author': self.author,
            'client_id': self.client_id,
            'is_paid': self.is_paid,
            'payment_date': self.payment_date.strftime('%d.%m.%Y %H:%M') if self.payment_date else None,
            'homework_id': self.homework_id,
            'status_id': self.status_id,
            'comment': self.comment,
            'closing_date': self.closing_date.strftime('%d.%m.%Y %H:%M') if self.closing_date else None,
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
    return jsonify({
        'tasks': [t.to_dict() for t in paginator.items],
        'total': paginator.total,
        'pages': paginator.pages,
        'current_page': paginator.page,
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


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
