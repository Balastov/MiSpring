document.addEventListener('DOMContentLoaded', () => {

    // ===== State =====
    let currentUser = null;
    let timerInterval = null;
    let homeworkData = [];

    // ===== Element refs =====
    const sdUsername = document.getElementById('sd-username');
    const sdTimerBlock = document.getElementById('sd-timer-block');
    const sdTimerDays = document.getElementById('sd-timer-days');
    const sdTimerHours = document.getElementById('sd-timer-hours');
    const sdTimerMinutes = document.getElementById('sd-timer-minutes');
    const sdTimerSeconds = document.getElementById('sd-timer-seconds');
    const sdNextTopicValue = document.getElementById('sd-next-topic-value');
    const sdNextTopic = document.getElementById('sd-next-topic');

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

    // ===== Helpers =====

    function openModal(el) { el.classList.remove('hidden'); }
    function closeModal(el) { el.classList.add('hidden'); }

    function showMsg(el, msg, isError) {
        el.textContent = msg;
        el.classList.remove('hidden');
        setTimeout(() => el.classList.add('hidden'), 4000);
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
            sdTimerSeconds.textContent = String(totalSec % 60).padStart(2, '0');
        }
        tick();
        timerInterval = setInterval(tick, 1000);
        sdTimerBlock.classList.remove('sd-hidden');
    }

    // ===== Mini Calendar =====

    function renderMiniCalendar() {
        const now = new Date();
        const year = now.getFullYear();
        const month = now.getMonth();
        const today = now.getDate();

        const monthNames = ['Январь','Февраль','Март','Апрель','Май','Июнь',
                            'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
        const dayNames = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];

        // days with homework lessons
        const lessonDays = new Set();
        homeworkData.forEach(hw => {
            if (hw.lesson_date_iso) {
                const d = new Date(hw.lesson_date_iso);
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
            if (lessonDays.has(day)) cls += ' sd-cal-has-lesson';
            html += `<div class="${cls}">${day}</div>`;
        }

        html += '</div>';
        sdMiniCalendar.innerHTML = html;
    }

    // ===== Homework =====

    function hwStatusClass(hw) {
        if (hw.status_group === 'done') return 'sd-hw-done';
        if (hw.is_overdue) return 'sd-hw-overdue';
        if (hw.status_group === 'active' || hw.status_group === 'in_progress') return 'sd-hw-inprogress';
        return 'sd-hw-queue';
    }

    function hwStatusLabel(hw) {
        if (hw.status_name) return hw.status_name;
        if (hw.is_overdue) return 'Просрочено';
        return 'В очереди';
    }

    function renderHomework() {
        if (homeworkData.length === 0) {
            sdHomeworkList.innerHTML = '<p class="sd-empty">Домашних заданий нет</p>';
            return;
        }
        let html = '';
        homeworkData.forEach((hw, idx) => {
            const cls = hwStatusClass(hw);
            const statusLabel = hwStatusLabel(hw);
            const dateLabel = hw.lesson_date
                ? (hw.is_overdue
                    ? `<span class="sd-hw-overdue-label">Просрочено (${hw.lesson_date})</span>`
                    : `Выполнить до ${hw.lesson_date}`)
                : '';
            html += `
            <div class="sd-hw-card ${cls}">
                <div class="sd-hw-num">Домашнее задание №${idx + 1}</div>
                <div class="sd-hw-name">${hw.homework_name || '—'}</div>
                <div class="sd-hw-meta">
                    <span>Статус: <b>${statusLabel}</b></span>
                    <span class="sd-hw-result">Результат: <b>—</b></span>
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
                renderMiniCalendar();
            })
            .catch(() => {
                sdHomeworkList.innerHTML = '<p class="sd-empty">Не удалось загрузить задания</p>';
            });
    }

    // ===== Learning Plan =====

    function loadPlan() {
        fetch('/api/my-plan')
            .then(r => {
                if (r.status === 404) return null;
                if (!r.ok) throw new Error();
                return r.json();
            })
            .then(data => {
                if (!data || !data.template) {
                    sdPlanContent.innerHTML = '<p class="sd-empty">План обучения ещё не назначен</p>';
                    return;
                }
                const p = data.progress;
                const pct = p ? p.percent : 0;
                const done = p ? p.conducted : 0;
                const total = p ? p.total : 0;

                // Find next step
                const steps = data.steps || [];
                let nextStepTitle = null;
                if (data.next_step_id) {
                    const next = steps.find(s => s.id === data.next_step_id);
                    if (next) nextStepTitle = next.title;
                }

                sdPlanContent.innerHTML = `
                    <div class="sd-plan-name">${data.template.name}</div>
                    <div class="sd-plan-progress-wrap">
                        <div class="sd-plan-progress-label">
                            <span>${done} из ${total} тем пройдено</span>
                            <span>${pct}%</span>
                        </div>
                        <div class="sd-plan-progress-track">
                            <div class="sd-plan-progress-fill" style="width:${pct}%"></div>
                        </div>
                    </div>
                    ${nextStepTitle ? `<div class="sd-plan-next">Следующая тема: <b>${nextStepTitle}</b></div>` : ''}
                    <button class="sd-btn-link" id="sd-view-plan-btn">Посмотреть весь план →</button>
                `;
                document.getElementById('sd-view-plan-btn')?.addEventListener('click', () => {
                    window.location.href = '/?plan=1';
                });
            })
            .catch(() => {
                sdPlanContent.innerHTML = '<p class="sd-empty">Не удалось загрузить план</p>';
            });
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
                    startCountdown(data.lesson.start_date_iso);
                    if (data.lesson.plan_step_title) {
                        sdNextTopicValue.textContent = data.lesson.plan_step_title;
                        sdNextTopic.classList.remove('sd-hidden');
                    }
                } else {
                    sdTimerBlock.classList.add('sd-hidden');
                }
            })
            .catch(() => {
                sdTimerBlock.classList.add('sd-hidden');
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

    // ===== Homework Toggle =====

    sdShowDoneCb.addEventListener('change', loadHomework);

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
            loadTeacher();
            loadHomework();
            loadPlan();
        })
        .catch(() => {
            window.location.href = '/login';
        });
});
