document.addEventListener('DOMContentLoaded', () => {

    // ===== State =====
    let currentUser = null;
    let timerInterval = null;
    let homeworkData = [];
    let nextLessonStartAt = null;
    let meetingLinkUrl = '';
    let monthLessons = [];
    let lessonMapByDate = {};
    let selectedHomeworkTaskId = null;

    // ===== Element refs =====
    const sdUsername = document.getElementById('sd-username');
    const sdTimerBlock = document.getElementById('sd-timer-block');
    const sdTimerDays = document.getElementById('sd-timer-days');
    const sdTimerHours = document.getElementById('sd-timer-hours');
    const sdTimerMinutes = document.getElementById('sd-timer-minutes');
    const sdNextTopicValue = document.getElementById('sd-next-topic-value');
    const sdNextTopic = document.getElementById('sd-next-topic');
    const sdJoinLessonBtn = document.getElementById('sd-join-lesson-btn');
    const sdJoinConfirmModal = document.getElementById('sd-join-confirm-modal');
    const sdJoinConfirmYes = document.getElementById('sd-join-confirm-yes');
    const sdJoinConfirmNo = document.getElementById('sd-join-confirm-no');

    const myTeacherCard = document.getElementById('my-teacher-card');
    const myTeacherPhoto = document.getElementById('my-teacher-photo');
    const myTeacherNoPhoto = document.getElementById('my-teacher-no-photo');
    const myTeacherName = document.getElementById('my-teacher-name');

    const sdProfileBtn = document.getElementById('sd-profile-btn');
    const sdProfileModal = document.getElementById('sd-profile-modal');
    const sdProfileModalClose = document.getElementById('sd-profile-modal-close');
    const sdLogoutBtn = document.getElementById('sd-logout-btn');
    const sdTelegramBtn = document.getElementById('sd-telegram-btn');
    const sdChangePasswordBtn = document.getElementById('sd-change-password-btn');

    const sdCpModal = document.getElementById('sd-change-password-modal');
    const sdCpModalClose = document.getElementById('sd-cp-modal-close');
    const sdCpCancel = document.getElementById('sd-cp-cancel');
    const sdCpForm = document.getElementById('sd-change-password-form');
    const sdOldPassword = document.getElementById('sd-old-password');
    const sdNewPassword = document.getElementById('sd-new-password');
    const sdConfirmPassword = document.getElementById('sd-confirm-password');
    const sdCpError = document.getElementById('sd-cp-error');
    const sdCpSuccess = document.getElementById('sd-cp-success');

    const sdShowDoneCb = document.getElementById('sd-show-done-cb');
    const sdHomeworkList = document.getElementById('sd-homework-list');

    const sdPlanContent = document.getElementById('sd-plan-content');
    const sdMiniCalendar = document.getElementById('sd-mini-calendar');
    const sdCenterContent = document.getElementById('sd-center-content');
    const sdCenterTitle = document.getElementById('sd-center-title');

    const CENTER_TITLE_LESSON = 'Информация по уроку';
    const CENTER_TITLE_HOMEWORK = 'Информация по домашнему заданию';

    function setCenterTitleLesson() {
        if (sdCenterTitle) sdCenterTitle.textContent = CENTER_TITLE_LESSON;
    }

    function setCenterTitleHomework() {
        if (sdCenterTitle) sdCenterTitle.textContent = CENTER_TITLE_HOMEWORK;
    }

    // ===== Helpers =====

    function openModal(el) { el.classList.remove('hidden'); }
    function closeModal(el) { el.classList.add('hidden'); }

    function showMsg(el, msg, isError) {
        el.textContent = msg;
        el.classList.remove('hidden');
        setTimeout(() => el.classList.add('hidden'), 4000);
    }

    function showToast(message, isError = false) {
        if (!sdCenterContent) return;
        const toast = document.createElement('div');
        toast.className = `sd-toast ${isError ? 'sd-toast-error' : 'sd-toast-success'}`;
        toast.textContent = message;
        sdCenterContent.prepend(toast);
        setTimeout(() => toast.remove(), 2600);
    }

    function escapeHtml(value) {
        const div = document.createElement('div');
        div.textContent = String(value ?? '');
        return div.innerHTML;
    }

    function formatBytes(bytes) {
        const b = Number(bytes || 0);
        if (b < 1024) return `${b} Б`;
        if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} КБ`;
        return `${(b / (1024 * 1024)).toFixed(2)} МБ`;
    }

    function updateJoinLessonButtonVisibility() {
        if (!sdJoinLessonBtn) return;
        if (meetingLinkUrl && nextLessonStartAt) {
            sdJoinLessonBtn.classList.remove('sd-hidden');
        } else {
            sdJoinLessonBtn.classList.add('sd-hidden');
        }
    }

    function openLessonLink() {
        if (!meetingLinkUrl) {
            alert('Ссылка на урок не настроена');
            return;
        }
        window.open(meetingLinkUrl, '_blank', 'noopener,noreferrer');
    }

    function loadMeetingLink() {
        return fetch('/api/settings/meeting_link')
            .then(r => r.json())
            .then(data => {
                meetingLinkUrl = (data.value || '').trim();
                updateJoinLessonButtonVisibility();
            })
            .catch(() => {
                meetingLinkUrl = '';
                updateJoinLessonButtonVisibility();
            });
    }

    function normalizeDateKey(d) {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
    }

    function buildLessonMap(lessons) {
        const map = {};
        lessons.forEach(lesson => {
            const key = lesson.date_iso;
            if (!key) return;
            if (!map[key]) map[key] = [];
            map[key].push(lesson);
        });
        return map;
    }

    // ===== Countdown Timer =====

    function startCountdown(isoDate) {
        const target = new Date(isoDate);
        if (timerInterval) clearInterval(timerInterval);

        function tick() {
            const diff = Math.max(0, target - Date.now());
            if (diff === 0) {
                clearInterval(timerInterval);
                sdTimerBlock.classList.add('sd-hidden');
                return;
            }
            const totalSec = Math.floor(diff / 1000);
            sdTimerDays.textContent = String(Math.floor(totalSec / 86400)).padStart(2, '0');
            sdTimerHours.textContent = String(Math.floor((totalSec % 86400) / 3600)).padStart(2, '0');
            sdTimerMinutes.textContent = String(Math.floor((totalSec % 3600) / 60)).padStart(2, '0');
        }
        tick();
        timerInterval = setInterval(tick, 1000);
        sdTimerBlock.classList.remove('sd-hidden');
    }

    // ===== Mini Calendar =====

    function renderLessonInfoForDate(dateKey) {
        if (!sdCenterContent) return;
        setCenterTitleLesson();
        const lessons = lessonMapByDate[dateKey] || [];
        if (!lessons.length) {
            sdCenterContent.innerHTML = `
                <div class="sd-center-empty">
                    В этот день у вас нет уроков.
                </div>
            `;
            return;
        }

        const cardsHtml = lessons.map(lesson => {
            const durationText = lesson.duration ? `${lesson.duration} мин` : '—';
            const paidClass = lesson.is_paid ? 'sd-paid-badge paid' : 'sd-paid-badge unpaid';
            const paidText = lesson.is_paid ? 'Оплачено' : 'Не оплачено';
            return `
                <div class="sd-lesson-card">
                    <div class="sd-lesson-row"><span>Дата</span><b>${lesson.date || '—'}</b></div>
                    <div class="sd-lesson-row"><span>Время</span><b>${lesson.time || '—'}</b></div>
                    <div class="sd-lesson-row"><span>Продолжительность</span><b>${durationText}</b></div>
                    <div class="sd-lesson-row"><span>Тема</span><b>${lesson.topic || '—'}</b></div>
                    <div class="sd-lesson-row"><span>Статус оплаты</span><span class="${paidClass}">${paidText}</span></div>
                </div>
            `;
        }).join('');

        sdCenterContent.innerHTML = cardsHtml;
    }

    function loadHomeworkEvidence(taskId) {
        return fetch(`/api/tasks/${taskId}/evidence`)
            .then(r => r.json())
            .then(data => ({
                files: data.files || [],
                totalSize: data.total_size_bytes || 0,
                limit: data.limit_bytes || (5 * 1024 * 1024),
            }))
            .catch(() => ({ files: [], totalSize: 0, limit: 5 * 1024 * 1024 }));
    }

    function uploadEvidenceFiles(taskId, files) {
        if (!files.length) return;
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));
        fetch(`/api/tasks/${taskId}/evidence`, {
            method: 'POST',
            body: formData,
        })
            .then(r => r.json().then(data => ({ ok: r.ok, data })))
            .then(({ ok, data }) => {
                if (!ok) {
                    showToast(data.error || 'Ошибка загрузки', true);
                    return;
                }
                showToast(files.length === 1 ? 'Файл загружен' : 'Файлы загружены');
                renderHomeworkCenter(taskId);
            })
            .catch(() => showToast('Ошибка загрузки файлов', true));
    }

    function renderHomeworkCenter(taskId) {
        const hw = homeworkData.find(x => x.task_id === taskId);
        if (!hw || !sdCenterContent) return;
        selectedHomeworkTaskId = taskId;
        setCenterTitleHomework();

        loadHomeworkEvidence(taskId).then(({ files, totalSize, limit }) => {
            const filesHtml = files.length
                ? files.map(f => `
                    <div class="sd-evidence-item">
                        <a href="${escapeHtml(f.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(f.original_name || 'Файл')}</a>
                        <span>${formatBytes(f.size_bytes)}</span>
                        <button class="sd-btn-link sd-delete-evidence-btn" data-evidence-id="${f.id}">Удалить</button>
                    </div>
                `).join('')
                : '<p class="sd-empty">Файлы пока не загружены</p>';

            const status = escapeHtml(hw.status_name || (hw.is_overdue ? 'Просрочено' : 'В очереди'));
            const submitDisabled = hw.status_group === 'done' || hw.status_group === 'in_review';
            const submitLabel = submitDisabled ? 'Уже отправлено' : 'Отправить учителю';
            const remarksRaw = (hw.homework_teacher_remarks || '').trim();
            const teacherRemarksBlock = remarksRaw
                ? `<div class="sd-homework-teacher-remarks">
                        <div class="sd-homework-teacher-remarks-label">Замечания учителя</div>
                        <div class="sd-homework-teacher-remarks-text">${escapeHtml(remarksRaw)}</div>
                   </div>`
                : '';

            sdCenterContent.innerHTML = `
                <div class="sd-homework-center-card">
                    <h3>${escapeHtml(hw.homework_name || 'Домашнее задание')}</h3>
                    <div class="sd-homework-center-row"><span>Статус</span><b>${status}</b></div>
                    <div class="sd-homework-center-row"><span>Дата урока</span><b>${escapeHtml(hw.lesson_date || '—')}</b></div>
                    <div class="sd-homework-center-row"><span>Тема</span><b>${escapeHtml(hw.topic_title || '—')}</b></div>
                    <div class="sd-homework-center-comment">${hw.homework_comment || '<span class="sd-empty">Комментарий не указан</span>'}</div>
                    ${teacherRemarksBlock}
                    <div class="sd-homework-center-files">
                        <div class="sd-homework-center-files-head">
                            <b>Файлы выполнения</b>
                            <span>${formatBytes(totalSize)} / ${formatBytes(limit)}</span>
                        </div>
                        <input type="file" id="sd-evidence-input" multiple>
                        <p class="sd-evidence-hint">Файлы загружаются сразу после выбора. Можно выбрать несколько за раз.</p>
                        <div class="sd-evidence-list">${filesHtml}</div>
                    </div>
                    <button class="sd-btn-join" id="sd-submit-homework-btn" ${submitDisabled ? 'disabled' : ''}>${submitLabel}</button>
                </div>
            `;
            renderHomework();
        });
    }

    function renderMiniCalendar() {
        const now = new Date();
        const year = now.getFullYear();
        const month = now.getMonth();
        const today = now.getDate();

        const monthNames = ['Январь','Февраль','Март','Апрель','Май','Июнь',
                            'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
        const dayNames = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];

        // days with lessons in current month
        const lessonDays = new Set();
        monthLessons.forEach(lesson => {
            if (lesson.start_date_iso) {
                const d = new Date(lesson.start_date_iso);
                if (d.getFullYear() === year && d.getMonth() === month) {
                    lessonDays.add(d.getDate());
                }
            }
        });

        const firstDay = new Date(year, month, 1).getDay(); // 0=Sun
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        // Convert Sunday-first to Monday-first
        const startOffset = (firstDay + 6) % 7;

        let html = `<div class="sd-cal-header">${monthNames[month]} ${year}</div>`;
        html += '<div class="sd-cal-grid">';

        // Day names header
        dayNames.forEach(d => { html += `<div class="sd-cal-cell sd-cal-dayname">${d}</div>`; });

        // Empty cells before first day
        for (let i = 0; i < startOffset; i++) {
            html += '<div class="sd-cal-cell"></div>';
        }

        // Day cells
        for (let day = 1; day <= daysInMonth; day++) {
            let cls = 'sd-cal-cell sd-cal-day';
            if (day === today) cls += ' sd-cal-today';
            if (day === today) cls += ' sd-cal-selected';
            if (lessonDays.has(day)) cls += ' sd-cal-has-lesson';
            const key = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            html += `<button type="button" class="${cls}" data-date-key="${key}">${day}</button>`;
        }

        html += '</div>';
        sdMiniCalendar.innerHTML = html;
    }

    function loadLessonsForCurrentMonth() {
        const now = new Date();
        const year = now.getFullYear();
        const month = now.getMonth() + 1;
        return fetch(`/api/my-lessons-month?year=${year}&month=${month}`)
            .then(r => r.json())
            .then(data => {
                monthLessons = data.lessons || [];
                lessonMapByDate = buildLessonMap(monthLessons);
                renderMiniCalendar();
                if (!selectedHomeworkTaskId) {
                    renderLessonInfoForDate(normalizeDateKey(now));
                }
            })
            .catch(() => {
                monthLessons = [];
                lessonMapByDate = {};
                renderMiniCalendar();
                if (!selectedHomeworkTaskId) {
                    renderLessonInfoForDate(normalizeDateKey(now));
                }
            });
    }

    // ===== Homework =====

    function hwStatusClass(hw) {
        if (hw.status_group === 'done') return 'sd-hw-done';
        if (hw.status_group === 'in_review') return 'sd-hw-inreview';
        if (hw.is_overdue) return 'sd-hw-overdue';
        if (hw.status_group === 'active' || hw.status_group === 'in_progress') return 'sd-hw-inprogress';
        return 'sd-hw-queue';
    }

    function hwStatusLabel(hw) {
        if (hw.status_name) return hw.status_name;
        if (hw.is_overdue) return 'Просрочено';
        return 'В очереди';
    }

    function hwStatusBadgeClass(hw) {
        if (hw.status_group === 'in_review') return 'sd-status-badge inreview';
        if (hw.status_group === 'done') return 'sd-status-badge done';
        if (hw.is_overdue) return 'sd-status-badge overdue';
        if (hw.status_group === 'active' || hw.status_group === 'in_progress') return 'sd-status-badge progress';
        return 'sd-status-badge queue';
    }

    function renderHomework() {
        if (homeworkData.length === 0) {
            sdHomeworkList.innerHTML = '<p class="sd-empty">Домашних заданий нет</p>';
            return;
        }
        let html = '';
        homeworkData.forEach((hw) => {
            const cls = hwStatusClass(hw);
            const statusLabel = hwStatusLabel(hw);
            const badgeCls = hwStatusBadgeClass(hw);
            const selectedClass = selectedHomeworkTaskId === hw.task_id ? ' sd-hw-selected' : '';
            const dateLabel = hw.lesson_date
                ? (hw.is_overdue
                    ? `<span class="sd-hw-overdue-label">Просрочено (${hw.lesson_date})</span>`
                    : `Выполнить до ${hw.lesson_date}`)
                : '';
            html += `
            <div class="sd-hw-card ${cls}${selectedClass}" data-task-id="${hw.task_id}">
                <div class="sd-hw-name">${hw.homework_name || '—'}</div>
                <div class="sd-hw-meta">
                    <span>Статус: <span class="${badgeCls}">${statusLabel}</span></span>
                </div>
                <div class="sd-hw-date">${dateLabel}</div>
            </div>`;
        });
        sdHomeworkList.innerHTML = html;
    }

    function loadHomework() {
        const showDone = sdShowDoneCb.checked ? '1' : '0';
        sdHomeworkList.innerHTML = '<p class="sd-loading">Загрузка…</p>';
        fetch(`/api/my-homework?show_done=${showDone}`)
            .then(r => r.json())
            .then(data => {
                homeworkData = data.homework || [];
                renderHomework();
                if (!selectedHomeworkTaskId && homeworkData.length) {
                    renderHomeworkCenter(homeworkData[0].task_id);
                } else if (selectedHomeworkTaskId) {
                    const exists = homeworkData.some(h => h.task_id === selectedHomeworkTaskId);
                    if (exists) renderHomeworkCenter(selectedHomeworkTaskId);
                    else if (homeworkData.length) renderHomeworkCenter(homeworkData[0].task_id);
                }
            })
            .catch(() => {
                sdHomeworkList.innerHTML = '<p class="sd-empty">Не удалось загрузить задания</p>';
            });
    }

    // ===== Learning Plan =====

    function loadPlan() {
        sdPlanContent.innerHTML = '<p class="sd-empty">Этот функционал на доработке</p>';
    }

    // ===== Teacher =====

    function loadTeacher() {
        fetch('/api/my-teacher')
            .then(r => r.json())
            .then(data => {
                if (!data.teacher) {
                    myTeacherCard.classList.add('hidden');
                    return;
                }
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
            .catch(() => {
                myTeacherCard.classList.add('hidden');
            });
    }

    // ===== Next Lesson =====

    function loadNextLesson() {
        fetch('/api/my-next-lesson')
            .then(r => r.json())
            .then(data => {
                if (data.lesson) {
                    nextLessonStartAt = new Date(data.lesson.start_date_iso);
                    startCountdown(data.lesson.start_date_iso);
                    if (data.lesson.plan_step_title) {
                        sdNextTopicValue.textContent = data.lesson.plan_step_title;
                        sdNextTopic.classList.remove('sd-hidden');
                    }
                    updateJoinLessonButtonVisibility();
                } else {
                    nextLessonStartAt = null;
                    sdTimerBlock.classList.add('sd-hidden');
                    updateJoinLessonButtonVisibility();
                }
            })
            .catch(() => {
                nextLessonStartAt = null;
                sdTimerBlock.classList.add('sd-hidden');
                updateJoinLessonButtonVisibility();
            });
    }

    // ===== Profile Actions =====

    sdProfileBtn.addEventListener('click', () => openModal(sdProfileModal));
    sdProfileModalClose.addEventListener('click', () => closeModal(sdProfileModal));
    sdProfileModal.addEventListener('click', e => { if (e.target === sdProfileModal) closeModal(sdProfileModal); });

    sdLogoutBtn.addEventListener('click', () => {
        fetch('/api/auth/logout', { method: 'POST' })
            .then(() => { window.location.href = '/login'; })
            .catch(() => { window.location.href = '/login'; });
    });

    sdTelegramBtn.addEventListener('click', () => {
        closeModal(sdProfileModal);
        window.location.href = '/?section=telegram';
    });

    sdChangePasswordBtn.addEventListener('click', () => {
        closeModal(sdProfileModal);
        sdCpForm.reset();
        sdCpError.classList.add('hidden');
        sdCpSuccess.classList.add('hidden');
        openModal(sdCpModal);
    });

    sdCpModalClose.addEventListener('click', () => closeModal(sdCpModal));
    sdCpCancel.addEventListener('click', () => closeModal(sdCpModal));
    sdCpModal.addEventListener('click', e => { if (e.target === sdCpModal) closeModal(sdCpModal); });

    sdCpForm.addEventListener('submit', e => {
        e.preventDefault();
        const oldPwd = sdOldPassword.value;
        const newPwd = sdNewPassword.value;
        const confirmPwd = sdConfirmPassword.value;
        if (newPwd !== confirmPwd) {
            showMsg(sdCpError, 'Пароли не совпадают', true);
            return;
        }
        fetch('/api/auth/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_password: oldPwd, new_password: newPwd }),
        })
            .then(r => r.json())
            .then(data => {
                if (data.error) {
                    showMsg(sdCpError, data.error, true);
                } else {
                    showMsg(sdCpSuccess, 'Пароль успешно изменён', false);
                    sdCpForm.reset();
                }
            })
            .catch(() => showMsg(sdCpError, 'Ошибка при смене пароля', true));
    });

    if (sdJoinLessonBtn) {
        sdJoinLessonBtn.addEventListener('click', () => {
            if (!meetingLinkUrl) {
                alert('Ссылка на урок не настроена');
                return;
            }
            const now = Date.now();
            const msToLesson = nextLessonStartAt ? (nextLessonStartAt.getTime() - now) : 0;
            const fifteenMinutes = 15 * 60 * 1000;
            if (msToLesson > fifteenMinutes) {
                openModal(sdJoinConfirmModal);
                return;
            }
            openLessonLink();
        });
    }

    if (sdJoinConfirmYes) {
        sdJoinConfirmYes.addEventListener('click', () => {
            closeModal(sdJoinConfirmModal);
            openLessonLink();
        });
    }

    if (sdJoinConfirmNo) {
        sdJoinConfirmNo.addEventListener('click', () => closeModal(sdJoinConfirmModal));
    }

    if (sdJoinConfirmModal) {
        sdJoinConfirmModal.addEventListener('click', e => {
            if (e.target === sdJoinConfirmModal) closeModal(sdJoinConfirmModal);
        });
    }

    // ===== Homework Toggle =====

    sdShowDoneCb.addEventListener('change', loadHomework);
    if (sdHomeworkList) {
        sdHomeworkList.addEventListener('click', (e) => {
            const card = e.target.closest('.sd-hw-card[data-task-id]');
            if (!card) return;
            const taskId = parseInt(card.dataset.taskId);
            renderHomeworkCenter(taskId);
        });
    }
    if (sdMiniCalendar) {
        sdMiniCalendar.addEventListener('click', (e) => {
            const cell = e.target.closest('.sd-cal-day[data-date-key]');
            if (!cell) return;
            sdMiniCalendar.querySelectorAll('.sd-cal-day').forEach(el => el.classList.remove('sd-cal-selected'));
            cell.classList.add('sd-cal-selected');
            renderLessonInfoForDate(cell.dataset.dateKey);
        });
    }
    if (sdCenterContent) {
        sdCenterContent.addEventListener('change', (e) => {
            if (e.target.id !== 'sd-evidence-input' || !selectedHomeworkTaskId) return;
            const input = e.target;
            const files = input.files ? Array.from(input.files) : [];
            input.value = '';
            if (!files.length) return;
            uploadEvidenceFiles(selectedHomeworkTaskId, files);
        });
        sdCenterContent.addEventListener('click', (e) => {
            const deleteBtn = e.target.closest('.sd-delete-evidence-btn');
            if (deleteBtn && selectedHomeworkTaskId) {
                const evidenceId = parseInt(deleteBtn.dataset.evidenceId);
                fetch(`/api/tasks/${selectedHomeworkTaskId}/evidence/${evidenceId}`, { method: 'DELETE' })
                    .then(() => {
                        showToast('Файл удалён');
                        renderHomeworkCenter(selectedHomeworkTaskId);
                    })
                    .catch(() => showToast('Не удалось удалить файл', true));
                return;
            }
            if (e.target.id === 'sd-submit-homework-btn' && selectedHomeworkTaskId) {
                fetch(`/api/tasks/${selectedHomeworkTaskId}/homework-submit`, { method: 'POST' })
                    .then(r => r.json().then(data => ({ ok: r.ok, data })))
                    .then(({ ok, data }) => {
                        if (!ok) {
                            showToast(data.error || 'Не удалось отправить задание', true);
                            return;
                        }
                        showToast('Задание отправлено учителю');
                        loadHomework();
                    })
                    .catch(() => showToast('Не удалось отправить задание', true));
            }
        });
    }

    // ===== Init =====

    fetch('/api/auth/me')
        .then(r => {
            if (!r.ok) throw new Error('Not authenticated');
            return r.json();
        })
        .then(user => {
            currentUser = user;
            sdUsername.textContent = user.display_name;

            // Hide change password for OAuth users
            if (user.auth_source !== 'local') {
                sdChangePasswordBtn.style.display = 'none';
            }

            loadNextLesson();
            loadMeetingLink();
            loadTeacher();
            loadHomework();
            loadLessonsForCurrentMonth();
            loadPlan();
        })
        .catch(() => {
            window.location.href = '/login';
        });
});
