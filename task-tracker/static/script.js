document.addEventListener('DOMContentLoaded', () => {
    // ========== Safari Workaround: bypass browser form validation ==========
    // Safari validates ALL forms on the page (including hidden ones with datetime-local).
    // Intercept submit-button clicks, prevent native validation, dispatch submit event directly.
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('button[type="submit"]');
        if (btn) {
            e.preventDefault();
            const form = btn.closest('form');
            if (form) {
                form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
            }
        }
    });

    // ========== Auth State ==========
    let currentUserData = null;

    // Main elements
    const addTaskBtn = document.getElementById('add-task-btn');
    // allTasksBtn removed — task list is always visible
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
    const formStudentId = document.getElementById('form-student-id');
    const studentRow = document.getElementById('student-row');
    const formIsPaid = document.getElementById('form-is-paid');
    const formPaymentDate = document.getElementById('form-payment-date');
    const formHomeworkId = document.getElementById('form-homework-id');
    const formHomeworkRequired = document.getElementById('form-homework-required');
    const homeworkRequiredRow = document.getElementById('homework-required-row');
    const homeworkRow = document.getElementById('homework-row');
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

    // Roles page elements
    const rolesPage = document.getElementById('roles-page');
    const backToMainFromRolesBtn = document.getElementById('back-to-main-from-roles-btn');
    const addRoleBtn = document.getElementById('add-role-btn');
    const rolesTbody = document.getElementById('roles-tbody');
    const rolesPaginationInfo = document.getElementById('roles-pagination-info');
    const rolesPaginationControls = document.getElementById('roles-pagination-controls');

    // Role modal elements
    const roleModal = document.getElementById('role-modal');
    const roleModalTitle = document.getElementById('role-modal-title');
    const roleModalClose = document.getElementById('role-modal-close');
    const roleModalCancel = document.getElementById('role-modal-cancel');
    const roleForm = document.getElementById('role-form');
    const formRoleIdDisplay = document.getElementById('form-role-id-display');
    const formRoleName = document.getElementById('form-role-name');
    const roleSubmitBtn = document.getElementById('role-submit-btn');

    // Homework page elements
    const homeworkPage = document.getElementById('homework-page');
    const backToMainFromHomeworkBtn = document.getElementById('back-to-main-from-homework-btn');
    const addHomeworkBtn = document.getElementById('add-homework-btn');
    const homeworkTbody = document.getElementById('homework-tbody');
    const homeworkPaginationInfo = document.getElementById('homework-pagination-info');
    const homeworkPaginationControls = document.getElementById('homework-pagination-controls');

    // Homework modal elements
    const homeworkModal = document.getElementById('homework-modal');
    const homeworkModalTitle = document.getElementById('homework-modal-title');
    const homeworkModalClose = document.getElementById('homework-modal-close');
    const homeworkModalCancel = document.getElementById('homework-modal-cancel');
    const homeworkForm = document.getElementById('homework-form');
    const formHomeworkIdDisplay = document.getElementById('form-homework-id-display');
    const formHomeworkName = document.getElementById('form-homework-name');
    const formHomeworkComment = document.getElementById('form-homework-comment');
    const homeworkSubmitBtn = document.getElementById('homework-submit-btn');

    // Flashcards page elements
    const flashcardsPage = document.getElementById('flashcards-page');
    const flashcardsBtn = document.getElementById('flashcards-btn');
    const backToMainFromFlashcardsBtn = document.getElementById('back-to-main-from-flashcards-btn');

    // Top bar elements
    const topBar = document.getElementById('top-bar');
    const userDisplayName = document.getElementById('user-display-name');
    const changePasswordBtn = document.getElementById('change-password-btn');
    const logoutBtn = document.getElementById('logout-btn');

    // Users page elements
    const usersPage = document.getElementById('users-page');
    const backToMainFromUsersBtn = document.getElementById('back-to-main-from-users-btn');
    const addUserBtn = document.getElementById('add-user-btn');
    const usersTbody = document.getElementById('users-tbody');
    const usersPaginationInfo = document.getElementById('users-pagination-info');
    const usersPaginationControls = document.getElementById('users-pagination-controls');

    // User modal elements
    const userModal = document.getElementById('user-modal');
    const userModalTitle = document.getElementById('user-modal-title');
    const userModalClose = document.getElementById('user-modal-close');
    const userModalCancel = document.getElementById('user-modal-cancel');
    const userForm = document.getElementById('user-form');
    const formUserIdDisplay = document.getElementById('form-user-id-display');
    const formUserUsername = document.getElementById('form-user-username');
    const formUserDisplayName = document.getElementById('form-user-display-name');
    const formUserPassword = document.getElementById('form-user-password');
    const formUserPasswordRow = document.getElementById('form-user-password-row');
    const formUserIsActive = document.getElementById('form-user-is-active');
    const formUserRoles = document.getElementById('form-user-roles');
    const userSubmitBtn = document.getElementById('user-submit-btn');

    // Filter elements
    const filterStudentId = document.getElementById('filter-student-id');
    const filterTaskTypeId = document.getElementById('filter-task-type-id');
    const filterDateFrom = document.getElementById('filter-date-from');
    const filterDateTo = document.getElementById('filter-date-to');
    const filterTodayBtn = document.getElementById('filter-today-btn');
    const filterIsPaid = document.getElementById('filter-is-paid');
    const filterApplyBtn = document.getElementById('filter-apply-btn');
    const filterResetBtn = document.getElementById('filter-reset-btn');

    // Calendar elements
    const viewToggleBtn = document.getElementById('view-toggle-btn');
    const calendarContainer = document.getElementById('calendar-container');
    const tableView = document.getElementById('table-view');

    // Change password modal elements
    const changePasswordModal = document.getElementById('change-password-modal');
    const changePasswordModalClose = document.getElementById('change-password-modal-close');
    const changePasswordModalCancel = document.getElementById('change-password-modal-cancel');
    const changePasswordForm = document.getElementById('change-password-form');

    let currentPage = 1;
    let isListVisible = true;
    let editingTaskId = null;
    let originalStudentId = null; // Store original student when editing
    let currentView = 'calendar';
    let calendar = null;
    let currentTaskStatusesPage = 1;
    let editingStatusId = null;
    let currentTaskTypesPage = 1;
    let editingTaskTypeId = null;
    let currentRolesPage = 1;
    let editingRoleId = null;
    let currentHomeworkPage = 1;
    let editingHomeworkId = null;
    let currentUsersPage = 1;
    let editingUserId = null;

    // ========== Auth: Fetch Current User ==========

    function hasRole(...roleNames) {
        if (!currentUserData || !currentUserData.roles) return false;
        return roleNames.some(r => currentUserData.roles.includes(r));
    }

    function applyRBAC() {
        if (!currentUserData) return;

        // Top bar
        userDisplayName.textContent = currentUserData.display_name;
        topBar.classList.add('visible');

        // Show change password only for local users
        if (currentUserData.auth_source === 'local') {
            changePasswordBtn.style.display = '';
        } else {
            changePasswordBtn.style.display = 'none';
        }

        // Settings button: only admin/owner
        if (hasRole('admin', 'owner')) {
            settingsBtn.style.display = '';
        } else {
            settingsBtn.style.display = 'none';
        }

        // Task list visibility: hide for guests
        if (!hasRole('admin', 'owner', 'teacher', 'student')) {
            taskListSection.style.display = 'none';
        }
    }

    fetch('/api/auth/me')
        .then(r => {
            if (!r.ok) throw new Error('Not authenticated');
            return r.json();
        })
        .then(user => {
            currentUserData = user;
            applyRBAC();
            // Load task list immediately
            loadFilterStudents();
            loadFilterTaskTypes().then(() => {
                if (currentView === 'calendar') {
                    initCalendar();
                } else {
                    fetchTasks();
                }
            });
        })
        .catch(() => {
            window.location.href = '/login';
        });

    // ========== User Bar Logic ==========

    logoutBtn.addEventListener('click', () => {
        fetch('/api/auth/logout', { method: 'POST' })
            .then(() => {
                window.location.href = '/login';
            });
    });

    changePasswordBtn.addEventListener('click', () => {
        changePasswordModal.classList.remove('hidden');
        changePasswordForm.reset();
    });

    // ========== Change Password Modal ==========

    function closeChangePasswordModal() {
        changePasswordModal.classList.add('hidden');
        changePasswordForm.reset();
    }

    changePasswordModalClose.addEventListener('click', closeChangePasswordModal);
    changePasswordModalCancel.addEventListener('click', closeChangePasswordModal);
    changePasswordModal.addEventListener('click', (e) => {
        if (e.target === changePasswordModal) closeChangePasswordModal();
    });

    changePasswordForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const oldPassword = document.getElementById('form-old-password').value;
        const newPassword = document.getElementById('form-new-password').value;
        const confirmPassword = document.getElementById('form-confirm-password').value;

        if (newPassword !== confirmPassword) {
            alert('Пароли не совпадают');
            return;
        }
        if (newPassword.length < 6) {
            alert('Минимум 6 символов');
            return;
        }

        fetch('/api/auth/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
        })
        .then(r => {
            if (r.ok) return r.json();
            return r.json().then(err => { throw new Error(err.error || 'Ошибка'); });
        })
        .then(() => {
            alert('Пароль успешно изменён');
            closeChangePasswordModal();
        })
        .catch(err => alert(err.message));
    });

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

    // Auto-fill next homework for student
    function autoFillNextHomework() {
        // Only auto-fill if:
        // 1. Task type is "Урок"
        // 2. Student is selected
        // 3. Homework is required
        const sel = formTaskTypeId.options[formTaskTypeId.selectedIndex];
        const isLesson = sel && sel.textContent === 'Урок';

        if (!isLesson || !formStudentId.value || !formHomeworkRequired.checked) {
            return;
        }

        const studentId = formStudentId.value;

        // Fetch last homework for this student
        fetch(`/api/students/${studentId}/last-homework`)
            .then(r => r.json())
            .then(data => {
                if (data.homework_id) {
                    // Find the next homework ID in the dropdown
                    const currentHomeworkId = data.homework_id;
                    const options = Array.from(formHomeworkId.options);
                    const currentIndex = options.findIndex(opt => opt.value == currentHomeworkId);

                    if (currentIndex !== -1 && currentIndex + 1 < options.length) {
                        // Set to next homework
                        const nextOption = options[currentIndex + 1];
                        formHomeworkId.value = nextOption.value;
                    }
                }
            })
            .catch(err => {
                console.error('Failed to fetch last homework:', err);
            });
    }

    // Show/hide lesson-specific fields based on task type
    function updateLessonFieldsVisibility() {
        const sel = formTaskTypeId.options[formTaskTypeId.selectedIndex];
        const isLesson = sel && sel.textContent === 'Урок';

        // Show/hide student, homework_required, and homework fields
        studentRow.style.display = isLesson ? '' : 'none';
        homeworkRequiredRow.style.display = isLesson ? '' : 'none';
        homeworkRow.style.display = isLesson ? '' : 'none';

        if (!isLesson) {
            formStudentId.value = '';
            formHomeworkRequired.checked = true; // Reset to default
            formHomeworkId.value = '';
        } else {
            // When switching to lesson type, set homework_required to true by default
            formHomeworkRequired.checked = true;
        }
    }

    formTaskTypeId.addEventListener('change', () => {
        updateLessonFieldsVisibility();
    });

    // Auto-fill homework when student or homework_required changes
    formStudentId.addEventListener('change', (e) => {
        // If editing and student changed, show confirmation
        if (editingTaskId && originalStudentId && formStudentId.value !== originalStudentId) {
            const confirmed = confirm('Внимание! Вы меняете ученика, изменится Домашнее задание, которое ему было назначено! Вы уверены?');

            if (!confirmed) {
                // Revert to original student
                formStudentId.value = originalStudentId;
                return;
            }

            // User confirmed, update originalStudentId and auto-fill homework
            originalStudentId = formStudentId.value;
        }

        autoFillNextHomework();
    });

    formHomeworkRequired.addEventListener('change', () => {
        autoFillNextHomework();
    });

    // Open modal and auto-fill fields
    addTaskBtn.addEventListener('click', () => {
        editingTaskId = null;
        originalStudentId = null;
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

                // Author from current user
                formAuthor.value = currentUserData ? currentUserData.display_name : '';

                // Clear other fields
                if (formDescription) formDescription.value = '';
                formStartDate.value = '';
                formDuration.value = '';
                formDuration.disabled = true;
                formEndDate.value = '';
                formStudentId.value = '';
                formStatusId.value = '';
                formTaskTypeId.value = '';
                formIsPaid.checked = false;
                formPaymentDate.value = '';
                formHomeworkId.value = '';
                formHomeworkRequired.checked = true;
                formComment.value = '';
                formClosingDate.value = '';

                // Fetch and populate student, status, task type, and homework dropdowns
                return Promise.all([
                    fetch('/api/students/all').then(r => r.json()),
                    fetch('/api/task-statuses/all').then(r => r.json()),
                    fetch('/api/task-types/all').then(r => r.json()),
                    fetch('/api/homework/all').then(r => r.json())
                ]);
            })
            .then(([studentData, statusData, typeData, homeworkData]) => {
                formStudentId.innerHTML = '<option value="">-- Выберите ученика --</option>';
                studentData.students.forEach(student => {
                    const option = document.createElement('option');
                    option.value = student.id;
                    option.textContent = student.display_name;
                    formStudentId.appendChild(option);
                });

                formStatusId.innerHTML = '<option value="">-- Выберите статус --</option>';
                statusData.statuses.forEach(status => {
                    const option = document.createElement('option');
                    option.value = status.id;
                    option.textContent = status.name;
                    formStatusId.appendChild(option);
                });
                // Default to "Новый"
                const newStatus = statusData.statuses.find(s => s.name === 'Новый');
                if (newStatus) formStatusId.value = newStatus.id;

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
                updateLessonFieldsVisibility();

                formHomeworkId.innerHTML = '<option value="">-- Выберите --</option>';
                homeworkData.homework.forEach(hw => {
                    const option = document.createElement('option');
                    option.value = hw.id;
                    option.textContent = hw.name;
                    formHomeworkId.appendChild(option);
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
        }
    });

    // Close modal on outside click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    // Task list is always visible — no toggle needed

    // ========== Filters Logic ==========

    function loadFilterStudents() {
        fetch('/api/students/all')
            .then(r => r.json())
            .then(data => {
                const currentVal = filterStudentId.value;
                filterStudentId.innerHTML = '<option value="">Все</option>';
                data.students.forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s.id;
                    opt.textContent = s.display_name;
                    filterStudentId.appendChild(opt);
                });
                filterStudentId.value = currentVal;
            });
    }

    function loadFilterTaskTypes() {
        return fetch('/api/task-types/all')
            .then(r => r.json())
            .then(data => {
                const currentVal = filterTaskTypeId.value;
                filterTaskTypeId.innerHTML = '<option value="">Все</option>';
                data.task_types.forEach(tt => {
                    const opt = document.createElement('option');
                    opt.value = tt.id;
                    opt.textContent = tt.name;
                    filterTaskTypeId.appendChild(opt);
                });
                // Set default to "Урок" if not already set
                if (!currentVal) {
                    const lessonType = data.task_types.find(tt => tt.name === 'Урок');
                    if (lessonType) filterTaskTypeId.value = lessonType.id;
                } else {
                    filterTaskTypeId.value = currentVal;
                }
            });
    }

    function buildFilterParams() {
        const params = new URLSearchParams();
        params.set('page', currentPage);
        if (filterStudentId.value) params.set('student_id', filterStudentId.value);
        if (filterTaskTypeId.value) params.set('task_type_id', filterTaskTypeId.value);
        if (filterDateFrom.value) params.set('date_from', filterDateFrom.value);
        if (filterDateTo.value) params.set('date_to', filterDateTo.value);
        if (filterIsPaid.value) params.set('is_paid', filterIsPaid.value);
        return params.toString();
    }

    filterTodayBtn.addEventListener('click', () => {
        const today = new Date();
        const y = today.getFullYear();
        const m = String(today.getMonth() + 1).padStart(2, '0');
        const d = String(today.getDate()).padStart(2, '0');
        filterDateFrom.value = `${y}-${m}-${d}T00:00`;
        filterDateTo.value = `${y}-${m}-${d}T23:59`;
    });

    filterApplyBtn.addEventListener('click', () => {
        currentPage = 1;
        fetchTasks();
    });

    filterResetBtn.addEventListener('click', () => {
        filterStudentId.value = '';
        filterDateFrom.value = '';
        filterDateTo.value = '';
        filterIsPaid.value = '';
        currentPage = 1;
        // Reset task type to default "Урок"
        fetch('/api/task-types/all')
            .then(r => r.json())
            .then(data => {
                const lessonType = data.task_types.find(tt => tt.name === 'Урок');
                if (lessonType) filterTaskTypeId.value = lessonType.id;
                fetchTasks();
            });
    });

    // ========== Calendar Logic ==========

    function dateToLocalIso(date) {
        if (!date) return null;
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        const h = String(date.getHours()).padStart(2, '0');
        const min = String(date.getMinutes()).padStart(2, '0');
        return `${y}-${m}-${d}T${h}:${min}`;
    }

    async function handleEventMove(info) {
        const taskId = info.event.id;
        const data = { start_date: dateToLocalIso(info.event.start) };
        if (info.event.end) {
            data.end_date = dateToLocalIso(info.event.end);
        }

        try {
            const r = await fetch(`/api/tasks/${taskId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (!r.ok) {
                let msg = 'Ошибка ' + r.status;
                try { const err = await r.json(); msg = err.error || msg; } catch {}
                alert(msg);
                info.revert();
                return;
            }
            // Update extendedProps with new dates
            const updated = await r.json().catch(() => null);
            if (updated) {
                info.event.setExtendedProp('start_date_iso', updated.start_date_iso);
                info.event.setExtendedProp('end_date_iso', updated.end_date_iso);
                info.event.setExtendedProp('start_date', updated.start_date);
                info.event.setExtendedProp('end_date', updated.end_date);
            }
        } catch (e) {
            alert('Ошибка сети при перемещении задачи');
            info.revert();
        }
    }

    function initCalendar() {
        calendar = new FullCalendar.Calendar(calendarContainer, {
            locale: 'ru',
            firstDay: 1, // Start week on Monday
            initialView: 'timeGridWeek',
            editable: true,
            longPressDelay: 300,
            eventLongPressDelay: 300,
            selectLongPressDelay: 300,
            snapDuration: '00:15:00',
            slotDuration: '00:15:00',
            slotMinTime: '07:00:00',
            slotMaxTime: '23:00:00',
            scrollTime: '08:00:00',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay'
            },
            buttonText: {
                today: 'Сегодня',
                month: 'Месяц',
                week: 'Неделя',
                day: 'День'
            },
            events: function(info, successCallback, failureCallback) {
                fetch(`/api/tasks/calendar?start=${info.startStr}&end=${info.endStr}`)
                    .then(r => r.json())
                    .then(events => successCallback(events))
                    .catch(() => failureCallback());
            },
            eventClick: function(info) {
                openEditFromCalendar(info.event);
            },
            eventDrop: function(info) {
                handleEventMove(info);
            },
            eventResize: function(info) {
                handleEventMove(info);
            },
            height: '100%',
            eventDisplay: 'block',
            dayMaxEvents: 4,
        });
        calendar.render();

        window.addEventListener('resize', () => {
            if (calendar) calendar.updateSize();
        });
    }

    function openEditFromCalendar(event) {
        const task = event.extendedProps;
        const taskId = parseInt(event.id);

        Promise.all([
            fetch('/api/students/all').then(r => r.json()),
            fetch('/api/task-statuses/all').then(r => r.json()),
            fetch('/api/task-types/all').then(r => r.json()),
            fetch('/api/homework/all').then(r => r.json())
        ]).then(([studentData, statusData, typeData, homeworkData]) => {
            editingTaskId = taskId;
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
            formHomeworkRequired.checked = task.homework_required ?? true;
            formComment.value = task.comment || '';
            formClosingDate.value = task.closing_date_iso || '';

            formStudentId.innerHTML = '<option value="">-- Выберите ученика --</option>';
            studentData.students.forEach(student => {
                const option = document.createElement('option');
                option.value = student.id;
                option.textContent = student.display_name;
                formStudentId.appendChild(option);
            });
            formStudentId.value = task.student_id || '';
            originalStudentId = task.student_id || null; // Store original for confirmation

            formStatusId.innerHTML = '<option value="">-- Выберите статус --</option>';
            statusData.statuses.forEach(status => {
                const option = document.createElement('option');
                option.value = status.id;
                option.textContent = status.name;
                formStatusId.appendChild(option);
            });
            formStatusId.value = task.status_id || '';

            formTaskTypeId.innerHTML = '<option value="">-- Выберите тип --</option>';
            typeData.task_types.forEach(tt => {
                const option = document.createElement('option');
                option.value = tt.id;
                option.textContent = tt.name;
                formTaskTypeId.appendChild(option);
            });
            formTaskTypeId.value = task.task_type_id || '';
            updateLessonFieldsVisibility();

            formHomeworkId.innerHTML = '<option value="">-- Выберите --</option>';
            homeworkData.homework.forEach(hw => {
                const option = document.createElement('option');
                option.value = hw.id;
                option.textContent = hw.name;
                formHomeworkId.appendChild(option);
            });
            formHomeworkId.value = task.homework_id || '';

            modal.classList.remove('hidden');
        });
    }

    viewToggleBtn.addEventListener('click', () => {
        if (currentView === 'table') {
            currentView = 'calendar';
            tableView.classList.add('hidden');
            calendarContainer.classList.remove('hidden');
            taskListSection.classList.add('view-calendar');
            viewToggleBtn.textContent = 'Таблица';
            if (!calendar) {
                initCalendar();
            } else {
                calendar.updateSize();
                calendar.refetchEvents();
            }
        } else {
            currentView = 'table';
            calendarContainer.classList.add('hidden');
            tableView.classList.remove('hidden');
            taskListSection.classList.remove('view-calendar');
            viewToggleBtn.textContent = 'Календарь';
        }
    });

    // Fetch paginated tasks
    function fetchTasks(page) {
        if (page !== undefined) currentPage = page;
        fetch(`/api/tasks?${buildFilterParams()}`)
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
                <td>${escapeHtml(task.student_name || '—')}</td>
                <td>${escapeHtml(task.task_type_name || '—')}</td>
                <!-- <td class="col-desc" title="${escapeAttr(task.description)}">${escapeHtml(task.description)}</td> -->
                <td>${task.created_at || '—'}</td>
                <td>${task.start_date || '—'}</td>
                <td>${task.end_date || '—'}</td>
                <td>${formatDuration(task.duration)}</td>
                <td>${escapeHtml(task.author || '—')}</td>
                <td class="cell-bool">${task.is_paid ? '✓' : '✗'}</td>
                <td>${task.payment_date || '—'}</td>
                <td>${escapeHtml(task.homework_name || '—')}</td>
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

    // Submit task form — button is type="button" to bypass Safari datetime-local validation
    taskSubmitBtn.addEventListener('click', () => {
        taskForm.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });

    taskForm.addEventListener('submit', (e) => {
        e.preventDefault();

        // Validate required fields
        if (!formTaskTypeId.value) {
            alert('Тип задачи обязателен для заполнения');
            return;
        }

        // Lesson-specific validations
        const selectedTypeOption = formTaskTypeId.options[formTaskTypeId.selectedIndex];
        const isLessonType = selectedTypeOption && selectedTypeOption.textContent === 'Урок';

        if (isLessonType) {
            if (!formStartDate.value) {
                alert('Дата начала обязательна для типа задачи "Урок"');
                return;
            }
            if (!formStudentId.value) {
                alert('Ученик обязателен для типа задачи "Урок"');
                return;
            }
            if (!formDuration.value) {
                alert('Продолжительность обязательна для типа задачи "Урок"');
                return;
            }

            // Check if homework is required
            const selectedStatusOption = formStatusId.options[formStatusId.selectedIndex];
            const isCompleted = selectedStatusOption && selectedStatusOption.textContent === 'Завершён';

            if (formHomeworkRequired.checked && isCompleted && !formHomeworkId.value) {
                alert('Домашнее задание обязательно, если включена опция "ДЗ обязательно" и статус "Завершён"');
                return;
            }
        }

        // Collect form data
        const taskData = {
            description: formDescription ? formDescription.value.trim() : '',
            start_date: formStartDate.value || null,
            end_date: formEndDate.value || null,
            duration: formDuration.value ? parseInt(formDuration.value) : null,
            student_id: formStudentId.value ? parseInt(formStudentId.value) : null,
            is_paid: formIsPaid.checked,
            payment_date: formPaymentDate.value || null,
            homework_id: formHomeworkId.value ? parseInt(formHomeworkId.value) : null,
            homework_required: formHomeworkRequired.checked,
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

            // Refresh data
            if (currentView === 'calendar' && calendar) {
                calendar.refetchEvents();
            }
            if (!isEditing) {
                currentPage = 1;
            }
            fetchTasks(currentPage);
            if (calendar) calendar.refetchEvents();
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
                fetch('/api/students/all').then(r => r.json()),
                fetch('/api/task-statuses/all').then(r => r.json()),
                fetch('/api/task-types/all').then(r => r.json()),
                fetch('/api/homework/all').then(r => r.json())
            ])
                .then(([data, studentData, statusData, typeData, homeworkData]) => {
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
                    formHomeworkRequired.checked = task.homework_required ?? true;
                    formComment.value = task.comment || '';
                    formClosingDate.value = task.closing_date_iso || '';

                    // Populate student dropdown
                    formStudentId.innerHTML = '<option value="">-- Выберите ученика --</option>';
                    studentData.students.forEach(student => {
                        const option = document.createElement('option');
                        option.value = student.id;
                        option.textContent = student.display_name;
                        formStudentId.appendChild(option);
                    });
                    formStudentId.value = task.student_id || '';
                    originalStudentId = task.student_id || null; // Store original for confirmation

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
                    updateLessonFieldsVisibility();

                    // Populate homework dropdown
                    formHomeworkId.innerHTML = '<option value="">-- Выберите --</option>';
                    homeworkData.homework.forEach(hw => {
                        const option = document.createElement('option');
                        option.value = hw.id;
                        option.textContent = hw.name;
                        formHomeworkId.appendChild(option);
                    });
                    formHomeworkId.value = task.homework_id || '';

                    modal.classList.remove('hidden');
                });
        }

        if (deleteBtn) {
            if (!confirm('Удалить эту задачу?')) return;
            const id = deleteBtn.dataset.id;
            fetch(`/api/tasks/${id}`, { method: 'DELETE' })
                .then(() => {
                    if (isListVisible) fetchTasks();
                    if (calendar) calendar.refetchEvents();
                });
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

            if (option === 'statuses') {
                showStatusesPage();
            } else if (option === 'task-types') {
                showTaskTypesPage();
            } else if (option === 'roles') {
                showRolesPage();
            } else if (option === 'users') {
                showUsersPage();
            } else if (option === 'homework') {
                showHomeworkPage();
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

    function hideAllPages() {
        document.querySelector('.container').classList.add('hidden');
        statusesPage.classList.add('hidden');
        taskTypesPage.classList.add('hidden');
        rolesPage.classList.add('hidden');
        homeworkPage.classList.add('hidden');
        usersPage.classList.add('hidden');
        flashcardsPage.classList.add('hidden');
    }

    function showMainPage() {
        hideAllPages();
        document.querySelector('.container').classList.remove('hidden');
    }

    // ========== Flashcards Page Logic ==========

    flashcardsBtn.addEventListener('click', () => {
        hideAllPages();
        flashcardsPage.classList.remove('hidden');
    });

    backToMainFromFlashcardsBtn.addEventListener('click', showMainPage);

    // ========== Statuses Page Logic ==========

    function showStatusesPage() {
        hideAllPages();
        statusesPage.classList.remove('hidden');
        currentTaskStatusesPage = 1;
        fetchTaskStatuses();
    }

    backToMainFromStatusesBtn.addEventListener('click', showMainPage);

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

    // Render statuses table
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
        fetch('/api/task-statuses?page=1')
            .then(r => r.json())
            .then(data => {
                editingStatusId = null;
                statusModalTitle.textContent = 'Создание статуса';
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

        const method = editingStatusId ? 'PUT' : 'POST';
        const url = editingStatusId ? `/api/task-statuses/${editingStatusId}` : '/api/task-statuses';

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
            fetchTaskStatuses(currentTaskStatusesPage);
        })
        .catch(err => alert(err.message));
    });

    // Edit/delete task statuses (event delegation)
    taskStatusesTbody.addEventListener('click', (e) => {
        handleStatusTableClick(e, '/api/task-statuses', currentTaskStatusesPage, fetchTaskStatuses);
    });

    // ========== Task Types Page Logic ==========

    function showTaskTypesPage() {
        hideAllPages();
        taskTypesPage.classList.remove('hidden');
        currentTaskTypesPage = 1;
        fetchTaskTypes();
    }

    backToMainFromTaskTypesBtn.addEventListener('click', showMainPage);

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

    // ========== Roles Page Logic ==========

    function showRolesPage() {
        hideAllPages();
        rolesPage.classList.remove('hidden');
        currentRolesPage = 1;
        fetchRoles();
    }

    backToMainFromRolesBtn.addEventListener('click', showMainPage);

    function fetchRoles(page) {
        if (page !== undefined) currentRolesPage = page;
        fetch(`/api/roles?page=${currentRolesPage}`)
            .then(r => r.json())
            .then(data => {
                renderRoles(data.roles);
                renderRolesPagination(data);
            });
    }

    function renderRoles(roles) {
        rolesTbody.innerHTML = '';
        if (roles.length === 0) {
            rolesTbody.innerHTML = '<tr><td colspan="4" class="empty-msg">Ролей нет</td></tr>';
            return;
        }
        roles.forEach(role => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${role.id}</td>
                <td>${escapeHtml(role.name)}</td>
                <td><button class="btn-edit" data-id="${role.id}">Изменить</button></td>
                <td><button class="btn-delete" data-id="${role.id}">Удалить</button></td>
            `;
            rolesTbody.appendChild(tr);
        });
    }

    function renderRolesPagination(data) {
        rolesPaginationControls.innerHTML = '';
        if (data.total === 0) {
            rolesPaginationInfo.textContent = '';
            return;
        }
        rolesPaginationInfo.textContent = `Страница ${data.current_page} из ${data.pages} (всего ${data.total} ролей)`;
        if (data.current_page > 1) {
            addRolePageBtn('← Пред', data.current_page - 1);
        }
        const start = Math.max(1, data.current_page - 2);
        const end = Math.min(data.pages, data.current_page + 2);
        for (let i = start; i <= end; i++) {
            addRolePageBtn(String(i), i, i === data.current_page);
        }
        if (data.current_page < data.pages) {
            addRolePageBtn('След →', data.current_page + 1);
        }
    }

    function addRolePageBtn(label, page, isActive = false) {
        const btn = document.createElement('button');
        btn.className = 'btn-page' + (isActive ? ' active' : '');
        btn.textContent = label;
        btn.addEventListener('click', () => fetchRoles(page));
        rolesPaginationControls.appendChild(btn);
    }

    // ========== Role Modal Logic ==========

    addRoleBtn.addEventListener('click', () => {
        fetch('/api/roles?page=1')
            .then(r => r.json())
            .then(data => {
                editingRoleId = null;
                roleModalTitle.textContent = 'Создание роли';
                roleSubmitBtn.textContent = 'Подтвердить и создать';
                formRoleIdDisplay.value = data.next_id;
                formRoleName.value = '';
                roleModal.classList.remove('hidden');
            });
    });

    function closeRoleModal() {
        roleModal.classList.add('hidden');
        roleForm.reset();
        editingRoleId = null;
    }

    roleModalClose.addEventListener('click', closeRoleModal);
    roleModalCancel.addEventListener('click', closeRoleModal);
    roleModal.addEventListener('click', (e) => {
        if (e.target === roleModal) closeRoleModal();
    });

    roleForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const name = formRoleName.value.trim();
        if (!name) {
            alert('Наименование обязательно для заполнения');
            return;
        }

        const method = editingRoleId ? 'PUT' : 'POST';
        const url = editingRoleId ? `/api/roles/${editingRoleId}` : '/api/roles';

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
            closeRoleModal();
            fetchRoles(currentRolesPage);
        })
        .catch(err => alert(err.message));
    });

    // Edit/delete roles (event delegation)
    rolesTbody.addEventListener('click', (e) => {
        const editBtn = e.target.closest('.btn-edit');
        const deleteBtn = e.target.closest('.btn-delete');

        if (editBtn) {
            const id = parseInt(editBtn.dataset.id);
            fetch(`/api/roles?page=${currentRolesPage}`)
                .then(r => r.json())
                .then(data => {
                    const role = data.roles.find(r => r.id === id);
                    if (!role) { alert('Роль не найдена'); return; }
                    editingRoleId = role.id;
                    roleModalTitle.textContent = 'Изменение роли';
                    roleSubmitBtn.textContent = 'Подтвердить изменения';
                    formRoleIdDisplay.value = role.id;
                    formRoleName.value = role.name;
                    roleModal.classList.remove('hidden');
                });
        }

        if (deleteBtn) {
            if (!confirm('Удалить эту роль?')) return;
            const id = deleteBtn.dataset.id;
            fetch(`/api/roles/${id}`, { method: 'DELETE' })
                .then(() => fetchRoles(currentRolesPage));
        }
    });

    // Sanitize HTML: keep only <a> tags with href, strip everything else
    function sanitizeHtml(html) {
        const div = document.createElement('div');
        div.innerHTML = html;

        // Step 1: Clean all <a> tags — keep only href, add target/rel
        div.querySelectorAll('a').forEach(a => {
            const href = a.getAttribute('href');
            while (a.attributes.length > 0) {
                a.removeAttribute(a.attributes[0].name);
            }
            if (href) {
                a.setAttribute('href', href);
                a.setAttribute('target', '_blank');
                a.setAttribute('rel', 'noopener');
            }
        });

        // Step 2: Strip all non-<a> elements (unwrap them, keeping children)
        // Repeat until no more non-<a> elements remain
        let found = true;
        while (found) {
            found = false;
            const els = div.getElementsByTagName('*');
            for (let i = 0; i < els.length; i++) {
                if (els[i].tagName !== 'A') {
                    const el = els[i];
                    while (el.firstChild) {
                        el.parentNode.insertBefore(el.firstChild, el);
                    }
                    el.parentNode.removeChild(el);
                    found = true;
                    break; // restart — DOM changed
                }
            }
        }

        return div.innerHTML;
    }

    // Auto-detect URLs in plain text and wrap them in <a> tags
    function autoLinkUrls(text) {
        const escaped = escapeHtml(text);
        return escaped.replace(
            /(https?:\/\/[^\s<]+)/g,
            '<a href="$1" target="_blank" rel="noopener">$1</a>'
        );
    }

    // Handle paste in richtext editor: preserve links from clipboard HTML
    formHomeworkComment.addEventListener('paste', (e) => {
        e.preventDefault();
        const html = e.clipboardData.getData('text/html');
        const text = e.clipboardData.getData('text/plain');

        if (html) {
            const sanitized = sanitizeHtml(html);
            // If HTML had no links after sanitizing, auto-link URLs from plain text
            if (!sanitized.includes('<a ') && text) {
                document.execCommand('insertHTML', false, autoLinkUrls(text));
            } else {
                document.execCommand('insertHTML', false, sanitized);
            }
        } else if (text) {
            document.execCommand('insertHTML', false, autoLinkUrls(text));
        }
    });

    // ========== Homework Page Logic ==========

    function showHomeworkPage() {
        hideAllPages();
        homeworkPage.classList.remove('hidden');
        currentHomeworkPage = 1;
        fetchHomework();
    }

    backToMainFromHomeworkBtn.addEventListener('click', showMainPage);

    function fetchHomework(page) {
        if (page !== undefined) currentHomeworkPage = page;
        fetch(`/api/homework?page=${currentHomeworkPage}`)
            .then(r => r.json())
            .then(data => {
                renderHomework(data.homework);
                renderHomeworkPagination(data);
            });
    }

    function renderHomework(items) {
        homeworkTbody.innerHTML = '';
        if (items.length === 0) {
            homeworkTbody.innerHTML = '<tr><td colspan="5" class="empty-msg">Домашних заданий нет</td></tr>';
            return;
        }
        items.forEach(hw => {
            const tr = document.createElement('tr');
            const commentHtml = hw.comment ? sanitizeHtml(hw.comment) : '—';
            tr.innerHTML = `
                <td>${hw.id}</td>
                <td>${escapeHtml(hw.name)}</td>
                <td class="col-comment homework-comment">${commentHtml}</td>
                <td><button class="btn-edit" data-id="${hw.id}">Изменить</button></td>
                <td><button class="btn-delete" data-id="${hw.id}">Удалить</button></td>
            `;
            homeworkTbody.appendChild(tr);
        });
    }

    function renderHomeworkPagination(data) {
        homeworkPaginationControls.innerHTML = '';
        if (data.total === 0) {
            homeworkPaginationInfo.textContent = '';
            return;
        }
        homeworkPaginationInfo.textContent = `Страница ${data.current_page} из ${data.pages} (всего ${data.total} заданий)`;
        if (data.current_page > 1) {
            addHomeworkPageBtn('← Пред', data.current_page - 1);
        }
        const start = Math.max(1, data.current_page - 2);
        const end = Math.min(data.pages, data.current_page + 2);
        for (let i = start; i <= end; i++) {
            addHomeworkPageBtn(String(i), i, i === data.current_page);
        }
        if (data.current_page < data.pages) {
            addHomeworkPageBtn('След →', data.current_page + 1);
        }
    }

    function addHomeworkPageBtn(label, page, isActive = false) {
        const btn = document.createElement('button');
        btn.className = 'btn-page' + (isActive ? ' active' : '');
        btn.textContent = label;
        btn.addEventListener('click', () => fetchHomework(page));
        homeworkPaginationControls.appendChild(btn);
    }

    // ========== Homework Modal Logic ==========

    addHomeworkBtn.addEventListener('click', () => {
        fetch('/api/homework?page=1')
            .then(r => r.json())
            .then(data => {
                editingHomeworkId = null;
                homeworkModalTitle.textContent = 'Создание домашнего задания';
                homeworkSubmitBtn.textContent = 'Подтвердить и создать';
                formHomeworkIdDisplay.value = data.next_id;
                formHomeworkName.value = '';
                formHomeworkComment.innerHTML = '';
                homeworkModal.classList.remove('hidden');
            });
    });

    function closeHomeworkModal() {
        homeworkModal.classList.add('hidden');
        homeworkForm.reset();
        formHomeworkComment.innerHTML = '';
        editingHomeworkId = null;
    }

    homeworkModalClose.addEventListener('click', closeHomeworkModal);
    homeworkModalCancel.addEventListener('click', closeHomeworkModal);
    homeworkModal.addEventListener('click', (e) => {
        if (e.target === homeworkModal) closeHomeworkModal();
    });

    homeworkForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const name = formHomeworkName.value.trim();
        if (!name) {
            alert('Наименование обязательно для заполнения');
            return;
        }

        const rawComment = sanitizeHtml(formHomeworkComment.innerHTML).trim();
        const hwData = {
            name: name,
            comment: rawComment || null,
        };

        const method = editingHomeworkId ? 'PUT' : 'POST';
        const url = editingHomeworkId ? `/api/homework/${editingHomeworkId}` : '/api/homework';

        fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(hwData)
        })
        .then(r => {
            if (r.ok) return r.json();
            return r.json().then(err => { throw new Error(err.error || 'Ошибка'); });
        })
        .then(() => {
            closeHomeworkModal();
            fetchHomework(currentHomeworkPage);
        })
        .catch(err => alert(err.message));
    });

    // Edit/delete homework (event delegation)
    homeworkTbody.addEventListener('click', (e) => {
        const editBtn = e.target.closest('.btn-edit');
        const deleteBtn = e.target.closest('.btn-delete');

        if (editBtn) {
            const id = parseInt(editBtn.dataset.id);
            fetch(`/api/homework?page=${currentHomeworkPage}`)
                .then(r => r.json())
                .then(data => {
                    const hw = data.homework.find(h => h.id === id);
                    if (!hw) { alert('Домашнее задание не найдено'); return; }
                    editingHomeworkId = hw.id;
                    homeworkModalTitle.textContent = 'Изменение домашнего задания';
                    homeworkSubmitBtn.textContent = 'Подтвердить изменения';
                    formHomeworkIdDisplay.value = hw.id;
                    formHomeworkName.value = hw.name;
                    formHomeworkComment.innerHTML = hw.comment || '';
                    homeworkModal.classList.remove('hidden');
                });
        }

        if (deleteBtn) {
            if (!confirm('Удалить это домашнее задание?')) return;
            const id = deleteBtn.dataset.id;
            fetch(`/api/homework/${id}`, { method: 'DELETE' })
                .then(() => fetchHomework(currentHomeworkPage));
        }
    });

    function handleStatusTableClick(e, apiBase, currentPageVal, fetchFn) {
        const editBtn = e.target.closest('.btn-edit');
        const deleteBtn = e.target.closest('.btn-delete');

        if (editBtn) {
            const id = parseInt(editBtn.dataset.id);
            fetch(`${apiBase}?page=${currentPageVal}`)
                .then(r => r.json())
                .then(data => {
                    const status = data.statuses.find(s => s.id === id);
                    if (!status) { alert('Статус не найден'); return; }
                    editingStatusId = status.id;
                    statusModalTitle.textContent = 'Изменение статуса';
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

    // ========== Users Page Logic ==========

    function showUsersPage() {
        hideAllPages();
        usersPage.classList.remove('hidden');
        currentUsersPage = 1;
        fetchUsers();
    }

    backToMainFromUsersBtn.addEventListener('click', showMainPage);

    function fetchUsers(page) {
        if (page !== undefined) currentUsersPage = page;
        fetch(`/api/users?page=${currentUsersPage}`)
            .then(r => r.json())
            .then(data => {
                renderUsers(data.users);
                renderUsersPagination(data);
            });
    }

    function renderUsers(users) {
        usersTbody.innerHTML = '';
        if (users.length === 0) {
            usersTbody.innerHTML = '<tr><td colspan="13" class="empty-msg">Пользователей нет</td></tr>';
            return;
        }

        const sourceLabels = { local: 'Локальный', yandex: 'Яндекс', vk: 'ВКонтакте' };

        users.forEach(user => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${user.id}</td>
                <td>${escapeHtml(user.username)}</td>
                <td>${escapeHtml(user.display_name)}</td>
                <td>${escapeHtml(user.roles.join(', ') || '—')}</td>
                <td>${escapeHtml(sourceLabels[user.auth_source] || user.auth_source)}</td>
                <td class="cell-bool">${user.is_active ? '✓' : '✗'}</td>
                <td>${user.created_at || '—'}</td>
                <td>${user.telegram_id ? escapeHtml(user.telegram_id) : '—'}</td>
                <td>${user.telegram_username ? escapeHtml(user.telegram_username) : '—'}</td>
                <td class="cell-bool">${user.telegram_notifications ? '✓' : '✗'}</td>
                <td><button class="btn-edit" data-id="${user.id}">Изменить</button></td>
                <td><button class="btn-delete" data-id="${user.id}">Удалить</button></td>
                <td><button class="btn-reset-password" data-id="${user.id}">Сбросить пароль</button></td>
            `;
            usersTbody.appendChild(tr);
        });
    }

    function renderUsersPagination(data) {
        usersPaginationControls.innerHTML = '';
        if (data.total === 0) {
            usersPaginationInfo.textContent = '';
            return;
        }
        usersPaginationInfo.textContent = `Страница ${data.current_page} из ${data.pages} (всего ${data.total} пользователей)`;
        if (data.current_page > 1) {
            addUserPageBtn('← Пред', data.current_page - 1);
        }
        const start = Math.max(1, data.current_page - 2);
        const end = Math.min(data.pages, data.current_page + 2);
        for (let i = start; i <= end; i++) {
            addUserPageBtn(String(i), i, i === data.current_page);
        }
        if (data.current_page < data.pages) {
            addUserPageBtn('След →', data.current_page + 1);
        }
    }

    function addUserPageBtn(label, page, isActive = false) {
        const btn = document.createElement('button');
        btn.className = 'btn-page' + (isActive ? ' active' : '');
        btn.textContent = label;
        btn.addEventListener('click', () => fetchUsers(page));
        usersPaginationControls.appendChild(btn);
    }

    // ========== User Modal Logic ==========

    addUserBtn.addEventListener('click', () => {
        Promise.all([
            fetch('/api/users?page=1').then(r => r.json()),
            fetch('/api/roles/all').then(r => r.json())
        ])
            .then(([data, rolesData]) => {
                editingUserId = null;
                userModalTitle.textContent = 'Создание пользователя';
                userSubmitBtn.textContent = 'Подтвердить и создать';
                formUserIdDisplay.value = data.next_id;
                formUserUsername.value = '';
                formUserUsername.readOnly = false;
                formUserDisplayName.value = '';
                formUserPassword.value = '';
                formUserPasswordRow.style.display = '';
                formUserIsActive.checked = true;

                // Render role checkboxes
                renderRoleCheckboxes(rolesData.roles, []);

                userModal.classList.remove('hidden');
            });
    });

    function renderRoleCheckboxes(allRoles, selectedRoleNames) {
        formUserRoles.innerHTML = '';
        allRoles.forEach(role => {
            const label = document.createElement('label');
            label.className = 'checkbox-label';
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.value = role.id;
            cb.name = 'user-role';
            if (selectedRoleNames.includes(role.name)) {
                cb.checked = true;
            }
            label.appendChild(cb);
            label.appendChild(document.createTextNode(' ' + role.name));
            formUserRoles.appendChild(label);
        });
    }

    function closeUserModal() {
        userModal.classList.add('hidden');
        userForm.reset();
        editingUserId = null;
    }

    userModalClose.addEventListener('click', closeUserModal);
    userModalCancel.addEventListener('click', closeUserModal);
    userModal.addEventListener('click', (e) => {
        if (e.target === userModal) closeUserModal();
    });

    userForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const username = formUserUsername.value.trim();
        const displayName = formUserDisplayName.value.trim();
        const password = formUserPassword.value;
        const isActive = formUserIsActive.checked;

        if (!username) { alert('Логин обязателен'); return; }
        if (!displayName) { alert('Имя обязательно'); return; }

        // Collect selected roles
        const roleIds = [];
        formUserRoles.querySelectorAll('input[name="user-role"]:checked').forEach(cb => {
            roleIds.push(parseInt(cb.value));
        });

        const userData = {
            display_name: displayName,
            is_active: isActive,
            role_ids: roleIds,
        };

        if (editingUserId) {
            // Update
            fetch(`/api/users/${editingUserId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userData)
            })
            .then(r => {
                if (r.ok) return r.json();
                return r.json().then(err => { throw new Error(err.error || 'Ошибка'); });
            })
            .then(() => {
                closeUserModal();
                fetchUsers(currentUsersPage);
            })
            .catch(err => alert(err.message));
        } else {
            // Create
            if (!password || password.length < 6) {
                alert('Пароль: минимум 6 символов');
                return;
            }
            userData.username = username;
            userData.password = password;

            fetch('/api/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userData)
            })
            .then(r => {
                if (r.ok) return r.json();
                return r.json().then(err => { throw new Error(err.error || 'Ошибка'); });
            })
            .then(() => {
                closeUserModal();
                fetchUsers(currentUsersPage);
            })
            .catch(err => alert(err.message));
        }
    });

    // Edit, delete, reset password for users (event delegation)
    usersTbody.addEventListener('click', (e) => {
        const editBtn = e.target.closest('.btn-edit');
        const deleteBtn = e.target.closest('.btn-delete');
        const resetBtn = e.target.closest('.btn-reset-password');

        if (editBtn) {
            const id = parseInt(editBtn.dataset.id);
            Promise.all([
                fetch(`/api/users?page=${currentUsersPage}`).then(r => r.json()),
                fetch('/api/roles/all').then(r => r.json())
            ])
                .then(([data, rolesData]) => {
                    const user = data.users.find(u => u.id === id);
                    if (!user) { alert('Пользователь не найден'); return; }
                    editingUserId = user.id;
                    userModalTitle.textContent = 'Изменение пользователя';
                    userSubmitBtn.textContent = 'Подтвердить изменения';
                    formUserIdDisplay.value = user.id;
                    formUserUsername.value = user.username;
                    formUserUsername.readOnly = true;
                    formUserDisplayName.value = user.display_name;
                    formUserPassword.value = '';
                    formUserPasswordRow.style.display = 'none';
                    formUserIsActive.checked = user.is_active;

                    renderRoleCheckboxes(rolesData.roles, user.roles);

                    userModal.classList.remove('hidden');
                });
        }

        if (deleteBtn) {
            if (!confirm('Удалить этого пользователя?')) return;
            const id = deleteBtn.dataset.id;
            fetch(`/api/users/${id}`, { method: 'DELETE' })
                .then(r => {
                    if (r.ok) {
                        fetchUsers(currentUsersPage);
                    } else {
                        return r.json().then(err => { alert(err.error || 'Ошибка'); });
                    }
                });
        }

        if (resetBtn) {
            if (!confirm('Сбросить пароль этого пользователя?')) return;
            const id = resetBtn.dataset.id;
            fetch(`/api/users/${id}/reset-password`, { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    if (data.new_password) {
                        alert(`Новый пароль: ${data.new_password}\n\nСообщите его пользователю.`);
                    } else if (data.error) {
                        alert(data.error);
                    }
                });
        }
    });
});
