document.addEventListener('DOMContentLoaded', () => {
    const taskForm = document.getElementById('task-form');
    const taskInput = document.getElementById('task-input');
    const taskList = document.getElementById('task-list');

    let tasks = JSON.parse(localStorage.getItem('tasks')) || [];

    function renderTasks() {
        taskList.innerHTML = '';
        tasks.forEach((task, index) => {
            const li = document.createElement('li');
            li.className = 'task-item';
            li.innerHTML = `
                <span>${task.text}</span>
                <div>
                    <input type="checkbox" ${task.done ? 'checked' : ''} onchange="toggleDone(${index})">
                    <button onclick="deleteTask(${index})">Удалить</button>
                </div>
            `;
            taskList.appendChild(li);
        });
    }

    window.toggleDone = (index) => {
        tasks[index].done = !tasks[index].done;
        saveTasks();
        renderTasks();
    };

    window.deleteTask = (index) => {
        tasks.splice(index, 1);
        saveTasks();
        renderTasks();
    };

    taskForm.addEventListener('submit', (e) => {
        e.preventDefault();
        if (!taskInput.value.trim()) return;

        tasks.push({
            text: taskInput.value,
            done: false
        });

        saveTasks();
        renderTasks();

        taskInput.value = '';
    });

    function saveTasks() {
        localStorage.setItem('tasks', JSON.stringify(tasks));
    }

    renderTasks();
});