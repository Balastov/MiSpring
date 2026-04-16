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
    const toggleFiltersBtn = document.getElementById('toggle-filters-btn');
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
    const taskDeleteBtn = document.getElementById('task-delete-btn');
    const taskDeleteConfirmModal = document.getElementById('task-delete-confirm-modal');
    const taskDeleteConfirmYes = document.getElementById('task-delete-confirm-yes');
    const taskDeleteConfirmNo = document.getElementById('task-delete-confirm-no');
    const taskDeleteConfirmClose = document.getElementById('task-delete-confirm-close');

    function closeTaskDeleteConfirm() {
        if (taskDeleteConfirmModal) taskDeleteConfirmModal.classList.add('hidden');
    }

    function syncTaskDeleteButtonVisibility() {
        if (!taskDeleteBtn) return;
        if (editingTaskId) taskDeleteBtn.classList.remove('hidden');
        else taskDeleteBtn.classList.add('hidden');
    }

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
    const formPlanStepId = document.getElementById('form-plan-step-id');
    const planStepRow = document.getElementById('plan-step-row');
    const planStepWarning = document.getElementById('plan-step-warning');
    let _pendingAdvancePlanStep = null;
    const formStatusId = document.getElementById('form-status-id');
    const formTaskTypeId = document.getElementById('form-task-type-id');
    const formDuration = document.getElementById('form-duration');
    const formComment = document.getElementById('form-comment');
    const formClosingDate = document.getElementById('form-closing-date');

    // Quick status buttons
    const quickStatusButtons = document.getElementById('quick-status-buttons');
    const btnStatusCompleted = document.getElementById('btn-status-completed');
    const btnStatusCancelled = document.getElementById('btn-status-cancelled');

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
    const homeworkCatalogSelect = document.getElementById('homework-catalog-select');
    const addHomeworkCatalogBtn = document.getElementById('add-homework-catalog-btn');
    const renameHomeworkCatalogBtn = document.getElementById('rename-homework-catalog-btn');
    const deleteHomeworkCatalogBtn = document.getElementById('delete-homework-catalog-btn');
    const homeworkCatalogPlanSelect = document.getElementById('homework-catalog-plan-select');
    const saveHomeworkCatalogBindingBtn = document.getElementById('save-homework-catalog-binding-btn');
    const homeworkCatalogBindingStatus = document.getElementById('homework-catalog-binding-status');
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
    const formHomeworkTopicStepId = document.getElementById('form-homework-topic-step-id');
    const formHomeworkTopicHint = document.getElementById('form-homework-topic-hint');
    const formHomeworkComment = document.getElementById('form-homework-comment');
    const insertHomeworkLinkBtn = document.getElementById('insert-homework-link-btn');
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
    const formUserLessonPriceRow = document.getElementById('form-user-lesson-price-row');
    const formUserLessonPrice = document.getElementById('form-user-lesson-price');
    const formUserTeacherRow = document.getElementById('form-user-teacher-row');
    const formUserTeacherId = document.getElementById('form-user-teacher-id');
    const formUserPhotoRow = document.getElementById('form-user-photo-row');
    const formUserPhotoBtn = document.getElementById('form-user-photo-btn');
    const formUserPhotoInput = document.getElementById('form-user-photo-input');
    const formUserPhotoPreview = document.getElementById('form-user-photo-preview');
    const formUserPhotoName = document.getElementById('form-user-photo-name');
    let _pendingPhotoFile = null;

    // Teacher card (main page)
    const myTeacherCard = document.getElementById('my-teacher-card');
    const myTeacherPhoto = document.getElementById('my-teacher-photo');
    const myTeacherNoPhoto = document.getElementById('my-teacher-no-photo');
    const myTeacherName = document.getElementById('my-teacher-name');

    // Next lesson countdown timer
    const nextLessonTimer = document.getElementById('next-lesson-timer');
    const timerDays = document.getElementById('timer-days');
    const timerHours = document.getElementById('timer-hours');
    const timerMinutes = document.getElementById('timer-minutes');
    const timerSeconds = document.getElementById('timer-seconds');
    let _timerInterval = null;
    let _timerTarget = null;

    function _startCountdown(isoDate) {
        _timerTarget = new Date(isoDate);
        if (_timerInterval) clearInterval(_timerInterval);
        function _tick() {
            const diff = Math.max(0, _timerTarget - Date.now());
            if (diff === 0) {
                clearInterval(_timerInterval);
                nextLessonTimer.classList.add('hidden');
                return;
            }
            const totalSec = Math.floor(diff / 1000);
            const d = Math.floor(totalSec / 86400);
            const h = Math.floor((totalSec % 86400) / 3600);
            const m = Math.floor((totalSec % 3600) / 60);
            const s = totalSec % 60;
            timerDays.textContent = String(d).padStart(2, '0');
            timerHours.textContent = String(h).padStart(2, '0');
            timerMinutes.textContent = String(m).padStart(2, '0');
            timerSeconds.textContent = String(s).padStart(2, '0');
        }
        _tick();
        _timerInterval = setInterval(_tick, 1000);
        nextLessonTimer.classList.remove('hidden');
    }

    // Balance modal elements
    const balanceModal = document.getElementById('balance-modal');
    const balanceModalTitle = document.getElementById('balance-modal-title');
    const balanceModalClose = document.getElementById('balance-modal-close');
    const balanceModalBody = document.getElementById('balance-modal-body');

    // Payment modal elements
    const paymentModal = document.getElementById('payment-modal');
    const paymentModalClose = document.getElementById('payment-modal-close');
    const paymentModalCancel = document.getElementById('payment-modal-cancel');
    const paymentForm = document.getElementById('payment-form');
    const formPayLessons = document.getElementById('form-pay-lessons');
    const formPayAmount = document.getElementById('form-pay-amount');
    const formPayDate = document.getElementById('form-pay-date');
    const formPayNotes = document.getElementById('form-pay-notes');

    // Reports page elements
    const reportsPage = document.getElementById('reports-page');
    const backToMainFromReportsBtn = document.getElementById('back-to-main-from-reports-btn');
    const reportYearSelect = document.getElementById('report-year-select');
    const reportLoadBtn = document.getElementById('report-load-btn');
    const reportContent = document.getElementById('report-content');
    const homeworkReviewPage = document.getElementById('homework-review-page');
    const backToMainFromHomeworkReviewBtn = document.getElementById('back-to-main-from-homework-review-btn');
    const homeworkReviewRefreshBtn = document.getElementById('homework-review-refresh-btn');
    const homeworkReviewWithFilesOnly = document.getElementById('homework-review-with-files-only');
    const homeworkReviewStudentFilter = document.getElementById('homework-review-student-filter');
    const homeworkReviewStatusFilter = document.getElementById('homework-review-status-filter');
    const homeworkReviewTbody = document.getElementById('homework-review-tbody');

    // My Plan page
    const myPlanPage = document.getElementById('my-plan-page');
    const myPlanBtn = document.getElementById('my-plan-btn');
    const planTemplatesPage = document.getElementById('plan-templates-page');

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
    const calendarStepToggleBtn = document.getElementById('calendar-step-toggle-btn');
    const calendarRangeToggleBtn = document.getElementById('calendar-range-toggle-btn');
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
    let useQuarterHourStep = false;
    let useFullDayRange = false;
    let calendar = null;
    let currentTaskStatusesPage = 1;
    let editingStatusId = null;
    let currentTaskTypesPage = 1;
    let editingTaskTypeId = null;
    let currentRolesPage = 1;
    let editingRoleId = null;
    let currentHomeworkPage = 1;
    let editingHomeworkId = null;
    let currentHomeworkCatalogId = null;
    let homeworkCatalogsCache = [];
    let homeworkSecondLevelPlansCache = [];
    let planRootTemplatesCache = [];
    let currentUsersPage = 1;
    let editingUserId = null;
    let currentBalanceStudentId = null;
    let currentBalanceStudentName = null;
    let currentPaymentStudentLessonPrice = null;

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

        // Settings button: visible to all authenticated users
        settingsBtn.style.display = '';

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
            // Show "Мой план" button if student has a plan
            if (hasRole('student') && myPlanBtn) {
                fetch('/api/my-plan')
                    .then(r => { if (r.ok) myPlanBtn.classList.remove('hidden'); })
                    .catch(() => {});
            }
            // Countdown timer for students
            if (hasRole('student') && nextLessonTimer) {
                fetch('/api/my-next-lesson')
                    .then(r => r.json())
                    .then(data => { if (data.lesson) _startCountdown(data.lesson.start_date_iso); })
                    .catch(() => {});
            }
            // Show teacher card for students
            if (hasRole('student') && myTeacherCard) {
                fetch('/api/my-teacher')
                    .then(r => r.json())
                    .then(data => {
                        if (!data.teacher) return;
                        myTeacherCard.classList.remove('hidden');
                        myTeacherName.textContent = data.teacher.display_name;
                        if (data.teacher.photo_url) {
                            myTeacherPhoto.src = data.teacher.photo_url;
                            myTeacherPhoto.classList.remove('hidden');
                            myTeacherNoPhoto.classList.add('hidden');
                        } else {
                            myTeacherPhoto.classList.add('hidden');
                            myTeacherNoPhoto.classList.remove('hidden');
                        }
                    })
                    .catch(() => {});
            }
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

    // Load plan steps for selected student into #form-plan-step-id
    function loadPlanStepsForStudent(studentId, currentPlanStepId = null) {
        if (!formPlanStepId) return;
        const sel = formTaskTypeId.options[formTaskTypeId.selectedIndex];
        const isLesson = sel && sel.textContent === 'Урок';
        if (!isLesson || !studentId) {
            formPlanStepId.innerHTML = '<option value="">-- Выберите этап --</option>';
            if (planStepWarning) planStepWarning.classList.add('hidden');
            return;
        }
        fetch(`/api/students/${studentId}/plan`)
            .then(r => r.json())
            .then(data => {
                formPlanStepId.innerHTML = '<option value="">-- Выберите этап --</option>';
                if (data.error || !data.template) {
                    formPlanStepId.disabled = true;
                    if (planStepWarning) planStepWarning.classList.remove('hidden');
                    return;
                }
                if (planStepWarning) planStepWarning.classList.add('hidden');
                formPlanStepId.disabled = hasRole('student');
                data.steps.forEach(step => {
                    const opt = document.createElement('option');
                    opt.value = step.id;
                    opt.textContent = step.title;
                    formPlanStepId.appendChild(opt);
                });
                if (currentPlanStepId) {
                    formPlanStepId.value = currentPlanStepId;
                } else if (data.next_step_id) {
                    formPlanStepId.value = data.next_step_id;
                } else if (data.steps.length > 0) {
                    formPlanStepId.value = data.steps[0].id;
                }
            })
            .catch(() => {});
    }

    // Show/hide lesson-specific fields based on task type
    function updateLessonFieldsVisibility() {
        const sel = formTaskTypeId.options[formTaskTypeId.selectedIndex];
        const isLesson = sel && sel.textContent === 'Урок';

        // Show/hide student, homework_required, and homework fields
        studentRow.style.display = isLesson ? '' : 'none';
        homeworkRequiredRow.style.display = isLesson ? '' : 'none';
        homeworkRow.style.display = isLesson ? '' : 'none';
        if (planStepRow) planStepRow.style.display = isLesson ? '' : 'none';

        if (!isLesson) {
            formStudentId.value = '';
            formHomeworkRequired.checked = true; // Reset to default
            formHomeworkId.value = '';
            if (formPlanStepId) {
                formPlanStepId.innerHTML = '<option value="">-- Выберите этап --</option>';
                formPlanStepId.disabled = false;
            }
            if (planStepWarning) planStepWarning.classList.add('hidden');
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
        checkAndApplyPrepaid();
        loadPlanStepsForStudent(formStudentId.value);
    });

    function checkAndApplyPrepaid() {
        const studentId = formStudentId.value;
        if (!studentId) {
            formIsPaid.disabled = false;
            return;
        }
        fetch(`/api/students/${studentId}/balance`)
            .then(r => r.json())
            .then(data => {
                if (data.remaining > 0) {
                    formIsPaid.checked = true;
                    formIsPaid.disabled = true;
                    if (data.prepaid_since_iso) {
                        formPaymentDate.value = data.prepaid_since_iso + 'T00:00';
                    } else {
                        const now = new Date();
                        formPaymentDate.value = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
                            .toISOString().slice(0, 16);
                    }
                } else {
                    formIsPaid.disabled = false;
                }
            })
            .catch(() => { formIsPaid.disabled = false; });
    }

    formHomeworkRequired.addEventListener('change', () => {
        autoFillNextHomework();
    });

    // Open modal and auto-fill fields
    toggleFiltersBtn.addEventListener('click', () => {
        const filtersBar = document.getElementById('filters-bar');
        const isHidden = filtersBar.classList.toggle('hidden');
        toggleFiltersBtn.classList.toggle('btn-toggle-filters--active', !isHidden);
    });

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
                formIsPaid.disabled = false;
                formPaymentDate.value = '';
                formHomeworkId.value = '';
                formHomeworkRequired.checked = true;
                formComment.value = '';
                formClosingDate.value = '';
                if (formPlanStepId) formPlanStepId.innerHTML = '<option value="">-- Выберите этап --</option>';
                if (planStepWarning) planStepWarning.classList.add('hidden');

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
                // Default to "В работе" для ДЗ
                const inProgressStatus = statusData.statuses.find(s => s.name === 'В работе');
                if (inProgressStatus) formStatusId.value = inProgressStatus.id;

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
                updateQuickStatusButtons();

                formHomeworkId.innerHTML = '<option value="">-- Выберите --</option>';
                homeworkData.homework.forEach(hw => {
                    const option = document.createElement('option');
                    option.value = hw.id;
                    option.textContent = hw.name;
                    formHomeworkId.appendChild(option);
                });

                modal.classList.remove('hidden');
                syncTaskDeleteButtonVisibility();
            })
            .catch(() => {
                // If fetch fails, still open modal with "Авто"
                formId.value = 'Авто';
                modal.classList.remove('hidden');
                syncTaskDeleteButtonVisibility();
            });
    });

    // Close modal
    function closeModal() {
        closeTaskDeleteConfirm();
        modal.classList.add('hidden');
        taskForm.reset();
        formIsPaid.disabled = false;
        editingTaskId = null;
        syncTaskDeleteButtonVisibility();
    }

    modalClose.addEventListener('click', closeModal);
    modalCancel.addEventListener('click', closeModal);

    if (taskDeleteBtn) {
        taskDeleteBtn.addEventListener('click', () => {
            if (!editingTaskId) return;
            if (taskDeleteConfirmModal) taskDeleteConfirmModal.classList.remove('hidden');
        });
    }
    if (taskDeleteConfirmNo) taskDeleteConfirmNo.addEventListener('click', closeTaskDeleteConfirm);
    if (taskDeleteConfirmClose) taskDeleteConfirmClose.addEventListener('click', closeTaskDeleteConfirm);
    if (taskDeleteConfirmModal) {
        taskDeleteConfirmModal.addEventListener('click', (e) => {
            if (e.target === taskDeleteConfirmModal) closeTaskDeleteConfirm();
        });
    }
    if (taskDeleteConfirmYes) {
        taskDeleteConfirmYes.addEventListener('click', () => {
            if (!editingTaskId) return;
            const id = editingTaskId;
            fetch(`/api/tasks/${id}`, { method: 'DELETE' })
                .then(async (r) => {
                    if (!r.ok) {
                        let msg = 'Не удалось удалить задачу';
                        try {
                            const j = await r.json();
                            if (j && j.error) msg = j.error;
                        } catch (_) { /* 204 или пустое тело */ }
                        throw new Error(msg);
                    }
                    closeTaskDeleteConfirm();
                    closeModal();
                    if (currentView === 'calendar' && calendar) calendar.refetchEvents();
                    fetchTasks(currentPage);
                    showAppToast('Задача удалена');
                })
                .catch((err) => {
                    showAppToast(err.message || 'Ошибка удаления', true);
                    closeTaskDeleteConfirm();
                });
        });
    }

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
        const step = useQuarterHourStep ? '00:15:00' : '00:30:00';
        const slotMinTime = useFullDayRange ? '00:00:00' : '07:00:00';
        const slotMaxTime = useFullDayRange ? '24:00:00' : '23:00:00';
        calendar = new FullCalendar.Calendar(calendarContainer, {
            locale: 'ru',
            firstDay: 1, // Start week on Monday
            initialView: 'timeGridWeek',
            editable: true,
            longPressDelay: 300,
            eventLongPressDelay: 300,
            selectLongPressDelay: 300,
            nowIndicator: true,
            snapDuration: step,
            slotDuration: step,
            slotMinTime: slotMinTime,
            slotMaxTime: slotMaxTime,
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

    function updateCalendarStepToggleButton() {
        if (!calendarStepToggleBtn) return;
        calendarStepToggleBtn.textContent = useQuarterHourStep
            ? 'Убрать шаг в 15 минут'
            : 'Добавить шаг в 15 минут';
        calendarStepToggleBtn.classList.toggle('btn-view-toggle--active', useQuarterHourStep);
    }

    function updateCalendarRangeToggleButton() {
        if (!calendarRangeToggleBtn) return;
        calendarRangeToggleBtn.textContent = useFullDayRange ? 'Сутки' : 'Рабочий день';
        calendarRangeToggleBtn.classList.toggle('btn-view-toggle--active', useFullDayRange);
    }

    function applyCalendarRangeOptions() {
        if (!calendar) return;
        calendar.setOption('slotMinTime', useFullDayRange ? '00:00:00' : '07:00:00');
        calendar.setOption('slotMaxTime', useFullDayRange ? '24:00:00' : '23:00:00');
        calendar.updateSize();
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

            loadPlanStepsForStudent(task.student_id, task.plan_step_id);
            updateQuickStatusButtons();
            checkAndApplyPrepaid();
            modal.classList.remove('hidden');
            syncTaskDeleteButtonVisibility();
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
            fetchTasks();
        }
    });

    if (calendarStepToggleBtn) {
        updateCalendarStepToggleButton();
        calendarStepToggleBtn.addEventListener('click', () => {
            useQuarterHourStep = !useQuarterHourStep;
            updateCalendarStepToggleButton();
            if (!calendar) return;
            const step = useQuarterHourStep ? '00:15:00' : '00:30:00';
            calendar.setOption('snapDuration', step);
            calendar.setOption('slotDuration', step);
            calendar.updateSize();
        });
    }

    if (calendarRangeToggleBtn) {
        updateCalendarRangeToggleButton();
        calendarRangeToggleBtn.addEventListener('click', () => {
            useFullDayRange = !useFullDayRange;
            updateCalendarRangeToggleButton();
            applyCalendarRangeOptions();
        });
    }

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

            // Plan step required for new lessons when student has a plan
            if (!editingTaskId && formPlanStepId && !formPlanStepId.disabled && !formPlanStepId.value
                    && formPlanStepId.options.length > 1) {
                alert('Этап плана обучения обязателен');
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
            closing_date: formClosingDate.value || null,
            plan_step_id: formPlanStepId && formPlanStepId.value ? parseInt(formPlanStepId.value) : null,
        };

        if (_pendingAdvancePlanStep !== null) {
            taskData.advance_plan_step = _pendingAdvancePlanStep;
            _pendingAdvancePlanStep = null;
        }

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

    // Quick status buttons handlers
    function updateTaskStatus(statusName) {
        if (!editingTaskId) {
            alert('Ошибка: задача не открыта для редактирования');
            return;
        }

        // Find status by name
        const statusOptions = Array.from(formStatusId.options);
        const statusOption = statusOptions.find(opt => opt.textContent === statusName);

        if (!statusOption) {
            alert(`Статус "${statusName}" не найден`);
            return;
        }

        // Set status
        formStatusId.value = statusOption.value;

        // Trigger form submit
        taskForm.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    }

    if (btnStatusCompleted) {
        btnStatusCompleted.addEventListener('click', () => {
            showConductedDialog();
        });
    }

    function showConductedDialog() {
        const dlg = document.getElementById('conducted-dialog-modal');
        if (!dlg) { updateTaskStatus('Проведён'); return; }

        // Reset state
        dlg.querySelectorAll('.toggle-ans-btn').forEach(b => b.classList.remove('active'));
        const testMsg = document.getElementById('test-soon-msg');
        if (testMsg) testMsg.classList.add('hidden');
        const confirmBtn = document.getElementById('conducted-confirm-btn');
        if (confirmBtn) confirmBtn.disabled = true;
        dlg.classList.remove('hidden');

        const answers = { test: null, advance: null };

        function checkBothAnswered() {
            if (confirmBtn) confirmBtn.disabled = answers.test === null || answers.advance === null;
        }

        dlg.querySelectorAll('.toggle-ans-btn').forEach(btn => {
            btn.onclick = () => {
                const q = btn.closest('.toggle-answer').dataset.q;
                btn.closest('.toggle-answer').querySelectorAll('.toggle-ans-btn')
                    .forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                answers[q] = btn.dataset.val;
                if (q === 'test' && testMsg) {
                    testMsg.classList.toggle('hidden', btn.dataset.val !== 'yes');
                }
                checkBothAnswered();
            };
        });

        if (confirmBtn) {
            confirmBtn.onclick = () => {
                dlg.classList.add('hidden');
                _pendingAdvancePlanStep = answers.advance === 'yes';
                updateTaskStatus('Проведён');
            };
        }

        const cancelBtn = document.getElementById('conducted-cancel-btn');
        if (cancelBtn) {
            cancelBtn.onclick = () => dlg.classList.add('hidden');
        }
    }

    if (btnStatusCancelled) {
        btnStatusCancelled.addEventListener('click', () => {
            updateTaskStatus('Отменён');
        });
    }

    // Show/hide quick status buttons based on task type
    function updateQuickStatusButtons() {
        if (!quickStatusButtons || !formTaskTypeId) return;
        const selectedTypeOption = formTaskTypeId.options[formTaskTypeId.selectedIndex];
        const isLessonType = selectedTypeOption && selectedTypeOption.textContent === 'Урок';
        const isEditing = !!editingTaskId;

        if (isLessonType && isEditing) {
            quickStatusButtons.classList.remove('hidden');
        } else {
            quickStatusButtons.classList.add('hidden');
        }
    }

    // Update buttons when task type changes
    if (formTaskTypeId) formTaskTypeId.addEventListener('change', updateQuickStatusButtons);

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
                    updateQuickStatusButtons();

                    // Populate homework dropdown
                    formHomeworkId.innerHTML = '<option value="">-- Выберите --</option>';
                    homeworkData.homework.forEach(hw => {
                        const option = document.createElement('option');
                        option.value = hw.id;
                        option.textContent = hw.name;
                        formHomeworkId.appendChild(option);
                    });
                    formHomeworkId.value = task.homework_id || '';

                    loadPlanStepsForStudent(task.student_id, task.plan_step_id);
                    modal.classList.remove('hidden');
                    syncTaskDeleteButtonVisibility();
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

    function showAppToast(message, isError = false) {
        let stack = document.getElementById('app-toast-stack');
        if (!stack) {
            stack = document.createElement('div');
            stack.id = 'app-toast-stack';
            stack.className = 'app-toast-stack';
            stack.setAttribute('aria-live', 'polite');
            document.body.appendChild(stack);
        }
        const toast = document.createElement('div');
        toast.className = `app-toast ${isError ? 'app-toast-error' : 'app-toast-success'}`;
        toast.textContent = message;
        stack.appendChild(toast);
        setTimeout(() => toast.remove(), 2800);
    }

    // ========== Settings Modal Logic ==========

    // Open settings modal
    settingsBtn.addEventListener('click', () => {
        const allOptionBtns = settingsModal.querySelectorAll('.settings-option-btn');
        const isPrivileged = hasRole('admin', 'owner', 'teacher');
        allOptionBtns.forEach(btn => {
            if (isPrivileged) {
                btn.style.display = '';
            } else {
                btn.style.display = ['users', 'telegram'].includes(btn.dataset.option) ? '' : 'none';
            }
        });
        // plan-templates никогда не показываем не-привилегированным
        const planTemplatesBtn = settingsModal.querySelector('[data-option="plan-templates"]');
        if (planTemplatesBtn) planTemplatesBtn.style.display = isPrivileged ? '' : 'none';
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
            } else if (option === 'telegram') {
                showTelegramPage();
            } else if (option === 'reports') {
                showReportsPage();
            } else if (option === 'homework-review') {
                showHomeworkReviewPage();
            } else if (option === 'plan-templates') {
                showPlanTemplatesPage();
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
        if (reportsPage) reportsPage.classList.add('hidden');
        if (telegramPage) telegramPage.classList.add('hidden');
        if (myPlanPage) myPlanPage.classList.add('hidden');
        if (planTemplatesPage) planTemplatesPage.classList.add('hidden');
        if (homeworkReviewPage) homeworkReviewPage.classList.add('hidden');
    }

    function showMainPage() {
        hideAllPages();
        document.querySelector('.container').classList.remove('hidden');
    }

    // ========== Telegram Page Logic ==========

    const telegramPage = document.getElementById('telegram-page');
    const backToMainFromTelegramBtn = document.getElementById('back-to-main-from-telegram-btn');
    const telegramStatusInfo = document.getElementById('telegram-status-info');
    const telegramNotBound = document.getElementById('telegram-not-bound');
    const telegramBound = document.getElementById('telegram-bound');
    const generateCodeBtn = document.getElementById('generate-code-btn');
    const bindingCodeDisplay = document.getElementById('binding-code-display');
    const bindingCodeValue = document.getElementById('binding-code-value');
    const codeHint = document.getElementById('code-hint');
    const boundTelegramId = document.getElementById('bound-telegram-id');
    const boundTelegramUsername = document.getElementById('bound-telegram-username');
    const notificationsToggle = document.getElementById('notifications-toggle');
    const unbindTelegramBtn = document.getElementById('unbind-telegram-btn');
    const integrationMeetingLinkInput = document.getElementById('integration-meeting-link-input');
    const integrationSaveMeetingLinkBtn = document.getElementById('integration-save-meeting-link-btn');
    const integrationMeetingLinkStatus = document.getElementById('integration-meeting-link-status');

    function showTelegramPage() {
        hideAllPages();
        telegramPage.classList.remove('hidden');
        loadTelegramStatus();
        loadIntegrationMeetingLink();
    }

    function loadIntegrationMeetingLink() {
        if (!integrationMeetingLinkInput) return;
        const canManageMeetingLink = hasRole('admin', 'owner', 'teacher');
        integrationMeetingLinkInput.disabled = !canManageMeetingLink;
        if (integrationSaveMeetingLinkBtn) integrationSaveMeetingLinkBtn.style.display = canManageMeetingLink ? '' : 'none';
        fetch('/api/settings/meeting_link')
            .then(r => r.json())
            .then(data => {
                integrationMeetingLinkInput.value = data.value || '';
                if (!canManageMeetingLink && integrationMeetingLinkStatus) {
                    integrationMeetingLinkStatus.textContent = 'Редактирование доступно учителю, владельцу и администратору.';
                } else if (integrationMeetingLinkStatus) {
                    integrationMeetingLinkStatus.textContent = '';
                }
            })
            .catch(() => {
                if (integrationMeetingLinkStatus) integrationMeetingLinkStatus.textContent = 'Ошибка загрузки ссылки';
            });
    }

    function loadTelegramStatus() {
        telegramStatusInfo.innerHTML = '<p class="loading">Загрузка...</p>';
        telegramNotBound.classList.add('hidden');
        telegramBound.classList.add('hidden');
        bindingCodeDisplay.classList.add('hidden');

        fetch('/api/telegram/status')
            .then(r => r.json())
            .then(data => {
                if (data.is_bound) {
                    // Show bound state
                    telegramStatusInfo.innerHTML = '<p class="status-bound">✓ Telegram привязан</p>';
                    telegramBound.classList.remove('hidden');
                    boundTelegramId.textContent = data.telegram_id || '—';
                    boundTelegramUsername.textContent = data.telegram_username ? '@' + data.telegram_username : '—';
                    notificationsToggle.checked = data.notifications_enabled;
                } else {
                    // Show not bound state
                    telegramStatusInfo.innerHTML = '<p class="status-not-bound">Telegram не привязан</p>';
                    telegramNotBound.classList.remove('hidden');

                    // If there's a pending code, show it
                    if (data.pending_code) {
                        bindingCodeValue.textContent = data.pending_code;
                        codeHint.textContent = data.pending_code;
                        bindingCodeDisplay.classList.remove('hidden');
                    }
                }
            })
            .catch(err => {
                telegramStatusInfo.innerHTML = '<p style="color: red;">Ошибка загрузки статуса</p>';
                console.error(err);
            });
    }

    backToMainFromTelegramBtn.addEventListener('click', showMainPage);

    generateCodeBtn.addEventListener('click', () => {
        generateCodeBtn.disabled = true;
        generateCodeBtn.textContent = 'Генерация...';

        fetch('/api/telegram/generate-code', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                if (data.code) {
                    bindingCodeValue.textContent = data.code;
                    codeHint.textContent = data.code;
                    bindingCodeDisplay.classList.remove('hidden');
                } else if (data.error) {
                    alert('Ошибка: ' + data.error);
                }
            })
            .catch(err => {
                alert('Ошибка генерации кода');
                console.error(err);
            })
            .finally(() => {
                generateCodeBtn.disabled = false;
                generateCodeBtn.textContent = 'Сгенерировать код';
            });
    });

    notificationsToggle.addEventListener('change', () => {
        const enabled = notificationsToggle.checked;

        fetch('/api/telegram/notifications', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    alert(enabled ? 'Уведомления включены' : 'Уведомления выключены');
                } else if (data.error) {
                    alert('Ошибка: ' + data.error);
                    notificationsToggle.checked = !enabled; // Revert
                }
            })
            .catch(err => {
                alert('Ошибка обновления настроек');
                notificationsToggle.checked = !enabled; // Revert
                console.error(err);
            });
    });

    unbindTelegramBtn.addEventListener('click', () => {
        if (!confirm('Вы уверены, что хотите отвязать Telegram аккаунт?')) {
            return;
        }

        unbindTelegramBtn.disabled = true;
        unbindTelegramBtn.textContent = 'Отвязка...';

        fetch('/api/telegram/unbind', { method: 'DELETE' })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    alert('Telegram отвязан');
                    loadTelegramStatus(); // Reload
                } else if (data.error) {
                    alert('Ошибка: ' + data.error);
                }
            })
            .catch(err => {
                alert('Ошибка отвязки');
                console.error(err);
            })
            .finally(() => {
                unbindTelegramBtn.disabled = false;
                unbindTelegramBtn.textContent = 'Отвязать Telegram';
            });
    });

    if (integrationSaveMeetingLinkBtn) {
        integrationSaveMeetingLinkBtn.addEventListener('click', () => {
            fetch('/api/settings/meeting_link', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ value: integrationMeetingLinkInput.value.trim() }),
            })
            .then(r => r.json())
            .then(() => {
                if (integrationMeetingLinkStatus) {
                    integrationMeetingLinkStatus.textContent = 'Сохранено ✓';
                    setTimeout(() => { integrationMeetingLinkStatus.textContent = ''; }, 3000);
                }
            })
            .catch(() => {
                if (integrationMeetingLinkStatus) integrationMeetingLinkStatus.textContent = 'Ошибка сохранения';
            });
        });
    }

    // ========== ICS Calendar Sync ==========

    const copyIcsBtn = document.getElementById('copy-ics-btn');
    const icsCopyHint = document.getElementById('ics-copy-hint');

    if (copyIcsBtn) {
        copyIcsBtn.addEventListener('click', () => {
            fetch('/api/user/calendar-token')
                .then(r => r.json())
                .then(data => {
                    navigator.clipboard.writeText(data.url).then(() => {
                        icsCopyHint.textContent = 'Ссылка скопирована: ' + data.url;
                        icsCopyHint.classList.remove('hidden');
                    }).catch(() => {
                        // Fallback for browsers that block clipboard API
                        icsCopyHint.textContent = data.url;
                        icsCopyHint.classList.remove('hidden');
                    });
                })
                .catch(() => alert('Ошибка получения ссылки'));
        });
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

    function _escapeAttr(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    if (insertHomeworkLinkBtn) {
        insertHomeworkLinkBtn.addEventListener('click', () => {
            const selection = window.getSelection();
            let selectedText = '';
            if (selection && selection.rangeCount > 0) {
                selectedText = selection.toString().trim();
            }
            const visibleText = prompt('Видимый текст ссылки:', selectedText || 'Открыть материал');
            if (!visibleText || !visibleText.trim()) return;
            let url = prompt('URL ссылки (https://...):', 'https://');
            if (!url || !url.trim()) return;
            url = url.trim();
            if (!/^https?:\/\//i.test(url)) {
                url = `https://${url}`;
            }
            const safeText = escapeHtml(visibleText.trim());
            const safeHref = _escapeAttr(url);
            formHomeworkComment.focus();
            document.execCommand('insertHTML', false, `<a href="${safeHref}" target="_blank" rel="noopener">${safeText}</a>`);
        });
    }

    // ========== Homework Page Logic ==========

    function getSelectedHomeworkCatalog() {
        if (!homeworkCatalogsCache.length || !currentHomeworkCatalogId) return null;
        return homeworkCatalogsCache.find(c => c.id === currentHomeworkCatalogId) || null;
    }

    function renderHomeworkCatalogStatus() {
        if (!homeworkCatalogBindingStatus) return;
        const c = getSelectedHomeworkCatalog();
        if (!c || !c.plan_template_id) {
            homeworkCatalogBindingStatus.textContent = 'Справочник не привязан к плану обучения';
            homeworkCatalogBindingStatus.classList.add('unbound');
            return;
        }
        homeworkCatalogBindingStatus.textContent = `Привязан к плану: ${c.plan_template_name || '—'}`;
        homeworkCatalogBindingStatus.classList.remove('unbound');
    }

    function fillHomeworkCatalogPlanOptions() {
        if (!homeworkCatalogPlanSelect) return;
        const options = ['<option value="">— без привязки —</option>']
            .concat(homeworkSecondLevelPlansCache.map(t => `<option value="${t.id}">${escapeHtml(t.full_name || t.name)}</option>`));
        homeworkCatalogPlanSelect.innerHTML = options.join('');
        const c = getSelectedHomeworkCatalog();
        if (c && c.plan_template_id) {
            homeworkCatalogPlanSelect.value = String(c.plan_template_id);
        } else {
            homeworkCatalogPlanSelect.value = '';
        }
    }

    function fillHomeworkCatalogSelect() {
        if (!homeworkCatalogSelect) return;
        if (!homeworkCatalogsCache.length) {
            homeworkCatalogSelect.innerHTML = '<option value="">Нет справочников</option>';
            currentHomeworkCatalogId = null;
            fillHomeworkCatalogPlanOptions();
            renderHomeworkCatalogStatus();
            return;
        }
        homeworkCatalogSelect.innerHTML = homeworkCatalogsCache
            .map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`)
            .join('');
        const exists = homeworkCatalogsCache.some(c => c.id === currentHomeworkCatalogId);
        if (!exists) currentHomeworkCatalogId = homeworkCatalogsCache[0].id;
        homeworkCatalogSelect.value = String(currentHomeworkCatalogId);
        fillHomeworkCatalogPlanOptions();
        renderHomeworkCatalogStatus();
    }

    function loadHomeworkTopicSteps(selectedStepId = null) {
        if (!formHomeworkTopicStepId || !formHomeworkTopicHint) return Promise.resolve();
        if (!currentHomeworkCatalogId) {
            formHomeworkTopicStepId.innerHTML = '<option value="">-- Не выбрано --</option>';
            formHomeworkTopicStepId.disabled = true;
            formHomeworkTopicHint.textContent = 'Сначала выберите справочник.';
            return Promise.resolve();
        }
        return fetch(`/api/homework-catalogs/${currentHomeworkCatalogId}/plan-steps`)
            .then(r => r.json())
            .then(data => {
                const steps = data.steps || [];
                formHomeworkTopicStepId.innerHTML = '<option value="">-- Не выбрано --</option>';
                if (!steps.length) {
                    formHomeworkTopicStepId.disabled = true;
                    formHomeworkTopicHint.textContent = 'Справочник не привязан к плану обучения.';
                    return;
                }
                formHomeworkTopicStepId.disabled = false;
                formHomeworkTopicHint.textContent = 'Выберите шаг из привязанного плана.';
                steps.forEach(step => {
                    const opt = document.createElement('option');
                    opt.value = step.id;
                    opt.textContent = step.title;
                    formHomeworkTopicStepId.appendChild(opt);
                });
                if (selectedStepId) {
                    formHomeworkTopicStepId.value = String(selectedStepId);
                }
            })
            .catch(() => {
                formHomeworkTopicStepId.innerHTML = '<option value="">-- Не выбрано --</option>';
                formHomeworkTopicStepId.disabled = true;
                formHomeworkTopicHint.textContent = 'Не удалось загрузить шаги плана.';
            });
    }

    function loadHomeworkCatalogs(preferredCatalogId = null) {
        return Promise.all([
            fetch('/api/homework-catalogs').then(r => r.json()),
            fetch('/api/plan-templates').then(r => r.json()),
        ]).then(([catalogData, plansData]) => {
            homeworkCatalogsCache = catalogData.catalogs || [];
            homeworkSecondLevelPlansCache = _flattenSecondLevelTemplates(plansData.templates || []);
            if (preferredCatalogId) currentHomeworkCatalogId = preferredCatalogId;
            fillHomeworkCatalogSelect();
        });
    }

    function showHomeworkPage() {
        hideAllPages();
        homeworkPage.classList.remove('hidden');
        currentHomeworkPage = 1;
        loadHomeworkCatalogs().then(() => fetchHomework()).catch(() => fetchHomework());
    }

    backToMainFromHomeworkBtn.addEventListener('click', showMainPage);

    function fetchHomework(page) {
        if (page !== undefined) currentHomeworkPage = page;
        const params = new URLSearchParams({ page: String(currentHomeworkPage) });
        if (currentHomeworkCatalogId) params.set('catalog_id', String(currentHomeworkCatalogId));
        fetch(`/api/homework?${params.toString()}`)
            .then(r => r.json())
            .then(data => {
                renderHomework(data.homework);
                renderHomeworkPagination(data);
            });
    }

    function renderHomework(items) {
        homeworkTbody.innerHTML = '';
        if (items.length === 0) {
            homeworkTbody.innerHTML = '<tr><td colspan="6" class="empty-msg">Домашних заданий нет</td></tr>';
            return;
        }
        items.forEach(hw => {
            const tr = document.createElement('tr');
            const commentHtml = hw.comment ? sanitizeHtml(hw.comment) : '—';
            tr.innerHTML = `
                <td>${hw.id}</td>
                <td>${escapeHtml(hw.name)}</td>
                <td>${escapeHtml(hw.topic_title || '—')}</td>
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
        if (!currentHomeworkCatalogId) {
            alert('Сначала создайте и выберите справочник домашних заданий');
            return;
        }
        const params = new URLSearchParams({ page: '1', catalog_id: String(currentHomeworkCatalogId) });
        fetch(`/api/homework?${params.toString()}`)
            .then(r => r.json())
            .then(data => {
                editingHomeworkId = null;
                homeworkModalTitle.textContent = 'Создание домашнего задания';
                homeworkSubmitBtn.textContent = 'Подтвердить и создать';
                formHomeworkIdDisplay.value = data.next_id;
                formHomeworkName.value = '';
                formHomeworkComment.innerHTML = '';
                loadHomeworkTopicSteps().then(() => {
                    formHomeworkTopicStepId.value = '';
                    homeworkModal.classList.remove('hidden');
                });
            });
    });

    function closeHomeworkModal() {
        homeworkModal.classList.add('hidden');
        homeworkForm.reset();
        if (formHomeworkTopicStepId) formHomeworkTopicStepId.innerHTML = '<option value="">-- Не выбрано --</option>';
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
            catalog_id: currentHomeworkCatalogId,
            plan_step_id: formHomeworkTopicStepId && formHomeworkTopicStepId.value ? parseInt(formHomeworkTopicStepId.value) : null,
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
            const params = new URLSearchParams({ page: String(currentHomeworkPage) });
            if (currentHomeworkCatalogId) params.set('catalog_id', String(currentHomeworkCatalogId));
            fetch(`/api/homework?${params.toString()}`)
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
                    loadHomeworkTopicSteps(hw.plan_step_id).then(() => {
                        homeworkModal.classList.remove('hidden');
                    });
                });
        }

        if (deleteBtn) {
            if (!confirm('Удалить это домашнее задание?')) return;
            const id = deleteBtn.dataset.id;
            fetch(`/api/homework/${id}`, { method: 'DELETE' })
                .then(() => fetchHomework(currentHomeworkPage));
        }
    });

    if (homeworkCatalogSelect) {
        homeworkCatalogSelect.addEventListener('change', () => {
            currentHomeworkCatalogId = parseInt(homeworkCatalogSelect.value) || null;
            fillHomeworkCatalogPlanOptions();
            renderHomeworkCatalogStatus();
            currentHomeworkPage = 1;
            fetchHomework();
        });
    }

    if (addHomeworkCatalogBtn) {
        addHomeworkCatalogBtn.addEventListener('click', () => {
            const name = prompt('Название нового справочника:');
            if (!name || !name.trim()) return;
            fetch('/api/homework-catalogs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name.trim() }),
            }).then(r => r.json()).then(data => {
                if (data.error) throw new Error(data.error);
                return loadHomeworkCatalogs(data.id).then(() => fetchHomework(1));
            }).catch(err => alert(err.message || 'Не удалось создать справочник'));
        });
    }

    if (renameHomeworkCatalogBtn) {
        renameHomeworkCatalogBtn.addEventListener('click', () => {
            const c = getSelectedHomeworkCatalog();
            if (!c) return;
            const name = prompt('Новое название справочника:', c.name);
            if (!name || !name.trim()) return;
            fetch(`/api/homework-catalogs/${c.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name.trim() }),
            }).then(r => r.json()).then(data => {
                if (data.error) throw new Error(data.error);
                return loadHomeworkCatalogs(c.id);
            }).catch(err => alert(err.message || 'Не удалось переименовать справочник'));
        });
    }

    if (deleteHomeworkCatalogBtn) {
        deleteHomeworkCatalogBtn.addEventListener('click', () => {
            const c = getSelectedHomeworkCatalog();
            if (!c) return;
            if (!confirm(`Удалить справочник "${c.name}" и все его домашние задания?`)) return;
            fetch(`/api/homework-catalogs/${c.id}`, { method: 'DELETE' })
                .then(() => loadHomeworkCatalogs().then(() => fetchHomework(1)))
                .catch(() => alert('Не удалось удалить справочник'));
        });
    }

    if (saveHomeworkCatalogBindingBtn) {
        saveHomeworkCatalogBindingBtn.addEventListener('click', () => {
            const c = getSelectedHomeworkCatalog();
            if (!c) return;
            const templateId = homeworkCatalogPlanSelect && homeworkCatalogPlanSelect.value
                ? parseInt(homeworkCatalogPlanSelect.value)
                : null;
            fetch(`/api/homework-catalogs/${c.id}/binding`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ plan_template_id: templateId }),
            })
                .then(r => r.json())
                .then(data => {
                    if (data.error) throw new Error(data.error);
                    return loadHomeworkCatalogs(c.id);
                })
                .catch(err => alert(err.message || 'Не удалось сохранить привязку'));
        });
    }

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
        if (!hasRole('admin', 'owner', 'teacher')) {
            if (currentUserData) renderUsers([currentUserData]);
            return;
        }
        fetch(`/api/users?page=${currentUsersPage}`)
            .then(r => r.json())
            .then(data => {
                renderUsers(data.users);
                renderUsersPagination(data);
            });
    }

    function renderUsers(users) {
        const canManage = hasRole('admin', 'owner', 'teacher');
        const usersTheadRow = document.querySelector('#users-table thead tr');

        if (canManage) {
            usersTheadRow.innerHTML = `
                <th>ID</th><th>Логин</th><th>Имя</th><th>Роли</th>
                <th>Источник</th><th>Активен</th><th>Дата создания</th>
                <th>Telegram ID</th><th>Telegram Username</th><th>Уведомления TG</th>
                <th></th><th></th><th></th><th></th>`;
        } else {
            usersTheadRow.innerHTML = `
                <th>Логин</th><th>Имя</th><th>Дата создания</th>
                <th>Telegram Username</th><th></th>`;
        }

        usersTbody.innerHTML = '';
        if (users.length === 0) {
            usersTbody.innerHTML = `<tr><td colspan="${canManage ? 14 : 5}" class="empty-msg">Пользователей нет</td></tr>`;
            return;
        }

        const sourceLabels = { local: 'Локальный', yandex: 'Яндекс', vk: 'ВКонтакте' };

        users.forEach(user => {
            const tr = document.createElement('tr');
            if (canManage) {
                const isStudent = user.roles.includes('student');
                const balanceBtn = isStudent
                    ? `<button class="btn-balance" data-id="${user.id}" data-name="${escapeAttr(user.display_name)}">Баланс</button>`
                    : '';
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
                    <td>${balanceBtn}</td>`;
            } else {
                tr.innerHTML = `
                    <td>${escapeHtml(user.username)}</td>
                    <td>${escapeHtml(user.display_name)}</td>
                    <td>${user.created_at || '—'}</td>
                    <td>${user.telegram_username ? escapeHtml(user.telegram_username) : '—'}</td>
                    <td><button class="btn-reset-password" data-id="${user.id}">Сбросить пароль</button></td>`;
            }
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

                // Hide lesson_price, teacher, photo for new users
                formUserLessonPriceRow.classList.add('hidden');
                formUserLessonPrice.value = '';
                formUserTeacherRow.classList.add('hidden');
                formUserPhotoRow.classList.add('hidden');
                formUserPhotoPreview.classList.add('hidden');
                _pendingPhotoFile = null;

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
        _pendingPhotoFile = null;
        formUserPhotoPreview.classList.add('hidden');
        formUserPhotoName.textContent = 'макс. 5 МБ';
    }

    if (formUserPhotoBtn) {
        formUserPhotoBtn.addEventListener('click', () => formUserPhotoInput.click());
    }
    if (formUserPhotoInput) {
        formUserPhotoInput.addEventListener('change', () => {
            const file = formUserPhotoInput.files[0];
            if (!file) return;
            if (file.size > 5 * 1024 * 1024) {
                alert('Файл слишком большой (макс. 5 МБ)');
                formUserPhotoInput.value = '';
                return;
            }
            _pendingPhotoFile = file;
            formUserPhotoName.textContent = file.name;
            const reader = new FileReader();
            reader.onload = (ev) => {
                formUserPhotoPreview.src = ev.target.result;
                formUserPhotoPreview.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        });
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
            // Update — sequential to avoid SQLite locking
            if (!formUserTeacherRow.classList.contains('hidden')) {
                userData.teacher_id = formUserTeacherId.value ? parseInt(formUserTeacherId.value) : null;
            }

            const checkOk = r => r.ok ? Promise.resolve() : r.json().then(e => { throw new Error(e.error || 'Ошибка'); });

            fetch(`/api/users/${editingUserId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userData)
            })
            .then(checkOk)
            .then(() => {
                if (!formUserLessonPriceRow.classList.contains('hidden')) {
                    const priceVal = formUserLessonPrice.value;
                    return fetch(`/api/students/${editingUserId}/lesson-price`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ lesson_price: priceVal === '' ? null : parseFloat(priceVal) })
                    }).then(checkOk);
                }
            })
            .then(() => {
                if (_pendingPhotoFile) {
                    const fd = new FormData();
                    fd.append('photo', _pendingPhotoFile);
                    return fetch(`/api/users/${editingUserId}/photo`, { method: 'POST', body: fd }).then(checkOk);
                }
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

                    // Show lesson_price for students (teacher/admin only)
                    const isStudent = user.roles.includes('student');
                    const isTeacher = user.roles.includes('teacher');
                    const canManage = hasRole('admin', 'owner', 'teacher');
                    const canManageAdmin = hasRole('admin', 'owner');
                    if (isStudent && canManage) {
                        formUserLessonPriceRow.classList.remove('hidden');
                        formUserLessonPrice.value = user.lesson_price != null ? user.lesson_price : '';
                    } else {
                        formUserLessonPriceRow.classList.add('hidden');
                        formUserLessonPrice.value = '';
                    }

                    // Teacher selector for students (admin/owner only)
                    if (isStudent && canManageAdmin) {
                        fetch('/api/teachers').then(r => r.json()).then(td => {
                            formUserTeacherId.innerHTML = '<option value="">— не назначен —</option>'
                                + (td.teachers || []).map(t => `<option value="${t.id}">${t.display_name}</option>`).join('');
                            if (user.teacher_id) formUserTeacherId.value = user.teacher_id;
                        });
                        formUserTeacherRow.classList.remove('hidden');
                    } else {
                        formUserTeacherRow.classList.add('hidden');
                        formUserTeacherId.innerHTML = '<option value="">— не назначен —</option>';
                    }

                    // Photo upload for teachers (admin/owner only)
                    if (isTeacher && canManageAdmin) {
                        formUserPhotoRow.classList.remove('hidden');
                        _pendingPhotoFile = null;
                        formUserPhotoInput.value = '';
                        formUserPhotoName.textContent = 'макс. 5 МБ';
                        if (user.teacher_photo) {
                            formUserPhotoPreview.src = `/static/uploads/teacher_photos/${user.teacher_photo}`;
                            formUserPhotoPreview.classList.remove('hidden');
                        } else {
                            formUserPhotoPreview.classList.add('hidden');
                        }
                    } else {
                        formUserPhotoRow.classList.add('hidden');
                        formUserPhotoPreview.classList.add('hidden');
                        _pendingPhotoFile = null;
                    }

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

        const balBtn = e.target.closest('.btn-balance');
        if (balBtn) {
            const id = parseInt(balBtn.dataset.id);
            const name = balBtn.dataset.name;
            openBalanceModal(id, name);
        }
    });

    // ========== Balance Modal Logic ==========

    function openBalanceModal(studentId, studentName) {
        currentBalanceStudentId = studentId;
        currentBalanceStudentName = studentName;
        balanceModalTitle.textContent = `Баланс: ${studentName}`;
        balanceModalBody.innerHTML = '<p class="loading">Загрузка...</p>';
        balanceModal.classList.remove('hidden');
        loadBalanceData(studentId, studentName);
    }

    function loadBalanceData(studentId, studentName) {
        fetch(`/api/students/${studentId}/balance`)
            .then(r => r.json())
            .then(data => renderBalanceContent(data, studentId, studentName))
            .catch(() => {
                balanceModalBody.innerHTML = '<p>Ошибка загрузки</p>';
            });
    }

    function renderBalanceContent(data, studentId, studentName) {
        const canManage = hasRole('admin', 'owner', 'teacher');
        const remaining = data.remaining || 0;
        const remainingClass = remaining <= 1 ? 'balance-stat--warning' : '';

        let lessonPriceHtml = '';
        if (canManage) {
            lessonPriceHtml = `
            <div class="balance-lesson-price">
                <label>Стоимость урока (₽):</label>
                <div class="lesson-price-row">
                    <input type="number" id="balance-lesson-price-input" class="form-control" value="${data.lesson_price != null ? data.lesson_price : ''}" min="0" step="1" placeholder="не задана">
                    <button type="button" class="btn-primary btn-sm" id="save-lesson-price-btn">Сохранить</button>
                </div>
            </div>`;
        }

        let paymentsHtml = '';
        if (data.payments && data.payments.length > 0) {
            paymentsHtml = data.payments.map(p => `
                <div class="payment-item">
                    <span class="payment-date">${p.payment_date || '—'}</span>
                    <span class="payment-lessons">${p.lessons_count} ур.</span>
                    <span class="payment-amount">${p.amount != null ? p.amount.toFixed(0) + ' ₽' : '—'}</span>
                    <span class="payment-notes">${escapeHtml(p.notes || '')}</span>
                    ${canManage ? `<button class="btn-delete-payment" data-payment-id="${p.id}" title="Удалить">×</button>` : ''}
                </div>
            `).join('');
        } else {
            paymentsHtml = '<p class="empty-msg">Платежей нет</p>';
        }

        balanceModalBody.innerHTML = `
            ${lessonPriceHtml}
            <div class="balance-stats">
                <div class="balance-stat">
                    <span class="balance-stat-label">Всего оплачено</span>
                    <span class="balance-stat-value">${data.total_paid}</span>
                    <span class="balance-stat-unit">уроков</span>
                </div>
                <div class="balance-stat">
                    <span class="balance-stat-label">Проведено</span>
                    <span class="balance-stat-value">${data.conducted}</span>
                    <span class="balance-stat-unit">уроков</span>
                </div>
                <div class="balance-stat ${remainingClass}">
                    <span class="balance-stat-label">Остаток</span>
                    <span class="balance-stat-value">${remaining}</span>
                    <span class="balance-stat-unit">уроков</span>
                </div>
                ${data.prepaid_since ? `
                <div class="balance-stat">
                    <span class="balance-stat-label">Предоплата с</span>
                    <span class="balance-stat-value balance-stat-value--date">${data.prepaid_since}</span>
                </div>` : ''}
            </div>
            <div class="payments-section">
                <h3 class="payments-title">История платежей</h3>
                <div id="payments-list">${paymentsHtml}</div>
                ${canManage ? `<button type="button" class="btn-primary btn-sm" id="add-payment-btn" style="margin-top:12px">+ Добавить оплату</button>` : ''}
                ${hasRole('admin', 'owner') ? `<button type="button" class="btn-secondary btn-sm" id="test-notification-btn" style="margin-top:12px">Тест: уведомление</button>` : ''}
            </div>
        `;

        if (canManage) {
            document.getElementById('save-lesson-price-btn').addEventListener('click', () => {
                const price = document.getElementById('balance-lesson-price-input').value;
                fetch(`/api/students/${studentId}/lesson-price`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ lesson_price: price === '' ? null : parseFloat(price) })
                })
                .then(r => r.json())
                .then(() => loadBalanceData(studentId, studentName))
                .catch(() => alert('Ошибка сохранения'));
            });

            document.getElementById('add-payment-btn').addEventListener('click', () => {
                openPaymentModal(studentId, data.lesson_price);
            });

            if (hasRole('admin', 'owner')) {
                document.getElementById('test-notification-btn').addEventListener('click', (e) => {
                    const btn = e.currentTarget;
                    btn.disabled = true;
                    btn.textContent = 'Отправка...';
                    fetch(`/api/students/${studentId}/test-notification`, { method: 'POST' })
                        .then(r => r.json())
                        .then(res => {
                            if (res.ok) {
                                btn.textContent = 'Отправлено ✓ → ' + res.sent_to.join(', ');
                                if (res.errors && res.errors.length) console.warn('Частичные ошибки:', res.errors);
                            } else {
                                btn.textContent = 'Ошибка: ' + res.error;
                            }
                            btn.disabled = false;
                        })
                        .catch(() => {
                            btn.textContent = 'Ошибка сети';
                            btn.disabled = false;
                        });
                });
            }

            document.getElementById('payments-list').addEventListener('click', (e) => {
                const deletePayBtn = e.target.closest('.btn-delete-payment');
                if (deletePayBtn) {
                    if (!confirm('Удалить этот платёж?')) return;
                    const paymentId = deletePayBtn.dataset.paymentId;
                    fetch(`/api/students/${studentId}/payment/${paymentId}`, { method: 'DELETE' })
                        .then(r => r.json())
                        .then(() => loadBalanceData(studentId, studentName))
                        .catch(() => alert('Ошибка удаления'));
                }
            });
        }
    }

    if (balanceModalClose) {
        balanceModalClose.addEventListener('click', () => balanceModal.classList.add('hidden'));
    }
    if (balanceModal) {
        balanceModal.addEventListener('click', (e) => {
            if (e.target === balanceModal) balanceModal.classList.add('hidden');
        });
    }

    // ========== Payment Modal Logic ==========

    function openPaymentModal(studentId, lessonPrice) {
        currentBalanceStudentId = studentId;
        currentPaymentStudentLessonPrice = lessonPrice;

        const today = new Date();
        if (formPayDate) formPayDate.value = today.toISOString().split('T')[0];
        if (formPayLessons) formPayLessons.value = '';
        if (formPayAmount) formPayAmount.value = '';
        if (formPayNotes) formPayNotes.value = '';

        if (paymentModal) paymentModal.classList.remove('hidden');
    }

    if (formPayLessons) {
        formPayLessons.addEventListener('input', () => {
            const count = parseInt(formPayLessons.value);
            if (count > 0 && currentPaymentStudentLessonPrice > 0) {
                formPayAmount.value = Math.round(count * currentPaymentStudentLessonPrice);
            }
        });
    }

    function closePaymentModal() {
        if (paymentModal) paymentModal.classList.add('hidden');
        if (paymentForm) paymentForm.reset();
    }

    if (paymentModalClose) paymentModalClose.addEventListener('click', closePaymentModal);
    if (paymentModalCancel) paymentModalCancel.addEventListener('click', closePaymentModal);
    if (paymentModal) {
        paymentModal.addEventListener('click', (e) => {
            if (e.target === paymentModal) closePaymentModal();
        });
    }

    if (paymentForm) paymentForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const lessonsCount = parseInt(formPayLessons.value);
        if (!lessonsCount || lessonsCount <= 0) {
            alert('Укажите количество уроков (больше 0)');
            return;
        }
        const amount = formPayAmount.value;
        const paymentDate = formPayDate.value;
        const notes = formPayNotes.value.trim();

        fetch(`/api/students/${currentBalanceStudentId}/payment`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lessons_count: lessonsCount,
                amount: amount ? parseFloat(amount) : null,
                payment_date: paymentDate || null,
                notes: notes || null
            })
        })
        .then(r => {
            if (r.ok) return r.json();
            return r.json().then(err => { throw new Error(err.error || 'Ошибка'); });
        })
        .then(() => {
            closePaymentModal();
            loadBalanceData(currentBalanceStudentId, currentBalanceStudentName);
        })
        .catch(err => alert(err.message));
    });

    // ========== My Plan Page Logic ==========

    function showMyPlanPage() {
        hideAllPages();
        if (!myPlanPage) return;
        myPlanPage.classList.remove('hidden');
        fetch('/api/my-plan')
            .then(r => r.json())
            .then(data => {
                if (data.error) return;
                document.getElementById('plan-title').textContent = data.template.full_name || data.template.name;
                const p = data.progress;
                const done = Math.min(p.conducted, p.total);
                document.getElementById('plan-progress-label').textContent =
                    `${done} из ${p.total} тем пройдено`;
                document.getElementById('plan-progress-percent').textContent = `${p.percent}%`;
                setTimeout(() => {
                    document.getElementById('plan-progress-fill').style.width = p.percent + '%';
                }, 50);
                const list = document.getElementById('plan-steps-list');
                list.innerHTML = '';
                data.steps.forEach((step, i) => {
                    const isDone = i < p.conducted;
                    const isCurrent = i === p.conducted && p.conducted < p.total;
                    const cls = isDone ? 'done' : isCurrent ? 'current' : 'pending';
                    const icon = isDone ? '✓' : isCurrent ? '→' : String(i + 1);
                    const el = document.createElement('div');
                    el.className = `plan-step plan-step--${cls}`;
                    el.innerHTML = `<span class="plan-step-icon">${icon}</span>
                        <span class="plan-step-title">${step.title}</span>`;
                    list.appendChild(el);
                });
            });
    }

    if (document.getElementById('plan-back-btn')) {
        document.getElementById('plan-back-btn').addEventListener('click', showMainPage);
    }
    if (myPlanBtn) {
        myPlanBtn.addEventListener('click', showMyPlanPage);
    }

    // ========== Plan Templates Page Logic ==========

    const collapsedRootTemplateIds = new Set();
    const collapsedChildTemplateIds = new Set();

    function _makeStepRow(s, i, templateId, stepsContainer) {
        const row = document.createElement('div');
        row.className = 'template-step-row';
        row.draggable = true;
        row.dataset.stepId = s.id;
        row.innerHTML = `
            <span class="drag-handle" title="Перетащить">⠿</span>
            <span class="template-step-num">${i + 1}.</span>
            <span class="template-step-title">${s.title}</span>
            <div class="template-step-actions">
                <button class="btn-edit btn-edit-step" data-id="${s.id}" style="padding:3px 8px;font-size:12px;">✎</button>
                <button class="btn-delete btn-delete-step" data-id="${s.id}" style="padding:3px 8px;font-size:12px;">✕</button>
            </div>`;

        row.addEventListener('dragstart', (e) => {
            row.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', s.id);
        });

        row.addEventListener('dragend', () => {
            row.classList.remove('dragging');
            stepsContainer.querySelectorAll('.template-step-row').forEach(r => r.classList.remove('drag-over'));
            const stepIds = [...stepsContainer.querySelectorAll('.template-step-row')]
                .map(r => parseInt(r.dataset.stepId));
            fetch(`/api/plan-templates/${templateId}/steps/reorder`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ step_ids: stepIds }),
            }).then(() => {
                stepsContainer.querySelectorAll('.template-step-row').forEach((r, idx) => {
                    r.querySelector('.template-step-num').textContent = `${idx + 1}.`;
                });
            });
        });

        row.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            const dragging = stepsContainer.querySelector('.dragging');
            if (!dragging || dragging === row) return;
            const rect = row.getBoundingClientRect();
            if (e.clientY < rect.top + rect.height / 2) {
                stepsContainer.insertBefore(dragging, row);
            } else {
                stepsContainer.insertBefore(dragging, row.nextSibling);
            }
        });

        row.addEventListener('drop', (e) => { e.preventDefault(); });

        return row;
    }

    function _setAccordionState(btn, body, collapsed) {
        if (!btn || !body) return;
        btn.classList.toggle('collapsed', collapsed);
        btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        if (collapsed) {
            body.classList.add('is-collapsed');
            body.style.maxHeight = '0px';
        } else {
            body.classList.remove('is-collapsed');
            body.style.maxHeight = `${body.scrollHeight}px`;
            setTimeout(() => {
                if (!btn.classList.contains('collapsed')) {
                    body.style.maxHeight = 'none';
                }
            }, 240);
        }
    }

    function _toggleAccordion(btn) {
        const body = document.getElementById(btn.dataset.targetId);
        if (!body) return;
        const templateId = parseInt(btn.dataset.templateId);
        const level = btn.dataset.level;
        const isCollapsed = btn.classList.contains('collapsed');
        if (isCollapsed) {
            if (level === 'root') collapsedRootTemplateIds.delete(templateId);
            if (level === 'child') collapsedChildTemplateIds.delete(templateId);
            _setAccordionState(btn, body, false);
            return;
        }
        if (body.style.maxHeight === 'none' || !body.style.maxHeight) {
            body.style.maxHeight = `${body.scrollHeight}px`;
        }
        requestAnimationFrame(() => {
            _setAccordionState(btn, body, true);
        });
        if (level === 'root') collapsedRootTemplateIds.add(templateId);
        if (level === 'child') collapsedChildTemplateIds.add(templateId);
    }

    function _flattenSecondLevelTemplates(roots) {
        const result = [];
        roots.forEach(root => {
            (root.children || []).forEach(child => {
                result.push({
                    ...child,
                    root_id: root.id,
                    root_name: root.name,
                    full_name: `${root.name} / ${child.name}`,
                });
            });
        });
        return result;
    }

    function renderTemplates(roots) {
        const container = document.getElementById('templates-list');
        container.innerHTML = '';
        if (!roots.length) {
            container.innerHTML = '<p style="color:var(--color-text-muted);font-size:14px;">Нет корневых планов</p>';
            return;
        }

        roots.forEach(root => {
            const rootCard = document.createElement('div');
            rootCard.className = 'plan-card';
            const rootBodyId = `plan-root-body-${root.id}`;
            rootCard.innerHTML = `
                <div class="plan-card-header">
                    <div class="plan-header-main">
                        <button class="plan-collapse-toggle" data-level="root" data-template-id="${root.id}" data-target-id="${rootBodyId}" aria-expanded="true" title="Свернуть/развернуть"></button>
                        <h3>${root.name}</h3>
                    </div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;">
                        <button class="btn-edit btn-rename-template" data-id="${root.id}" data-name="${root.name}">Переименовать</button>
                        <button class="btn-delete btn-delete-template" data-id="${root.id}">Удалить</button>
                    </div>
                </div>
                <div class="plan-accordion-body" id="${rootBodyId}">
                    <div class="template-add-step" style="margin-bottom:10px;">
                        <input type="text" class="new-child-input" placeholder="Новый план 2-го уровня..." data-root-id="${root.id}">
                        <button class="btn-primary btn-add-child" data-root-id="${root.id}" style="padding:8px 14px;font-size:13px;">+ Добавить уровень</button>
                    </div>
                    <div class="template-children"></div>
                </div>
            `;

            const childrenContainer = rootCard.querySelector('.template-children');
            const children = root.children || [];
            if (!children.length) {
                const empty = document.createElement('p');
                empty.style.cssText = 'color:var(--color-text-muted);font-size:14px;';
                empty.textContent = 'Нет планов 2-го уровня';
                childrenContainer.appendChild(empty);
            } else {
                children.forEach(child => {
                    const childCard = document.createElement('div');
                    childCard.className = 'plan-card';
                    childCard.style.marginTop = '10px';
                    const childBodyId = `plan-child-body-${child.id}`;
                    childCard.innerHTML = `
                        <div class="plan-card-header">
                            <div class="plan-header-main">
                                <button class="plan-collapse-toggle" data-level="child" data-template-id="${child.id}" data-target-id="${childBodyId}" aria-expanded="true" title="Свернуть/развернуть"></button>
                                <h3 style="font-size:16px;margin:0;">${child.name}</h3>
                            </div>
                            <div style="display:flex;gap:8px;flex-wrap:wrap;">
                                <button class="btn-secondary btn-copy-template" data-id="${child.id}" data-name="${child.name}" data-root-id="${root.id}">Копировать</button>
                                <button class="btn-edit btn-rename-template" data-id="${child.id}" data-name="${child.name}">Переименовать</button>
                                <button class="btn-delete btn-delete-template" data-id="${child.id}">Удалить</button>
                            </div>
                        </div>
                        <div class="plan-accordion-body" id="${childBodyId}">
                            <div class="template-steps"></div>
                            <div class="template-add-step">
                                <input type="text" class="new-step-input" placeholder="Новый шаг плана..." data-template-id="${child.id}">
                                <button class="btn-primary btn-add-step" data-template-id="${child.id}" style="padding:8px 14px;font-size:13px;">+ Добавить шаг</button>
                            </div>
                        </div>
                    `;
                    const stepsContainer = childCard.querySelector('.template-steps');
                    (child.steps || []).forEach((s, i) => stepsContainer.appendChild(_makeStepRow(s, i, child.id, stepsContainer)));
                    childrenContainer.appendChild(childCard);
                });
            }

            container.appendChild(rootCard);
        });
        container.querySelectorAll('.plan-collapse-toggle[data-level="root"]').forEach(btn => {
            const body = document.getElementById(btn.dataset.targetId);
            const isCollapsed = collapsedRootTemplateIds.has(parseInt(btn.dataset.templateId));
            _setAccordionState(btn, body, isCollapsed);
        });
        container.querySelectorAll('.plan-collapse-toggle[data-level="child"]').forEach(btn => {
            const body = document.getElementById(btn.dataset.targetId);
            const isCollapsed = collapsedChildTemplateIds.has(parseInt(btn.dataset.templateId));
            _setAccordionState(btn, body, isCollapsed);
        });
    }

    function renderStudentAssignments(students, templates) {
        const container = document.getElementById('student-plan-assignments');
        if (!students.length) {
            container.innerHTML = '<p style="color:var(--color-text-muted);font-size:14px;">Нет учеников</p>';
            return;
        }
        const tmplOptions = ['<option value="">— без плана —</option>',
            ...templates.map(t => `<option value="${t.id}">${t.full_name || t.name}</option>`)
        ].join('');
        container.innerHTML = students.map(s => `
            <div class="student-assign-row">
                <span>${s.display_name}</span>
                <select class="student-plan-select" data-student-id="${s.id}">
                    ${tmplOptions}
                </select>
            </div>`).join('');
        // Set current values
        students.forEach(s => {
            const sel = container.querySelector(`.student-plan-select[data-student-id="${s.id}"]`);
            if (sel && s.template_id) sel.value = s.template_id;
        });
        // Save on change
        container.querySelectorAll('.student-plan-select').forEach(sel => {
            sel.addEventListener('change', () => {
                const studentId = sel.dataset.studentId;
                const templateId = sel.value ? parseInt(sel.value) : null;
                fetch(`/api/students/${studentId}/plan`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ template_id: templateId }),
                });
            });
        });
    }

    function loadPlanTemplatesPage() {
        Promise.all([
            fetch('/api/plan-templates').then(r => r.json()),
            fetch('/api/students-with-plans').then(r => r.json()),
        ]).then(([tData, sData]) => {
            const roots = tData.templates || [];
            planRootTemplatesCache = roots.map(r => ({ id: r.id, name: r.name }));
            const secondLevel = _flattenSecondLevelTemplates(roots);
            renderTemplates(roots);
            renderStudentAssignments(sData.students || [], secondLevel);
        });
    }

    function showPlanTemplatesPage() {
        hideAllPages();
        if (!planTemplatesPage) return;
        planTemplatesPage.classList.remove('hidden');
        loadPlanTemplatesPage();
    }

    if (document.getElementById('plan-templates-back-btn')) {
        document.getElementById('plan-templates-back-btn').addEventListener('click', showMainPage);
    }

    if (document.getElementById('add-template-btn')) {
        document.getElementById('add-template-btn').addEventListener('click', () => {
            const name = prompt('Название корневого плана (1-й уровень):');
            if (!name || !name.trim()) return;
            fetch('/api/plan-templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name.trim() }),
            }).then(r => r.json()).then(() => loadPlanTemplatesPage());
        });
    }

    // Event delegation for templates list
    document.addEventListener('click', e => {
        // Copy second-level template with steps
        if (e.target.closest('.btn-copy-template')) {
            const btn = e.target.closest('.btn-copy-template');
            const sourceTemplateId = parseInt(btn.dataset.id);
            const sourceName = btn.dataset.name || '';
            const defaultRootId = parseInt(btn.dataset.rootId);
            const roots = planRootTemplatesCache || [];
            if (!roots.length) {
                alert('Нет доступных планов 1-го уровня');
                return;
            }
            const rootsText = roots.map(r => `${r.id}: ${r.name}`).join('\n');
            const rootInput = prompt(
                `Выберите ID плана 1-го уровня, куда создать копию:\n${rootsText}`,
                String(defaultRootId || roots[0].id)
            );
            if (!rootInput) return;
            const targetRootId = parseInt(rootInput.trim());
            if (!roots.some(r => r.id === targetRootId)) {
                alert('Неверный ID плана 1-го уровня');
                return;
            }

            const copyNameDefault = `Копия ${sourceName}`;
            const copyNameInput = prompt('Название копии:', copyNameDefault);
            if (!copyNameInput || !copyNameInput.trim()) return;

            fetch(`/api/plan-templates/${sourceTemplateId}/copy`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    parent_id: targetRootId,
                    name: copyNameInput.trim(),
                }),
            })
                .then(r => r.json().then(data => ({ ok: r.ok, data })))
                .then(({ ok, data }) => {
                    if (!ok) {
                        alert(data.error || 'Не удалось создать копию');
                        return;
                    }
                    loadPlanTemplatesPage();
                })
                .catch(() => alert('Ошибка при создании копии'));
        }
        // Delete step
        if (e.target.closest('.btn-delete-step')) {
            const btn = e.target.closest('.btn-delete-step');
            if (!confirm('Удалить шаг?')) return;
            fetch(`/api/plan-steps/${btn.dataset.id}`, { method: 'DELETE' })
                .then(() => loadPlanTemplatesPage());
        }
        // Edit step
        if (e.target.closest('.btn-edit-step')) {
            const btn = e.target.closest('.btn-edit-step');
            const currentTitle = btn.closest('.template-step-row')?.querySelector('.template-step-title')?.textContent || '';
            const newTitle = prompt('Новое название шага:', currentTitle);
            if (!newTitle || !newTitle.trim()) return;
            fetch(`/api/plan-steps/${btn.dataset.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle.trim() }),
            }).then(() => loadPlanTemplatesPage());
        }
        // Delete template
        if (e.target.closest('.btn-delete-template')) {
            const btn = e.target.closest('.btn-delete-template');
            if (!confirm('Удалить шаблон и все его шаги?')) return;
            fetch(`/api/plan-templates/${btn.dataset.id}`, { method: 'DELETE' })
                .then(() => loadPlanTemplatesPage());
        }
        // Rename template
        if (e.target.closest('.btn-rename-template')) {
            const btn = e.target.closest('.btn-rename-template');
            const newName = prompt('Новое название:', btn.dataset.name);
            if (!newName || !newName.trim()) return;
            fetch(`/api/plan-templates/${btn.dataset.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: newName.trim() }),
            }).then(() => loadPlanTemplatesPage());
        }
        // Add step button
        if (e.target.closest('.btn-add-step')) {
            const btn = e.target.closest('.btn-add-step');
            const tid = btn.dataset.templateId;
            const input = document.querySelector(`.new-step-input[data-template-id="${tid}"]`);
            const title = (input?.value || '').trim();
            if (!title) return;
            fetch(`/api/plan-templates/${tid}/steps`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title }),
            }).then(() => loadPlanTemplatesPage());
        }
        // Add second-level plan
        if (e.target.closest('.btn-add-child')) {
            const btn = e.target.closest('.btn-add-child');
            const rootId = btn.dataset.rootId;
            const input = document.querySelector(`.new-child-input[data-root-id="${rootId}"]`);
            const name = (input?.value || '').trim();
            if (!name) return;
            fetch('/api/plan-templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, parent_id: parseInt(rootId) }),
            }).then(() => loadPlanTemplatesPage());
        }
        // Accordion toggle
        if (e.target.closest('.plan-collapse-toggle')) {
            const btn = e.target.closest('.plan-collapse-toggle');
            _toggleAccordion(btn);
        }
    });

    // Add step on Enter key in step input
    document.addEventListener('keydown', e => {
        if (e.key === 'Enter' && e.target.classList.contains('new-step-input')) {
            const tid = e.target.dataset.templateId;
            const title = e.target.value.trim();
            if (!title) return;
            fetch(`/api/plan-templates/${tid}/steps`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title }),
            }).then(() => loadPlanTemplatesPage());
        }
        if (e.key === 'Enter' && e.target.classList.contains('new-child-input')) {
            const rootId = e.target.dataset.rootId;
            const name = e.target.value.trim();
            if (!name) return;
            fetch('/api/plan-templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, parent_id: parseInt(rootId) }),
            }).then(() => loadPlanTemplatesPage());
        }
    });

    // ========== Homework Review Page ==========
    function reviewStatusBadge(name, group) {
        const g = (group || '').toLowerCase();
        if (g === 'in_review') return `<span style="color:#2563eb;font-weight:700;">${escapeHtml(name || 'На проверке')}</span>`;
        if (g === 'done') return `<span style="color:#15803d;font-weight:700;">${escapeHtml(name || 'Выполнено')}</span>`;
        return `<span>${escapeHtml(name || '—')}</span>`;
    }

    function showHomeworkReviewPage() {
        hideAllPages();
        if (!homeworkReviewPage) return;
        homeworkReviewPage.classList.remove('hidden');
        loadHomeworkReviewFilters();
        loadHomeworkReviewPage();
    }

    function loadHomeworkReviewPage() {
        if (!homeworkReviewTbody) return;
        const withFiles = homeworkReviewWithFilesOnly && homeworkReviewWithFilesOnly.checked ? '1' : '0';
        const studentId = homeworkReviewStudentFilter && homeworkReviewStudentFilter.value ? `&student_id=${encodeURIComponent(homeworkReviewStudentFilter.value)}` : '';
        const statusId = homeworkReviewStatusFilter && homeworkReviewStatusFilter.value ? `&status_id=${encodeURIComponent(homeworkReviewStatusFilter.value)}` : '';
        homeworkReviewTbody.innerHTML = '<tr><td colspan="9">Загрузка...</td></tr>';
        fetch(`/api/homework-review?with_files=${withFiles}${studentId}${statusId}`)
            .then(r => r.json())
            .then(data => {
                const items = data.items || [];
                // #region agent log
                fetch('http://127.0.0.1:7831/ingest/28f26b46-aadf-4ddb-9fc0-0d229b16104f', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'e062f9' }, body: JSON.stringify({ sessionId: 'e062f9', hypothesisId: 'H2', location: 'script.js:loadHomeworkReviewPage', message: 'list_loaded', data: { n: items.length, statusFilter: homeworkReviewStatusFilter && homeworkReviewStatusFilter.value, sample: items.slice(0, 8).map(i => ({ task_id: i.task_id, status_id: i.status_id, status_name: i.status_name, status_group: i.status_group, has_remarks: !!(i.homework_teacher_remarks && String(i.homework_teacher_remarks).trim()) })) }, timestamp: Date.now() }) }).catch(() => {});
                // #endregion
                if (!items.length) {
                    homeworkReviewTbody.innerHTML = '<tr><td colspan="9">Нет заданий для проверки</td></tr>';
                    return;
                }
                homeworkReviewTbody.innerHTML = items.map(item => {
                    const studentFiles = item.student_files || item.files || [];
                    const teacherFiles = item.teacher_files || [];
                    const studentFilesHtml = studentFiles.length
                        ? studentFiles.map(f => `<a href="${escapeAttr(f.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(f.name)}</a>`).join('<br>')
                        : '<span style="color:var(--color-text-secondary);">Нет файлов</span>';
                    const teacherFilesHtml = teacherFiles.length
                        ? teacherFiles.map(f => `<a href="${escapeAttr(f.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(f.name)}</a>`).join('<br>')
                        : '<span style="color:var(--color-text-secondary);">Нет файлов</span>';
                    const remarksVal = escapeHtml(item.homework_teacher_remarks || '');
                    return `
                        <tr>
                            <td>${escapeHtml(item.student_name || '—')}</td>
                            <td>${escapeHtml(item.homework_name || '—')}</td>
                            <td>${escapeHtml(item.homework_topic || '—')}</td>
                            <td>${escapeHtml(item.lesson_date || '—')}</td>
                            <td>${reviewStatusBadge(item.status_name, item.status_group)}</td>
                            <td>
                                <div class="homework-review-files-block">
                                    <div class="homework-review-files-title">Файлы ученика</div>
                                    <div>${studentFilesHtml}</div>
                                </div>
                                <div class="homework-review-files-block">
                                    <div class="homework-review-files-title">Файлы учителя</div>
                                    <div>${teacherFilesHtml}</div>
                                    <input type="file" class="homework-review-teacher-files-input" data-task-id="${item.task_id}" multiple>
                                    <div class="homework-review-files-hint">Можно выбрать несколько файлов (до 5 МБ суммарно)</div>
                                </div>
                            </td>
                            <td>${escapeHtml(item.submitted_at || '—')}</td>
                            <td>
                                <textarea class="homework-review-remarks filter-control" rows="3" placeholder="Замечания учителя…" data-task-id="${item.task_id}">${remarksVal}</textarea>
                            </td>
                            <td>
                                <div style="display:flex;gap:8px;flex-wrap:wrap;">
                                    <button type="button" class="btn-secondary btn-hw-review-action" data-task-id="${item.task_id}" data-action="rework">На доработку</button>
                                    <button type="button" class="btn-primary btn-hw-review-action" data-task-id="${item.task_id}" data-action="approve">Подтвердить</button>
                                </div>
                            </td>
                        </tr>
                    `;
                }).join('');
            })
            .catch(() => {
                homeworkReviewTbody.innerHTML = '<tr><td colspan="9">Ошибка загрузки</td></tr>';
            });
    }

    function loadHomeworkReviewFilters() {
        Promise.all([
            fetch('/api/students/all').then(r => r.json()),
            fetch('/api/task-statuses/all').then(r => r.json()),
        ]).then(([studentsData, statusesData]) => {
            if (homeworkReviewStudentFilter) {
                const students = studentsData.students || [];
                const prev = homeworkReviewStudentFilter.value;
                homeworkReviewStudentFilter.innerHTML = '<option value="">Все ученики</option>'
                    + students.map(s => `<option value="${s.id}">${escapeHtml(s.display_name)}</option>`).join('');
                if (prev) homeworkReviewStudentFilter.value = prev;
            }
            if (homeworkReviewStatusFilter) {
                const statuses = statusesData.statuses || [];
                const prev = homeworkReviewStatusFilter.value;
                homeworkReviewStatusFilter.innerHTML = '<option value="">Все статусы</option>'
                    + statuses.map(s => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join('');
                if (prev) homeworkReviewStatusFilter.value = prev;
            }
        }).catch(() => {});
    }

    if (backToMainFromHomeworkReviewBtn) backToMainFromHomeworkReviewBtn.addEventListener('click', showMainPage);
    if (homeworkReviewRefreshBtn) homeworkReviewRefreshBtn.addEventListener('click', loadHomeworkReviewPage);
    if (homeworkReviewWithFilesOnly) homeworkReviewWithFilesOnly.addEventListener('change', loadHomeworkReviewPage);
    if (homeworkReviewStudentFilter) homeworkReviewStudentFilter.addEventListener('change', loadHomeworkReviewPage);
    if (homeworkReviewStatusFilter) homeworkReviewStatusFilter.addEventListener('change', loadHomeworkReviewPage);
    if (homeworkReviewTbody) {
        homeworkReviewTbody.addEventListener('change', (e) => {
            const input = e.target.closest('.homework-review-teacher-files-input');
            if (!input) return;
            const taskId = input.dataset.taskId;
            const files = input.files ? Array.from(input.files) : [];
            input.value = '';
            if (!taskId || !files.length) return;
            const formData = new FormData();
            files.forEach(file => formData.append('files', file));
            fetch(`/api/tasks/${taskId}/evidence`, {
                method: 'POST',
                body: formData,
            })
                .then(r => r.json().then(data => ({ ok: r.ok, data })))
                .then(({ ok, data }) => {
                    if (!ok) {
                        showAppToast(data.error || 'Не удалось загрузить файлы', true);
                        return;
                    }
                    showAppToast(files.length === 1 ? 'Файл учителя загружен' : 'Файлы учителя загружены');
                    loadHomeworkReviewPage();
                })
                .catch(() => showAppToast('Ошибка загрузки файлов', true));
        });
        homeworkReviewTbody.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn-hw-review-action');
            if (!btn) return;
            const taskId = btn.dataset.taskId;
            const action = btn.dataset.action;
            const row = btn.closest('tr');
            const ta = row && row.querySelector('.homework-review-remarks');
            const remarks = (ta && ta.value) ? ta.value.trim() : '';
            if (action === 'rework' && !remarks) {
                showAppToast('Укажите замечания при возврате на доработку', true);
                return;
            }
            fetch(`/api/tasks/${taskId}/homework-review`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action, remarks }),
            })
                .then(r => r.json().then(data => ({ ok: r.ok, data })))
                .then(({ ok, data }) => {
                    if (!ok) {
                        showAppToast(data.error || 'Не удалось обновить статус', true);
                        return;
                    }
                    // #region agent log
                    fetch('http://127.0.0.1:7831/ingest/28f26b46-aadf-4ddb-9fc0-0d229b16104f', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'e062f9' }, body: JSON.stringify({ sessionId: 'e062f9', hypothesisId: 'H3', location: 'script.js:homework-review-action', message: 'review_ok', data: { taskId, action, response_status_id: data.status_id, remarks_len: (data.homework_teacher_remarks && String(data.homework_teacher_remarks).length) || 0 }, timestamp: Date.now() }) }).catch(() => {});
                    // #endregion
                    showAppToast(action === 'approve' ? 'Задание отмечено как выполненное' : 'Задание отправлено на доработку');
                    loadHomeworkReviewPage();
                })
                .catch(() => showAppToast('Ошибка обновления статуса', true));
        });
    }

    // ========== Reports Page Logic ==========

    function showReportsPage() {
        hideAllPages();
        reportsPage.classList.remove('hidden');

        const currentYear = new Date().getFullYear();
        reportYearSelect.innerHTML = '';
        for (let y = currentYear; y >= currentYear - 3; y--) {
            const opt = document.createElement('option');
            opt.value = y;
            opt.textContent = y;
            reportYearSelect.appendChild(opt);
        }

        loadEarningsReport(currentYear);
    }

    if (backToMainFromReportsBtn) backToMainFromReportsBtn.addEventListener('click', showMainPage);

    if (reportLoadBtn) reportLoadBtn.addEventListener('click', () => {
        const year = parseInt(reportYearSelect.value);
        if (year) loadEarningsReport(year);
    });

    function loadEarningsReport(year) {
        reportContent.innerHTML = '<p class="loading">Загрузка...</p>';
        fetch(`/api/reports/earnings?year=${year}`)
            .then(r => r.json())
            .then(data => renderEarningsReport(data))
            .catch(() => { reportContent.innerHTML = '<p>Ошибка загрузки</p>'; });
    }

    function renderEarningsReport(data) {
        if (!data.months || data.months.length === 0) {
            reportContent.innerHTML = '<p class="empty-msg">Данных за этот год нет</p>';
            return;
        }

        const totalAmount = data.months.reduce((s, m) => s + m.total_amount, 0);
        const totalLessons = data.months.reduce((s, m) => s + m.total_lessons, 0);

        let html = `
            <div class="report-summary">
                Итого за ${data.year}: <strong>${totalLessons} уроков</strong>, <strong>${totalAmount.toFixed(0)} ₽</strong>
            </div>
            <div class="report-months">
        `;

        data.months.forEach(month => {
            html += `
            <div class="report-month">
                <div class="report-month-header">
                    <span class="report-month-name">${month.month_name}</span>
                    <span class="report-month-stats">${month.total_lessons} уроков &mdash; ${month.total_amount.toFixed(0)} ₽</span>
                </div>
                <table class="data-table report-table">
                    <thead>
                        <tr>
                            <th>Дата</th>
                            <th>Ученик</th>
                            <th>Уроков</th>
                            <th>Сумма</th>
                            <th>Заметка</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            month.payments.forEach(p => {
                html += `
                        <tr>
                            <td>${p.payment_date || '—'}</td>
                            <td>${escapeHtml(p.student_name || '—')}</td>
                            <td>${p.lessons_count}</td>
                            <td>${p.amount != null ? p.amount.toFixed(0) + ' ₽' : '—'}</td>
                            <td>${escapeHtml(p.notes || '—')}</td>
                        </tr>
                `;
            });
            html += `
                    </tbody>
                </table>
            </div>
            `;
        });

        html += '</div>';
        reportContent.innerHTML = html;
    }
});
