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

    // Settings elements
    const settingsBtn = document.getElementById('settings-btn');
    const settingsModal = document.getElementById('settings-modal');
    const settingsModalClose = document.getElementById('settings-modal-close');

    // Clients page elements
    const clientsPage = document.getElementById('clients-page');
    const backToMainBtn = document.getElementById('back-to-main-btn');
    const addClientBtn = document.getElementById('add-client-btn');
    const clientsTbody = document.getElementById('clients-tbody');
    const clientsPaginationInfo = document.getElementById('clients-pagination-info');
    const clientsPaginationControls = document.getElementById('clients-pagination-controls');

    // Client modal elements
    const clientModal = document.getElementById('client-modal');
    const clientModalTitle = document.getElementById('client-modal-title');
    const clientModalClose = document.getElementById('client-modal-close');
    const clientModalCancel = document.getElementById('client-modal-cancel');
    const clientForm = document.getElementById('client-form');
    const formClientIdDisplay = document.getElementById('form-client-id-display');
    const formClientName = document.getElementById('form-client-name');
    const formClientStatusId = document.getElementById('form-client-status-id');
    const clientSubmitBtn = document.getElementById('client-submit-btn');

    // Placeholder modal
    const placeholderModal = document.getElementById('placeholder-modal');
    const placeholderModalTitle = document.getElementById('placeholder-modal-title');
    const placeholderModalClose = document.getElementById('placeholder-modal-close');

    let currentPage = 1;
    let isListVisible = false;
    let currentClientsPage = 1;
    let editingClientId = null;

    // Open modal and auto-fill fields
    addTaskBtn.addEventListener('click', () => {
        // Fetch next task ID from API
        fetch('/api/tasks?page=1')
            .then(r => r.json())
            .then(data => {
                // Use next_id from API response
                formId.value = data.next_id;

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

                // Fetch and populate client dropdown
                return fetch('/api/clients/all');
            })
            .then(r => r.json())
            .then(clientData => {
                formClientId.innerHTML = '<option value="">-- Выберите клиента --</option>';
                clientData.clients.forEach(client => {
                    const option = document.createElement('option');
                    option.value = client.id;
                    option.textContent = `${client.id} - ${client.name}`;
                    formClientId.appendChild(option);
                });

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
        if (!description) {
            alert('Описание обязательно для заполнения');
            return;
        }

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
        })
        .then(r => {
            if (r.ok) {
                return r.json();
            } else {
                return r.json().then(err => {
                    throw new Error(err.error || 'Ошибка при создании задачи');
                });
            }
        })
        .then(() => {
            // Close modal
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
        })
        .catch(err => {
            alert(err.message || 'Ошибка при создании задачи');
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

    // ========== Settings Modal Logic ==========

    // Open settings modal
    settingsBtn.addEventListener('click', () => {
        settingsModal.classList.remove('hidden');
    });

    // Close settings modal
    settingsModalClose.addEventListener('click', () => {
        settingsModal.classList.add('hidden');
    });

    settingsModal.addEventListener('click', (e) => {
        if (e.target === settingsModal) settingsModal.classList.add('hidden');
    });

    // Handle settings options
    document.querySelectorAll('.settings-option-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const option = e.target.dataset.option;
            settingsModal.classList.add('hidden');

            if (option === 'clients') {
                showClientsPage();
            } else if (option === 'statuses') {
                showPlaceholder('Статусы');
            } else if (option === 'homework') {
                showPlaceholder('Домашки');
            }
        });
    });

    // ========== Placeholder Modal ==========

    function showPlaceholder(title) {
        placeholderModalTitle.textContent = title;
        placeholderModal.classList.remove('hidden');
    }

    placeholderModalClose.addEventListener('click', () => {
        placeholderModal.classList.add('hidden');
    });

    placeholderModal.addEventListener('click', (e) => {
        if (e.target === placeholderModal) placeholderModal.classList.add('hidden');
    });

    // ========== Page Navigation ==========

    function showClientsPage() {
        document.querySelector('.container').classList.add('hidden');
        clientsPage.classList.remove('hidden');
        currentClientsPage = 1;
        fetchClients();
    }

    backToMainBtn.addEventListener('click', () => {
        clientsPage.classList.add('hidden');
        document.querySelector('.container').classList.remove('hidden');
    });

    // ========== Clients CRUD Logic ==========

    // Fetch paginated clients
    function fetchClients(page) {
        if (page !== undefined) currentClientsPage = page;
        fetch(`/api/clients?page=${currentClientsPage}`)
            .then(r => r.json())
            .then(data => {
                renderClients(data.clients);
                renderClientsPagination(data);
            });
    }

    // Render clients table
    function renderClients(clients) {
        clientsTbody.innerHTML = '';
        if (clients.length === 0) {
            clientsTbody.innerHTML = '<tr><td colspan="6" class="empty-msg">Клиентов нет</td></tr>';
            return;
        }
        clients.forEach(client => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${client.id}</td>
                <td>${escapeHtml(client.name)}</td>
                <td>${client.status_id ?? '—'}</td>
                <td>${client.created_at || '—'}</td>
                <td><button class="btn-edit" data-id="${client.id}">Изменить</button></td>
                <td><button class="btn-delete" data-id="${client.id}">Удалить</button></td>
            `;
            clientsTbody.appendChild(tr);
        });
    }

    // Render pagination for clients
    function renderClientsPagination(data) {
        clientsPaginationControls.innerHTML = '';

        if (data.total === 0) {
            clientsPaginationInfo.textContent = '';
            return;
        }

        clientsPaginationInfo.textContent = `Страница ${data.current_page} из ${data.pages} (всего ${data.total} клиентов)`;

        if (data.current_page > 1) {
            addClientPageBtn('← Пред', data.current_page - 1);
        }

        const start = Math.max(1, data.current_page - 2);
        const end = Math.min(data.pages, data.current_page + 2);
        for (let i = start; i <= end; i++) {
            addClientPageBtn(String(i), i, i === data.current_page);
        }

        if (data.current_page < data.pages) {
            addClientPageBtn('След →', data.current_page + 1);
        }
    }

    function addClientPageBtn(label, page, isActive = false) {
        const btn = document.createElement('button');
        btn.className = 'btn-page' + (isActive ? ' active' : '');
        btn.textContent = label;
        btn.addEventListener('click', () => fetchClients(page));
        clientsPaginationControls.appendChild(btn);
    }

    // ========== Client Modal Logic ==========

    // Open client modal for adding
    addClientBtn.addEventListener('click', () => {
        fetch('/api/clients?page=1')
            .then(r => r.json())
            .then(data => {
                editingClientId = null;
                clientModalTitle.textContent = 'Создание клиента';
                clientSubmitBtn.textContent = 'Подтвердить и создать';
                formClientIdDisplay.value = data.next_id;
                formClientName.value = '';
                formClientStatusId.value = '';
                clientModal.classList.remove('hidden');
            })
            .catch(() => {
                formClientIdDisplay.value = 'Авто';
                clientModal.classList.remove('hidden');
            });
    });

    // Close client modal
    function closeClientModal() {
        clientModal.classList.add('hidden');
        clientForm.reset();
        editingClientId = null;
    }

    clientModalClose.addEventListener('click', closeClientModal);
    clientModalCancel.addEventListener('click', closeClientModal);

    clientModal.addEventListener('click', (e) => {
        if (e.target === clientModal) closeClientModal();
    });

    // Submit client form
    clientForm.addEventListener('submit', (e) => {
        e.preventDefault();

        const name = formClientName.value.trim();
        if (!name) {
            alert('Имя обязательно для заполнения');
            return;
        }

        const clientData = {
            name: name,
            status_id: formClientStatusId.value ? parseInt(formClientStatusId.value) : null,
        };

        const method = editingClientId ? 'PUT' : 'POST';
        const url = editingClientId ? `/api/clients/${editingClientId}` : '/api/clients';

        fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(clientData)
        })
        .then(r => {
            if (r.ok) {
                return r.json();
            } else {
                return r.json().then(err => {
                    throw new Error(err.error || 'Ошибка при сохранении клиента');
                });
            }
        })
        .then(() => {
            closeClientModal();
            fetchClients(currentClientsPage);
        })
        .catch(err => {
            alert(err.message || 'Ошибка при сохранении клиента');
        });
    });

    // Edit and delete client (event delegation)
    clientsTbody.addEventListener('click', (e) => {
        const editBtn = e.target.closest('.btn-edit');
        const deleteBtn = e.target.closest('.btn-delete');

        if (editBtn) {
            const id = parseInt(editBtn.dataset.id);
            fetch(`/api/clients?page=${currentClientsPage}`)
                .then(r => r.json())
                .then(data => {
                    const client = data.clients.find(c => c.id === id);
                    if (!client) {
                        alert('Клиент не найден');
                        return;
                    }
                    editingClientId = client.id;
                    clientModalTitle.textContent = 'Изменение клиента';
                    clientSubmitBtn.textContent = 'Подтвердить изменения';
                    formClientIdDisplay.value = client.id;
                    formClientName.value = client.name;
                    formClientStatusId.value = client.status_id || '';
                    clientModal.classList.remove('hidden');
                });
        }

        if (deleteBtn) {
            if (!confirm('Удалить этого клиента?')) return;
            const id = deleteBtn.dataset.id;
            fetch(`/api/clients/${id}`, { method: 'DELETE' })
                .then(() => fetchClients(currentClientsPage));
        }
    });
});
