document.addEventListener('DOMContentLoaded', () => {

    // ===== State =====
    let currentUser = null;
    let timerInterval = null;
    let homeworkData = [];
    let nextLessonStartAt = null;
    let meetingLinkUrl = '';

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

    // ===== Helpers =====

    function openModal(el) { el.classList.remove('hidden'); }
    function closeModal(el) { el.classList.add('hidden'); }

    function showMsg(el, msg, isError) {
        el.textContent = msg;
        el.classList.remove('hidden');
        setTimeout(() => el.classList.add('hidden'), 4000);
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
        homeworkData.forEach((hw) => {
            const cls = hwStatusClass(hw);
            const statusLabel = hwStatusLabel(hw);
            const dateLabel = hw.lesson_date
                ? (hw.is_overdue
                    ? `<span class="sd-hw-overdue-label">Просрочено (${hw.lesson_date})</span>`
                    : `Выполнить до ${hw.lesson_date}`)
                : '';
            html += `
            <div class="sd-hw-card ${cls}">
                <div class="sd-hw-name">${hw.homework_name || '—'}</div>
                <div class="sd-hw-meta">
                    <span>Статус: <b>${statusLabel}</b></span>
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
            loadPlan();
        })
        .catch(() => {
            window.location.href = '/login';
        });
});
