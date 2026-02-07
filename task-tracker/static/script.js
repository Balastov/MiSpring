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

    // Task modal title and submit button
    const taskModalTitle = document.getElementById('task-modal-title');
    const taskSubmitBtn = document.getElementById('task-submit-btn');

    // Form fields
    const formId = document.getElementById('form-id');
    const formDescription = document.getElementById('form-description');
    const formCreatedAt = document.getElementById('form-created-at');
    const formStartDate = document.getElementById('form-start-date');
    const formEndDate = document.getElementById('form-end-date');
    const formAuthor = document.getElementById('form-author');
    const formClientId = document.getElementById('form-client-id');
    const formIsPaid = document.getElementById('form-is-paid');
    const formPaymentDate = document.getElementById('form-payment-date');
    const formHomeworkId = document.getElementById('form-homework-id');
    const formStatusId = document.getElementById('form-status-id');
    const formTaskTypeId = document.getElementById('form-task-type-id');
    const formDuration = document.getElementById('form-duration');
    const formComment = document.getElementById('form-comment');
    const formClosingDate = document.getElementById('form-closing-date');

    // Task types page elements
    const taskTypesPage = document.getElementById('task-types-page');
    const backToMainFromTaskTypesBtn = document.getElementById('back-to-main-from-task-types-btn');
    const addTaskTypeBtn = document.getElementById('add-task-type-btn');
    const taskTypesTbody = document.getElementById('task-types-tbody');
    const taskTypesPaginationInfo = document.getElementById('task-types-pagination-info');
    const taskTypesPaginationControls = document.getElementById('task-types-pagination-controls');

    // Task type modal elements
    const taskTypeModal = document.getElementById('task-type-modal');
    const taskTypeModalTitle = document.getElementById('task-type-modal-title');
    const taskTypeModalClose = document.getElementById('task-type-modal-close');
    const taskTypeModalCancel = document.getElementById('task-type-modal-cancel');
    const taskTypeForm = document.getElementById('task-type-form');
    const formTaskTypeIdDisplay = document.getElementById('form-task-type-id-display');
    const formTaskTypeName = document.getElementById('form-task-type-name');
    const taskTypeSubmitBtn = document.getElementById('task-type-submit-btn');

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

    // Statuses page elements
    const statusesPage = document.getElementById('statuses-page');
    const backToMainFromStatusesBtn = document.getElementById('back-to-main-from-statuses-btn');
    const addStatusBtn = document.getElementById('add-status-btn');
    const taskStatusesTbody = document.getElementById('task-statuses-tbody');
    const taskStatusesPaginationInfo = document.getElementById('task-statuses-pagination-info');
    const taskStatusesPaginationControls = document.getElementById('task-statuses-pagination-controls');
    const clientStatusesTbody = document.getElementById('client-statuses-tbody');
    const clientStatusesPaginationInfo = document.getElementById('client-statuses-pagination-info');
    const clientStatusesPaginationControls = document.getElementById('client-statuses-pagination-controls');

    // Status modal elements
    const statusModal = document.getElementById('status-modal');
    const statusModalTitle = document.getElementById('status-modal-title');
    const statusModalClose = document.getElementById('status-modal-close');
    const statusModalCancel = document.getElementById('status-modal-cancel');
    const statusForm = document.getElementById('status-form');
    const formStatusIdDisplay = document.getElementById('form-status-id-display');
    const formStatusName = document.getElementById('form-status-name');
    const formStatusGroup = document.getElementById('form-status-group');
    const statusSubmitBtn = document.getElementById('status-submit-btn');

    let currentPage = 1;
    let isListVisible = false;
    let currentClientsPage = 1;
    let editingTaskId = null;
    let editingClientId = null;
    let currentTaskStatusesPage = 1;
    let currentClientStatusesPage = 1;
    let currentStatusType = 'task'; // 'task' or 'client'
    let editingStatusId = null;
    let currentTaskTypesPage = 1;
    let editingTaskTypeId = null;

    // Duration display helper
    function formatDuration(minutes) {
        if (!minutes) return '—';
        if (minutes === 30) return '30 мин';
        if (minutes === 60) return '1 час';
        if (minutes === 90) return '1 час 30 мин';
        if (minutes === 120) return '2 часа';
        return minutes + ' мин';
    }

    // Recalculate end_date from start_date + duration
    function recalcEndDate() {
        if (formStartDate.value && formDuration.value) {
            const start = new Date(formStartDate.value);
            start.setMinutes(start.getMinutes() + parseInt(formDuration.value));
            const iso = new Date(start.getTime() - start.getTimezoneOffset() * 60000)
                .toISOString().slice(0, 16);
            formEndDate.value = iso;
        } else {
            formEndDate.value = '';
        }
    }

    // Enable/disable duration based on start_date
    function updateDurationState() {
        if (formStartDate.value) {
            formDuration.disabled = false;
        } else {
            formDuration.disabled = true;
            formDuration.value = '';
            formEndDate.value = '';
        }
    }

    formStartDate.addEventListener('change', () => {
        updateDurationState();
        recalcEndDate();
    });

    formDuration.addEventListener('change', () => {
        recalcEndDate();
    });

    // Open modal and auto-fill fields
    addTaskBtn.addEventListener('click', () => {
        editingTaskId = null;
        taskModalTitle.textContent = 'Создание задачи';
        taskSubmitBtn.textContent = 'Подтвердить и создать';

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

                // Set default author
                formAuthor.value = 'Система';

                // Clear other fields
                if (formDescription) formDescription.value = '';
                formStartDate.value = '';
                formDuration.value = '';
                formDuration.disabled = true;
                formEndDate.value = '';
                formClientId.value = '';
                formStatusId.value = '';
                formTaskTypeId.value = '';
                formIsPaid.checked = false;
                formPaymentDate.value = '';
                formHomeworkId.value = '';
                formComment.value = '';
                formClosingDate.value = '';

                // Fetch and populate client, status, and task type dropdowns
                return Promise.all([
                    fetch('/api/clients/all').then(r => r.json()),
                    fetch('/api/task-statuses/all').then(r => r.json()),
                    fetch('/api/task-types/all').then(r => r.json())
                ]);
            })
            .then(([clientData, statusData, typeData]) => {
                formClientId.innerHTML = '<option value="">-- Выберите клиента --</option>';
                clientData.clients.forEach(client => {
                    const option = document.createElement('option');
                    option.value = client.id;
                    option.textContent = `${client.id} - ${client.name}`;
                    formClientId.appendChild(option);
                });

                formStatusId.innerHTML = '<option value="">-- Выберите статус --</option>';
                statusData.statuses.forEach(status => {
                    const option = document.createElement('option');
                    option.value = status.id;
                    option.textContent = status.name;
                    formStatusId.appendChild(option);
                });

                formTaskTypeId.innerHTML = '<option value="">-- Выберите тип --</option>';
                typeData.task_types.forEach(tt => {
                    const option = document.createElement('option');
                    option.value = tt.id;
                    option.textContent = tt.name;
                    formTaskTypeId.appendChild(option);
                });
                // Default to "Урок"
                const lessonType = typeData.task_types.find(tt => tt.name === 'Урок');
                if (lessonType) formTaskTypeId.value = lessonType.id;

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
        editingTaskId = null;
    }

    modalClose.addEventListener('click', closeModal);
    modalCancel.addEventListener('click', closeModal);

    // Auto-fill payment date when "is paid" checkbox changes
    formIsPaid.addEventListener('change', () => {
        if (formIsPaid.checked) {
            const now = new Date();
            formPaymentDate.value = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
                .toISOString().slice(0, 16);
        } else {
            formPaymentDate.value = '';
            formPaymentDate.defaultValue = '';
        }
    });

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
            tasksTbody.innerHTML = '<tr><td colspan="16" class="empty-msg">Задач нет</td></tr>';
            return;
        }
        tasks.forEach(task => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${task.id}</td>
                <td>${escapeHtml(task.client_name || '—')}</td>
                <td>${escapeHtml(task.task_type_name || '—')}</td>
                <!-- <td class="col-desc" title="${escapeAttr(task.description)}">${escapeHtml(task.description)}</td> -->
                <td>${task.created_at || '—'}</td>
                <td>${task.start_date || '—'}</td>
                <td>${task.end_date || '—'}</td>
                <td>${formatDuration(task.duration)}</td>
                <td>${escapeHtml(task.author || '—')}</td>
                <td class="cell-bool">${task.is_paid ? '✓' : '✗'}</td>
                <td>${task.payment_date || '—'}</td>
                <td>${task.homework_id ?? '—'}</td>
                <td>${escapeHtml(task.status_name || '—')}</td>
                <td class="col-comment" title="${escapeAttr(task.comment || '')}">${escapeHtml(task.comment || '—')}</td>
                <td>${task.closing_date || '—'}</td>
                <td><button class="btn-edit" data-id="${task.id}">Изменить</button></td>
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

        // Validate required fields
        if (!formClientId.value) {
            alert('Клиент обязателен для заполнения');
            return;
        }
        if (!formTaskTypeId.value) {
            alert('Тип задачи обязателен для заполнения');
            return;
        }
        if (!formStartDate.value) {
            alert('Дата начала обязательна для заполнения');
            return;
        }

        // Duration is required when task type is "Урок"
        const selectedTypeOption = formTaskTypeId.options[formTaskTypeId.selectedIndex];
        if (selectedTypeOption && selectedTypeOption.textContent === 'Урок' && !formDuration.value) {
            alert('Продолжительность обязательна для типа задачи "Урок"');
            return;
        }

        // Collect form data
        const taskData = {
            description: formDescription ? formDescription.value.trim() : '',
            start_date: formStartDate.value || null,
            end_date: formEndDate.value || null,
            duration: formDuration.value ? parseInt(formDuration.value) : null,
            author: formAuthor.value.trim() || null,
            client_id: formClientId.value ? parseInt(formClientId.value) : null,
            is_paid: formIsPaid.checked,
            payment_date: formPaymentDate.value || null,
            homework_id: formHomeworkId.value ? parseInt(formHomeworkId.value) : null,
            status_id: formStatusId.value ? parseInt(formStatusId.value) : null,
            task_type_id: formTaskTypeId.value ? parseInt(formTaskTypeId.value) : null,
            comment: formComment.value.trim() || null,
            closing_date: formClosingDate.value || null
        };

        const isEditing = !!editingTaskId;
        const method = isEditing ? 'PUT' : 'POST';
        const url = isEditing ? `/api/tasks/${editingTaskId}` : '/api/tasks';

        fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(taskData)
        })
        .then(r => {
            if (r.ok) {
                return r.json();
            } else {
                return r.json().then(err => {
                    throw new Error(err.error || 'Ошибка при сохранении задачи');
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

            // Refresh list - stay on current page when editing, go to page 1 for new
            if (!isEditing) {
                currentPage = 1;
            }
            fetchTasks(currentPage);
        })
        .catch(err => {
            alert(err.message || 'Ошибка при сохранении задачи');
        });
    });

    // Edit and delete task (event delegation)
    tasksTbody.addEventListener('click', (e) => {
        const editBtn = e.target.closest('.btn-edit');
        const deleteBtn = e.target.closest('.btn-delete');

        if (editBtn) {
            const id = parseInt(editBtn.dataset.id);
            Promise.all([
                fetch(`/api/tasks?page=${currentPage}`).then(r => r.json()),
                fetch('/api/clients/all').then(r => r.json()),
                fetch('/api/task-statuses/all').then(r => r.json()),
                fetch('/api/task-types/all').then(r => r.json())
            ])
                .then(([data, clientData, statusData, typeData]) => {
                    const task = data.tasks.find(t => t.id === id);
                    if (!task) {
                        alert('Задача не найдена');
                        return;
                    }
                    editingTaskId = task.id;
                    taskModalTitle.textContent = 'Редактирование задачи';
                    taskSubmitBtn.textContent = 'Подтвердить изменения';

                    formId.value = task.id;
                    if (formDescription) formDescription.value = task.description || '';
                    formCreatedAt.value = task.created_at_iso || '';
                    formStartDate.value = task.start_date_iso || '';
                    formDuration.value = task.duration || '';
                    updateDurationState();
                    formEndDate.value = task.end_date_iso || '';
                    formAuthor.value = task.author || '';
                    formIsPaid.checked = task.is_paid || false;
                    formPaymentDate.value = task.payment_date_iso || '';
                    formHomeworkId.value = task.homework_id ?? '';
                    formComment.value = task.comment || '';
                    formClosingDate.value = task.closing_date_iso || '';

                    // Populate client dropdown
                    formClientId.innerHTML = '<option value="">-- Выберите клиента --</option>';
                    clientData.clients.forEach(client => {
                        const option = document.createElement('option');
                        option.value = client.id;
                        option.textContent = `${client.id} - ${client.name}`;
                        formClientId.appendChild(option);
                    });
                    formClientId.value = task.client_id || '';

                    // Populate status dropdown
                    formStatusId.innerHTML = '<option value="">-- Выберите статус --</option>';
                    statusData.statuses.forEach(status => {
                        const option = document.createElement('option');
                        option.value = status.id;
                        option.textContent = status.name;
                        formStatusId.appendChild(option);
                    });
                    formStatusId.value = task.status_id || '';

                    // Populate task type dropdown
                    formTaskTypeId.innerHTML = '<option value="">-- Выберите тип --</option>';
                    typeData.task_types.forEach(tt => {
                        const option = document.createElement('option');
                        option.value = tt.id;
                        option.textContent = tt.name;
                        formTaskTypeId.appendChild(option);
                    });
                    formTaskTypeId.value = task.task_type_id || '';

                    modal.classList.remove('hidden');
                });
        }

        if (deleteBtn) {
            if (!confirm('Удалить эту задачу?')) return;
            const id = deleteBtn.dataset.id;
            fetch(`/api/tasks/${id}`, { method: 'DELETE' })
                .then(() => { if (isListVisible) fetchTasks(); });
        }
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
                showStatusesPage();
            } else if (option === 'task-types') {
                showTaskTypesPage();
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
                <td>${escapeHtml(client.status_name || '—')}</td>
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
        Promise.all([
            fetch('/api/clients?page=1').then(r => r.json()),
            fetch('/api/client-statuses/all').then(r => r.json())
        ])
            .then(([data, statusData]) => {
                editingClientId = null;
                clientModalTitle.textContent = 'Создание клиента';
                clientSubmitBtn.textContent = 'Подтвердить и создать';
                formClientIdDisplay.value = data.next_id;
                formClientName.value = '';

                // Populate client status dropdown
                formClientStatusId.innerHTML = '<option value="">-- Выберите статус --</option>';
                statusData.statuses.forEach(status => {
                    const option = document.createElement('option');
                    option.value = status.id;
                    option.textContent = status.name;
                    formClientStatusId.appendChild(option);
                });
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
            Promise.all([
                fetch(`/api/clients?page=${currentClientsPage}`).then(r => r.json()),
                fetch('/api/client-statuses/all').then(r => r.json())
            ])
                .then(([data, statusData]) => {
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

                    // Populate client status dropdown
                    formClientStatusId.innerHTML = '<option value="">-- Выберите статус --</option>';
                    statusData.statuses.forEach(status => {
                        const option = document.createElement('option');
                        option.value = status.id;
                        option.textContent = status.name;
                        formClientStatusId.appendChild(option);
                    });
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

    // ========== Statuses Page Logic ==========

    function showStatusesPage() {
        document.querySelector('.container').classList.add('hidden');
        statusesPage.classList.remove('hidden');
        currentTaskStatusesPage = 1;
        currentClientStatusesPage = 1;
        fetchTaskStatuses();
    }

    backToMainFromStatusesBtn.addEventListener('click', () => {
        statusesPage.classList.add('hidden');
        document.querySelector('.container').classList.remove('hidden');
    });

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');

            const tab = e.target.dataset.tab;
            document.getElementById('task-statuses-tab').classList.toggle('hidden', tab !== 'task-statuses');
            document.getElementById('client-statuses-tab').classList.toggle('hidden', tab !== 'client-statuses');

            if (tab === 'task-statuses') {
                currentStatusType = 'task';
                fetchTaskStatuses();
            } else {
                currentStatusType = 'client';
                fetchClientStatuses();
            }
        });
    });

    // Fetch task statuses
    function fetchTaskStatuses(page) {
        if (page !== undefined) currentTaskStatusesPage = page;
        fetch(`/api/task-statuses?page=${currentTaskStatusesPage}`)
            .then(r => r.json())
            .then(data => {
                renderStatuses(data.statuses, taskStatusesTbody);
                renderStatusesPagination(data, taskStatusesPaginationInfo, taskStatusesPaginationControls, fetchTaskStatuses);
            });
    }

    // Fetch client statuses
    function fetchClientStatuses(page) {
        if (page !== undefined) currentClientStatusesPage = page;
        fetch(`/api/client-statuses?page=${currentClientStatusesPage}`)
            .then(r => r.json())
            .then(data => {
                renderStatuses(data.statuses, clientStatusesTbody);
                renderStatusesPagination(data, clientStatusesPaginationInfo, clientStatusesPaginationControls, fetchClientStatuses);
            });
    }

    // Shared render for both status types
    function renderStatuses(statuses, tbody) {
        tbody.innerHTML = '';
        if (statuses.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-msg">Статусов нет</td></tr>';
            return;
        }
        statuses.forEach(status => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${status.id}</td>
                <td>${escapeHtml(status.name)}</td>
                <td>${escapeHtml(status.group || '—')}</td>
                <td><button class="btn-edit" data-id="${status.id}">Изменить</button></td>
                <td><button class="btn-delete" data-id="${status.id}">Удалить</button></td>
            `;
            tbody.appendChild(tr);
        });
    }

    // Shared pagination for statuses
    function renderStatusesPagination(data, infoEl, controlsEl, fetchFn) {
        controlsEl.innerHTML = '';
        if (data.total === 0) {
            infoEl.textContent = '';
            return;
        }
        infoEl.textContent = `Страница ${data.current_page} из ${data.pages} (всего ${data.total} статусов)`;

        if (data.current_page > 1) {
            addStatusPageBtn('← Пред', data.current_page - 1, controlsEl, fetchFn);
        }
        const start = Math.max(1, data.current_page - 2);
        const end = Math.min(data.pages, data.current_page + 2);
        for (let i = start; i <= end; i++) {
            addStatusPageBtn(String(i), i, controlsEl, fetchFn, i === data.current_page);
        }
        if (data.current_page < data.pages) {
            addStatusPageBtn('След →', data.current_page + 1, controlsEl, fetchFn);
        }
    }

    function addStatusPageBtn(label, page, controlsEl, fetchFn, isActive = false) {
        const btn = document.createElement('button');
        btn.className = 'btn-page' + (isActive ? ' active' : '');
        btn.textContent = label;
        btn.addEventListener('click', () => fetchFn(page));
        controlsEl.appendChild(btn);
    }

    // ========== Status Modal Logic ==========

    addStatusBtn.addEventListener('click', () => {
        const apiUrl = currentStatusType === 'task' ? '/api/task-statuses?page=1' : '/api/client-statuses?page=1';
        fetch(apiUrl)
            .then(r => r.json())
            .then(data => {
                editingStatusId = null;
                statusModalTitle.textContent = currentStatusType === 'task' ? 'Создание статуса задачи' : 'Создание статуса клиента';
                statusSubmitBtn.textContent = 'Подтвердить и создать';
                formStatusIdDisplay.value = data.next_id;
                formStatusName.value = '';
                formStatusGroup.value = '';
                statusModal.classList.remove('hidden');
            });
    });

    function closeStatusModal() {
        statusModal.classList.add('hidden');
        statusForm.reset();
        editingStatusId = null;
    }

    statusModalClose.addEventListener('click', closeStatusModal);
    statusModalCancel.addEventListener('click', closeStatusModal);
    statusModal.addEventListener('click', (e) => {
        if (e.target === statusModal) closeStatusModal();
    });

    // Submit status form
    statusForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const name = formStatusName.value.trim();
        if (!name) {
            alert('Имя обязательно для заполнения');
            return;
        }

        const statusData = {
            name: name,
            group: formStatusGroup.value.trim() || null,
        };

        const baseUrl = currentStatusType === 'task' ? '/api/task-statuses' : '/api/client-statuses';
        const method = editingStatusId ? 'PUT' : 'POST';
        const url = editingStatusId ? `${baseUrl}/${editingStatusId}` : baseUrl;

        fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(statusData)
        })
        .then(r => {
            if (r.ok) return r.json();
            return r.json().then(err => { throw new Error(err.error || 'Ошибка'); });
        })
        .then(() => {
            closeStatusModal();
            if (currentStatusType === 'task') fetchTaskStatuses(currentTaskStatusesPage);
            else fetchClientStatuses(currentClientStatusesPage);
        })
        .catch(err => alert(err.message));
    });

    // Edit/delete task statuses (event delegation)
    taskStatusesTbody.addEventListener('click', (e) => {
        handleStatusTableClick(e, 'task', '/api/task-statuses', currentTaskStatusesPage, fetchTaskStatuses);
    });

    // Edit/delete client statuses (event delegation)
    clientStatusesTbody.addEventListener('click', (e) => {
        handleStatusTableClick(e, 'client', '/api/client-statuses', currentClientStatusesPage, fetchClientStatuses);
    });

    // ========== Task Types Page Logic ==========

    function showTaskTypesPage() {
        document.querySelector('.container').classList.add('hidden');
        taskTypesPage.classList.remove('hidden');
        currentTaskTypesPage = 1;
        fetchTaskTypes();
    }

    backToMainFromTaskTypesBtn.addEventListener('click', () => {
        taskTypesPage.classList.add('hidden');
        document.querySelector('.container').classList.remove('hidden');
    });

    function fetchTaskTypes(page) {
        if (page !== undefined) currentTaskTypesPage = page;
        fetch(`/api/task-types?page=${currentTaskTypesPage}`)
            .then(r => r.json())
            .then(data => {
                renderTaskTypes(data.task_types);
                renderTaskTypesPagination(data);
            });
    }

    function renderTaskTypes(taskTypes) {
        taskTypesTbody.innerHTML = '';
        if (taskTypes.length === 0) {
            taskTypesTbody.innerHTML = '<tr><td colspan="4" class="empty-msg">Типов задач нет</td></tr>';
            return;
        }
        taskTypes.forEach(tt => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${tt.id}</td>
                <td>${escapeHtml(tt.name)}</td>
                <td><button class="btn-edit" data-id="${tt.id}">Изменить</button></td>
                <td><button class="btn-delete" data-id="${tt.id}">Удалить</button></td>
            `;
            taskTypesTbody.appendChild(tr);
        });
    }

    function renderTaskTypesPagination(data) {
        taskTypesPaginationControls.innerHTML = '';
        if (data.total === 0) {
            taskTypesPaginationInfo.textContent = '';
            return;
        }
        taskTypesPaginationInfo.textContent = `Страница ${data.current_page} из ${data.pages} (всего ${data.total} типов)`;
        if (data.current_page > 1) {
            addTaskTypePageBtn('← Пред', data.current_page - 1);
        }
        const start = Math.max(1, data.current_page - 2);
        const end = Math.min(data.pages, data.current_page + 2);
        for (let i = start; i <= end; i++) {
            addTaskTypePageBtn(String(i), i, i === data.current_page);
        }
        if (data.current_page < data.pages) {
            addTaskTypePageBtn('След →', data.current_page + 1);
        }
    }

    function addTaskTypePageBtn(label, page, isActive = false) {
        const btn = document.createElement('button');
        btn.className = 'btn-page' + (isActive ? ' active' : '');
        btn.textContent = label;
        btn.addEventListener('click', () => fetchTaskTypes(page));
        taskTypesPaginationControls.appendChild(btn);
    }

    // ========== Task Type Modal Logic ==========

    addTaskTypeBtn.addEventListener('click', () => {
        fetch('/api/task-types?page=1')
            .then(r => r.json())
            .then(data => {
                editingTaskTypeId = null;
                taskTypeModalTitle.textContent = 'Создание типа задачи';
                taskTypeSubmitBtn.textContent = 'Подтвердить и создать';
                formTaskTypeIdDisplay.value = data.next_id;
                formTaskTypeName.value = '';
                taskTypeModal.classList.remove('hidden');
            });
    });

    function closeTaskTypeModal() {
        taskTypeModal.classList.add('hidden');
        taskTypeForm.reset();
        editingTaskTypeId = null;
    }

    taskTypeModalClose.addEventListener('click', closeTaskTypeModal);
    taskTypeModalCancel.addEventListener('click', closeTaskTypeModal);
    taskTypeModal.addEventListener('click', (e) => {
        if (e.target === taskTypeModal) closeTaskTypeModal();
    });

    taskTypeForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const name = formTaskTypeName.value.trim();
        if (!name) {
            alert('Наименование обязательно для заполнения');
            return;
        }

        const method = editingTaskTypeId ? 'PUT' : 'POST';
        const url = editingTaskTypeId ? `/api/task-types/${editingTaskTypeId}` : '/api/task-types';

        fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name })
        })
        .then(r => {
            if (r.ok) return r.json();
            return r.json().then(err => { throw new Error(err.error || 'Ошибка'); });
        })
        .then(() => {
            closeTaskTypeModal();
            fetchTaskTypes(currentTaskTypesPage);
        })
        .catch(err => alert(err.message));
    });

    // Edit/delete task types (event delegation)
    taskTypesTbody.addEventListener('click', (e) => {
        const editBtn = e.target.closest('.btn-edit');
        const deleteBtn = e.target.closest('.btn-delete');

        if (editBtn) {
            const id = parseInt(editBtn.dataset.id);
            fetch(`/api/task-types?page=${currentTaskTypesPage}`)
                .then(r => r.json())
                .then(data => {
                    const tt = data.task_types.find(t => t.id === id);
                    if (!tt) { alert('Тип задачи не найден'); return; }
                    editingTaskTypeId = tt.id;
                    taskTypeModalTitle.textContent = 'Изменение типа задачи';
                    taskTypeSubmitBtn.textContent = 'Подтвердить изменения';
                    formTaskTypeIdDisplay.value = tt.id;
                    formTaskTypeName.value = tt.name;
                    taskTypeModal.classList.remove('hidden');
                });
        }

        if (deleteBtn) {
            if (!confirm('Удалить этот тип задачи?')) return;
            const id = deleteBtn.dataset.id;
            fetch(`/api/task-types/${id}`, { method: 'DELETE' })
                .then(() => fetchTaskTypes(currentTaskTypesPage));
        }
    });

    function handleStatusTableClick(e, type, apiBase, currentPageVal, fetchFn) {
        const editBtn = e.target.closest('.btn-edit');
        const deleteBtn = e.target.closest('.btn-delete');

        if (editBtn) {
            const id = parseInt(editBtn.dataset.id);
            fetch(`${apiBase}?page=${currentPageVal}`)
                .then(r => r.json())
                .then(data => {
                    const status = data.statuses.find(s => s.id === id);
                    if (!status) { alert('Статус не найден'); return; }
                    currentStatusType = type;
                    editingStatusId = status.id;
                    statusModalTitle.textContent = type === 'task' ? 'Изменение статуса задачи' : 'Изменение статуса клиента';
                    statusSubmitBtn.textContent = 'Подтвердить изменения';
                    formStatusIdDisplay.value = status.id;
                    formStatusName.value = status.name;
                    formStatusGroup.value = status.group || '';
                    statusModal.classList.remove('hidden');
                });
        }

        if (deleteBtn) {
            if (!confirm('Удалить этот статус?')) return;
            const id = deleteBtn.dataset.id;
            fetch(`${apiBase}/${id}`, { method: 'DELETE' })
                .then(() => fetchFn(currentPageVal));
        }
    }
});
