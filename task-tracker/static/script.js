document.addEventListener('DOMContentLoaded', () => {
    const taskForm = document.getElementById('task-form');
    const taskInput = document.getElementById('task-input');
    const taskList = document.getElementById('task-list');

    function fetchTasks() {
        fetch('/api/tasks')
            .then(response => response.json())
            .then(renderTasks);
    }

    function renderTasks(tasks) {
        taskList.innerHTML = '';
        tasks.forEach(task => {
            const li = document.createElement('li');
            li.className = 'task-item';
            li.innerHTML = `
                <span>${task.text}</span>
                <div>
                    <input type="checkbox" ${task.done ? 'checked' : ''}
                        onchange="toggleTask(${task.id})">
                    <button onclick="deleteTask(${task.id})">Удалить</button>
                </div>
            `;
            taskList.appendChild(li);
        });
    }

    window.toggleTask = (id) => {
        fetch(`/api/tasks/${id}`, { method: 'PUT' })
            .then(fetchTasks);
    };

    window.deleteTask = (id) => {
        fetch(`/api/tasks/${id}`, { method: 'DELETE' })
            .then(fetchTasks);
    };

    taskForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = taskInput.value.trim();
        if (!text) return;

        fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        }).then(fetchTasks);

        taskInput.value = '';
    });

    fetchTasks();
});