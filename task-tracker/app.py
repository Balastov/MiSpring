from flask import Flask, request, jsonify, render_template
import json
import os

app = Flask(__name__, template_folder='templates', static_folder='static')
DATA_FILE = 'task-tracker/data.json'

def read_tasks():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_tasks(tasks):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    tasks = read_tasks()
    return jsonify(tasks)

@app.route('/api/tasks', methods=['POST'])
def add_task():
    data = request.get_json()
    tasks = read_tasks()
    new_task = {'id': len(tasks) + 1, 'text': data['text'], 'done': False}
    tasks.append(new_task)
    write_tasks(tasks)
    return jsonify(new_task), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    tasks = read_tasks()
    for t in tasks:
        if t['id'] == task_id:
            t['done'] = not t['done']
            write_tasks(tasks)
            return jsonify(t)
    return jsonify({'error': 'Task not found'}), 404

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    tasks = read_tasks()
    tasks = [t for t in tasks if t['id'] != task_id]
    write_tasks(tasks)
    return '', 204

if __name__ == '__main__':
    app.run(debug=True)