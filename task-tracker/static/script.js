document.addEventListener('DOMContentLoaded', () => {
    // Main elements
    const addTaskBtn = document.getElementById('add-task-btn');
    const allTasksBtn = document.getElementById('all-tasks-btn');
    const taskListSection = document.getElementById('task-list-section');
    const tasksTbody = document.getElementById('tasks-tbody');
    const paginationInfo = document.getElementById('pagination-info');
    const paginationControls = document.getElementById('pagination-controls');

    // Modal elements
    const modal = document.getElementById('task-modal');
    const modalClose = document.getElementById('modal-close');
    const modalCancel = document.getElementById('modal-cancel');
    const taskForm = document.getElementById('task-form');

    // Form fields
    const formId = document.getElementById('form-id');
    const formDescription = document.getElementById('form-description');
    const formCreatedAt = document.getElementById('form-created-at');
    const formAuthor = document.getElementById('form-author');
    const formClientId = document.getElementById('form-client-id');
    const formIsPaid = document.getElementById('form-is-paid');
    const formPaymentDate = document.getElementById('form-payment-date');
    const formHomeworkId = document.getElementById('form-homework-id');
    const formStatusId = document.getElementById('form-status-id');
    const formComment = document.getElementById('form-comment');
    const formClosingDate = document.getElementById('form-closing-date');

    let currentPage = 1;
    let isListVisible = false;

    // Open modal and auto-fill fields
    addTaskBtn.addEventListener('click', () => {
        // Fetch total task count to determine next ID
        fetch('/api/tasks?page=1')
            .then(r => r.json())
            .then(data => {
                const nextId = data.total + 1;
                formId.value = nextId;

                // Auto-fill current datetime
                const now = new Date();
                const localDateTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
                    .toISOString()
                    .slice(0, 16);
                formCreatedAt.value = localDateTime;

                // Set default status to 1 ("Created")
                formStatusId.value = '1';

                // Set default author
                formAuthor.value = 'Система';

                // Clear other fields
                formDescription.value = '';
                formClientId.value = '';
                formIsPaid.checked = false;
                formPaymentDate.value = '';
                formHomeworkId.value = '';
                formComment.value = '';
                formClosingDate.value = '';

                modal.classList.remove('hidden');
            })
            .catch(() => {
                // If fetch fails, still open modal with "Авто"
                formId.value = 'Авто';
                modal.classList.remove('hidden');
            });
    });

    // Close modal
    function closeModal() {
        modal.classList.add('hidden');
        taskForm.reset();
    }

    modalClose.addEventListener('click', closeModal);
    modalCancel.addEventListener('click', closeModal);

    // Close modal on outside click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    // Toggle task list
    allTasksBtn.addEventListener('click', () => {
        isListVisible = !isListVisible;
        taskListSection.classList.toggle('hidden', !isListVisible);
        allTasksBtn.textContent = isListVisible ? 'Все задачи ▲' : 'Все задачи ▼';
        if (isListVisible) {
            currentPage = 1;
            fetchTasks();
        }
    });

    // Fetch paginated tasks
    function fetchTasks(page) {
        if (page !== undefined) currentPage = page;
        fetch(`/api/tasks?page=${currentPage}`)
            .then(r => r.json())
            .then(data => {
                renderTasks(data.tasks);
                renderPagination(data);
            });
    }

    // Render table body
    function renderTasks(tasks) {
        tasksTbody.innerHTML = '';
        if (tasks.length === 0) {
            tasksTbody.innerHTML = '<tr><td colspan="12" class="empty-msg">Задач нет</td></tr>';
            return;
        }
        tasks.forEach(task => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${task.id}</td>
                <td class="col-desc" title="${escapeAttr(task.description)}">${escapeHtml(task.description)}</td>
                <td>${task.created_at || '—'}</td>
                <td>${escapeHtml(task.author || '—')}</td>
                <td>${task.client_id ?? '—'}</td>
                <td class="cell-bool">${task.is_paid ? '✓' : '✗'}</td>
                <td>${task.payment_date || '—'}</td>
                <td>${task.homework_id ?? '—'}</td>
                <td>${task.status_id ?? '—'}</td>
                <td class="col-comment" title="${escapeAttr(task.comment || '')}">${escapeHtml(task.comment || '—')}</td>
                <td>${task.closing_date || '—'}</td>
                <td><button class="btn-delete" data-id="${task.id}">Удалить</button></td>
            `;
            tasksTbody.appendChild(tr);
        });
    }

    // Render pagination controls
    function renderPagination(data) {
        paginationControls.innerHTML = '';

        if (data.total === 0) {
            paginationInfo.textContent = '';
            return;
        }

        paginationInfo.textContent = `Страница ${data.current_page} из ${data.pages} (всего ${data.total} задач)`;

        if (data.current_page > 1) {
            addPageBtn('← Пред', data.current_page - 1);
        }

        const start = Math.max(1, data.current_page - 2);
        const end = Math.min(data.pages, data.current_page + 2);
        for (let i = start; i <= end; i++) {
            addPageBtn(String(i), i, i === data.current_page);
        }

        if (data.current_page < data.pages) {
            addPageBtn('След →', data.current_page + 1);
        }
    }

    function addPageBtn(label, page, isActive = false) {
        const btn = document.createElement('button');
        btn.className = 'btn-page' + (isActive ? ' active' : '');
        btn.textContent = label;
        btn.addEventListener('click', () => fetchTasks(page));
        paginationControls.appendChild(btn);
    }

    // Submit task form
    taskForm.addEventListener('submit', (e) => {
        e.preventDefault();

        const description = formDescription.value.trim();
        if (!description) return;

        // Collect form data
        const taskData = {
            description: description,
            author: formAuthor.value.trim() || null,
            client_id: formClientId.value ? parseInt(formClientId.value) : null,
            is_paid: formIsPaid.checked,
            payment_date: formPaymentDate.value || null,
            homework_id: formHomeworkId.value ? parseInt(formHomeworkId.value) : null,
            status_id: formStatusId.value ? parseInt(formStatusId.value) : null,
            comment: formComment.value.trim() || null,
            closing_date: formClosingDate.value || null
        };

        fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(taskData)
        }).then(r => {
            if (r.ok) {
                closeModal();
                // Auto-open "All tasks" list if not visible
                if (!isListVisible) {
                    isListVisible = true;
                    taskListSection.classList.remove('hidden');
                    allTasksBtn.textContent = 'Все задачи ▲';
                }
                // Refresh list to page 1 to show new task
                currentPage = 1;
                fetchTasks(1);
            } else {
                r.json().then(err => alert(err.error || 'Ошибка при создании задачи'));
            }
        });
    });

    // Delete task (event delegation)
    tasksTbody.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn-delete');
        if (!btn) return;
        if (!confirm('Удалить эту задачу?')) return;
        const id = btn.dataset.id;
        fetch(`/api/tasks/${id}`, { method: 'DELETE' })
            .then(() => { if (isListVisible) fetchTasks(); });
    });

    // Escape for HTML content
    function escapeHtml(str) {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(String(str)));
        return div.innerHTML;
    }

    // Escape for HTML attribute values
    function escapeAttr(str) {
        return escapeHtml(str).replace(/"/g, '&quot;');
    }
});
