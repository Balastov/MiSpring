document.addEventListener('DOMContentLoaded', () => {
    const fab = document.getElementById('chat-fab');
    const fabBadge = document.getElementById('chat-fab-badge');
    const panel = document.getElementById('chat-panel');
    const panelClose = document.getElementById('chat-panel-close');
    const dialogsToggleBtn = document.getElementById('chat-dialogs-toggle-btn');
    const dialogList = document.getElementById('chat-dialog-list');
    const contactSelect = document.getElementById('chat-contact-select');
    const openBtn = document.getElementById('chat-open-btn');
    const newBlock = document.getElementById('chat-new-block');
    const mainContent = document.getElementById('chat-main-content');
    const activeTitle = document.getElementById('chat-active-title');
    const messagesEl = document.getElementById('chat-messages');
    const inputEl = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send-btn');

    if (!fab || !panel || !dialogList || !messagesEl || !inputEl || !sendBtn) return;

    let me = null;
    let dialogs = [];
    let contacts = [];
    let activeDialogId = null;
    let activePartnerName = '';
    let pollTimer = null;
    let prevUnreadTotal = 0;
    let prevUnreadByDialog = {};
    let unreadSoundPrimed = false;
    let unreadAudioCtx = null;

    function ensureAudioCtx() {
        if (!window.AudioContext && !window.webkitAudioContext) return null;
        if (!unreadAudioCtx) {
            const Ctx = window.AudioContext || window.webkitAudioContext;
            unreadAudioCtx = new Ctx();
        }
        if (unreadAudioCtx.state === 'suspended') {
            unreadAudioCtx.resume().catch(() => {});
        }
        return unreadAudioCtx;
    }

    function playUnreadSound() {
        if (!unreadSoundPrimed) return;
        if (document.visibilityState !== 'visible') return;
        const ctx = ensureAudioCtx();
        if (!ctx) return;
        try {
            const now = ctx.currentTime;
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(620, now);
            gain.gain.setValueAtTime(0.0001, now);
            gain.gain.exponentialRampToValueAtTime(0.045, now + 0.015);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.20);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(now);
            osc.stop(now + 0.22);
        } catch (_) {
            // ignore audio errors
        }
    }

    function primeUnreadSound() {
        if (unreadSoundPrimed) return;
        const ctx = ensureAudioCtx();
        if (!ctx) return;
        unreadSoundPrimed = true;
    }

    function hasRole(name) {
        return me && Array.isArray(me.roles) && me.roles.includes(name);
    }

    function isAllowedForChat() {
        return hasRole('student') || hasRole('teacher') || hasRole('admin') || hasRole('owner');
    }

    function showBadge(n) {
        const count = Number(n || 0);
        if (count <= 0) {
            fabBadge.classList.add('hidden');
            fab.classList.remove('chat-fab--pulse');
            prevUnreadTotal = 0;
            return;
        }
        if (count > prevUnreadTotal) {
            fab.classList.remove('chat-fab--pulse');
            // force reflow to restart css animation
            void fab.offsetWidth;
            fab.classList.add('chat-fab--pulse');
            if (prevUnreadTotal > 0) {
                playUnreadSound();
            }
        }
        prevUnreadTotal = count;
        fabBadge.textContent = count > 99 ? '99+' : String(count);
        fabBadge.classList.remove('hidden');
    }

    function fmtDateTime(iso) {
        if (!iso) return '';
        const d = new Date(iso);
        if (Number.isNaN(d.getTime())) return '';
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const hh = String(d.getHours()).padStart(2, '0');
        const mm = String(d.getMinutes()).padStart(2, '0');
        return `${day}.${m}.${y} ${hh}:${mm}`;
    }

    function escapeHtml(value) {
        const div = document.createElement('div');
        div.textContent = String(value || '');
        return div.innerHTML;
    }

    function setActiveDialog(dialogId, partnerName) {
        activeDialogId = dialogId;
        activePartnerName = partnerName || '';
        mainContent.classList.remove('hidden');
        activeTitle.textContent = activePartnerName || 'Диалог';
        renderDialogList();
        loadMessages(true);
        setSidebarCollapsed(true);
    }

    function setSidebarCollapsed(collapsed) {
        panel.classList.toggle('chat-sidebar-collapsed', !!collapsed);
        if (dialogsToggleBtn) {
            dialogsToggleBtn.textContent = collapsed ? 'Выберите диалог' : 'Скрыть диалоги';
        }
    }

    function renderDialogList() {
        dialogList.innerHTML = '';
        if (!dialogs.length) {
            dialogList.innerHTML = '<div class="chat-main-empty">Диалогов пока нет</div>';
            return;
        }

        dialogs.forEach((d) => {
            const item = document.createElement('div');
            const unread = Number(d.unread_count || 0);
            const prevUnread = Number(prevUnreadByDialog[d.id] || 0);
            const unreadIncreased = unread > prevUnread;
            item.className = `chat-dialog-item${d.id === activeDialogId ? ' active' : ''}${unreadIncreased ? ' unread-new' : ''}`;
            item.innerHTML = `
                <div class="chat-dialog-top">
                    <span class="chat-dialog-name">${escapeHtml(d.partner?.display_name || 'Пользователь')}</span>
                    ${unread > 0 ? `<span class="chat-dialog-unread">${unread}</span>` : ''}
                </div>
            `;
            item.addEventListener('click', () => setActiveDialog(d.id, d.partner?.display_name || 'Пользователь'));
            dialogList.appendChild(item);
        });
    }

    function renderContacts() {
        if (!contactSelect || !newBlock) return;
        contactSelect.innerHTML = '<option value="">Выберите собеседника</option>';
        contacts.forEach((c) => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.display_name;
            contactSelect.appendChild(opt);
        });
        newBlock.classList.toggle('hidden', contacts.length === 0);
    }

    function renderMessages(messages) {
        messagesEl.innerHTML = '';
        if (!messages.length) {
            messagesEl.innerHTML = '<div class="chat-main-empty">Сообщений пока нет</div>';
            return;
        }
        messages.forEach((m) => {
            const mine = m.sender_id === me.id;
            const row = document.createElement('div');
            row.className = `chat-msg ${mine ? 'mine' : 'theirs'}`;
            row.innerHTML = `
                <div>${escapeHtml(m.text)}</div>
                <div class="chat-msg-meta">${escapeHtml(m.sender_name || '')} · ${fmtDateTime(m.created_at_iso)}</div>
            `;
            messagesEl.appendChild(row);
        });
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function refreshUnreadCount() {
        return fetch('/api/chat/unread-count')
            .then(r => r.json())
            .then(data => showBadge(data.unread_count || 0))
            .catch(() => {});
    }

    function loadDialogs() {
        return fetch('/api/chat/dialogs')
            .then(r => r.json())
            .then(data => {
                dialogs = Array.isArray(data.dialogs) ? data.dialogs : [];
                contacts = Array.isArray(data.contacts) ? data.contacts : [];
                renderDialogList();
                renderContacts();
                const nextMap = {};
                dialogs.forEach(d => { nextMap[d.id] = Number(d.unread_count || 0); });
                prevUnreadByDialog = nextMap;
                if (activeDialogId && !dialogs.some(d => d.id === activeDialogId)) {
                    activeDialogId = null;
                    mainContent.classList.add('hidden');
                }
            });
    }

    function markRead() {
        if (!activeDialogId) return Promise.resolve();
        return fetch(`/api/chat/dialogs/${activeDialogId}/read`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        })
            .then(() => refreshUnreadCount())
            .catch(() => {});
    }

    function loadMessages(withRead) {
        if (!activeDialogId) return Promise.resolve();
        return fetch(`/api/chat/dialogs/${activeDialogId}/messages?limit=100`)
            .then(r => r.json())
            .then(data => {
                renderMessages(Array.isArray(data.messages) ? data.messages : []);
            })
            .then(() => (withRead ? markRead() : Promise.resolve()))
            .catch(() => {});
    }

    function openOrCreateDialogWith(partnerId) {
        return fetch('/api/chat/dialogs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ partner_id: Number(partnerId) }),
        })
            .then(r => r.json().then(data => ({ ok: r.ok, data })))
            .then(({ ok, data }) => {
                if (!ok) throw new Error(data.error || 'Не удалось открыть диалог');
                const d = data.dialog;
                return loadDialogs().then(() => {
                    setActiveDialog(d.id, d.partner?.display_name || '');
                });
            });
    }

    function sendMessage() {
        const text = (inputEl.value || '').trim();
        if (!activeDialogId || !text) return;
        fetch(`/api/chat/dialogs/${activeDialogId}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        })
            .then(r => r.json().then(data => ({ ok: r.ok, data })))
            .then(({ ok, data }) => {
                if (!ok) throw new Error(data.error || 'Не удалось отправить сообщение');
                inputEl.value = '';
                return Promise.all([loadMessages(false), loadDialogs(), refreshUnreadCount()]);
            })
            .catch((e) => {
                alert(e.message || 'Ошибка отправки сообщения');
            });
    }

    function startPolling() {
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(() => {
            refreshUnreadCount();
            if (!panel.classList.contains('hidden')) {
                loadDialogs().then(() => {
                    if (activeDialogId) loadMessages(false);
                }).catch(() => {});
            }
        }, 5000);
    }

    function init() {
        fetch('/api/auth/me')
            .then(r => r.json())
            .then(user => {
                me = user;
                if (!isAllowedForChat()) return;
                fab.classList.remove('hidden');
                refreshUnreadCount();
                startPolling();
                loadDialogs();
            })
            .catch(() => {});
    }

    fab.addEventListener('click', () => {
        primeUnreadSound();
        panel.classList.toggle('hidden');
        if (!panel.classList.contains('hidden')) {
            setSidebarCollapsed(true);
            loadDialogs().then(() => {
                if (activeDialogId) loadMessages(true);
            }).catch(() => {});
        }
    });

    document.addEventListener('keydown', primeUnreadSound, { once: true });
    document.addEventListener('click', primeUnreadSound, { once: true });
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') primeUnreadSound();
    });

    if (panelClose) {
        panelClose.addEventListener('click', () => panel.classList.add('hidden'));
    }

    if (dialogsToggleBtn) {
        dialogsToggleBtn.addEventListener('click', () => {
            const collapsed = panel.classList.contains('chat-sidebar-collapsed');
            setSidebarCollapsed(!collapsed);
        });
    }

    if (openBtn && contactSelect) {
        openBtn.addEventListener('click', () => {
            const partnerId = Number(contactSelect.value || 0);
            if (!partnerId) return;
            openOrCreateDialogWith(partnerId).catch((e) => alert(e.message || 'Ошибка открытия диалога'));
        });
    }

    sendBtn.addEventListener('click', sendMessage);
    inputEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    init();
});
