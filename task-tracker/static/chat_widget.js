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
    let unreadNotifyPrimed = false;
    let lastUnreadNotifyAt = 0;
    let pushPublicKey = '';
    let pushEnabled = false;
    let hasPushSubscription = false;

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
            // 4-note motif: A#4, F5, A#4, E5 with 0.3s spacing.
            const notes = [466.16, 698.46, 466.16, 659.25];
            const step = 0.3;
            const duration = 0.2;
            notes.forEach((freq, index) => {
                const start = now + (index * step);
                const end = start + duration;
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, start);
                // Linear envelope is more stable across browsers than exponential ramps.
                gain.gain.setValueAtTime(0, start);
                gain.gain.linearRampToValueAtTime(0.12, start + 0.02);
                gain.gain.linearRampToValueAtTime(0.09, start + 0.08);
                gain.gain.linearRampToValueAtTime(0, end);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(start);
                osc.stop(end + 0.01);
            });
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

    function notifyUnread(count) {
        if (!('Notification' in window)) return;
        if (Notification.permission !== 'granted') return;
        // Throttle noisy polling updates.
        const now = Date.now();
        if (now - lastUnreadNotifyAt < 4000) return;
        lastUnreadNotifyAt = now;
        const title = 'MiSpring: новое сообщение';
        const body = count > 1
            ? `У вас ${count} непрочитанных сообщений`
            : 'У вас новое непрочитанное сообщение';
        try {
            const n = new Notification(title, { body, tag: 'mispring-chat-unread', renotify: true });
            n.onclick = () => {
                try { window.focus(); } catch (_) {}
                panel.classList.remove('hidden');
                setSidebarCollapsed(true);
                loadDialogs().then(() => {
                    if (activeDialogId) loadMessages(true);
                }).catch(() => {});
                n.close();
            };
        } catch (_) {
            // ignore notification errors
        }
    }

    function primeUnreadNotifications() {
        if (unreadNotifyPrimed) return;
        if (!('Notification' in window)) return;
        unreadNotifyPrimed = true;
        if (Notification.permission === 'default') {
            Notification.requestPermission().then((perm) => {
                if (perm === 'granted') syncPushSubscription();
            }).catch(() => {});
        }
    }

    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
        const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        const raw = window.atob(base64);
        const out = new Uint8Array(raw.length);
        for (let i = 0; i < raw.length; ++i) out[i] = raw.charCodeAt(i);
        return out;
    }

    function sendPushSubscribe(subscription) {
        if (!subscription) return Promise.resolve();
        const json = subscription.toJSON ? subscription.toJSON() : subscription;
        return fetch('/api/chat/push/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                endpoint: json.endpoint,
                keys: json.keys || {},
            }),
        }).catch(() => {});
    }

    function sendPushUnsubscribe(endpoint) {
        if (!endpoint) return Promise.resolve();
        return fetch('/api/chat/push/unsubscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ endpoint }),
        }).catch(() => {});
    }

    function fetchPushPublicKey() {
        return fetch('/api/chat/push/public-key')
            .then(r => r.json())
            .then((data) => {
                pushEnabled = !!(data && data.enabled && data.public_key);
                pushPublicKey = pushEnabled ? String(data.public_key) : '';
            })
            .catch(() => {
                pushEnabled = false;
                pushPublicKey = '';
            });
    }

    function syncPushSubscription() {
        if (!isAllowedForChat()) return Promise.resolve(false);
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) return Promise.resolve(false);
        if (!('Notification' in window)) return Promise.resolve(false);
        if (Notification.permission !== 'granted') return Promise.resolve(false);

        return fetchPushPublicKey().then(() => {
            if (!pushEnabled || !pushPublicKey) return false;
            return navigator.serviceWorker.ready.then((reg) => {
                return reg.pushManager.getSubscription().then((current) => {
                    if (current) {
                        hasPushSubscription = true;
                        return sendPushSubscribe(current).then(() => true);
                    }
                    return reg.pushManager.subscribe({
                        userVisibleOnly: true,
                        applicationServerKey: urlBase64ToUint8Array(pushPublicKey),
                    }).then((sub) => {
                        hasPushSubscription = true;
                        return sendPushSubscribe(sub).then(() => true);
                    });
                });
            });
        }).catch(() => false);
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
            playUnreadSound();
            if (document.visibilityState !== 'visible' && !hasPushSubscription) {
                notifyUnread(count);
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

    function isStudentOnlyUser() {
        return hasRole('student') && !hasRole('teacher') && !hasRole('admin') && !hasRole('owner');
    }

    function shouldOpenDialogsListByDefault() {
        return hasRole('admin') || hasRole('teacher');
    }

    function ensureStudentDialogSelected() {
        if (!isStudentOnlyUser()) return Promise.resolve(false);
        if (activeDialogId && dialogs.some(d => d.id === activeDialogId)) return Promise.resolve(false);
        if (dialogs.length) {
            const firstDialog = dialogs[0];
            setActiveDialog(firstDialog.id, firstDialog.partner?.display_name || 'Учитель');
            return Promise.resolve(true);
        }
        if (contacts.length) {
            return openOrCreateDialogWith(contacts[0].id).then(() => true).catch(() => false);
        }
        return Promise.resolve(false);
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
                    return ensureStudentDialogSelected();
                }).then((activated) => {
                    if (activeDialogId && !activated) loadMessages(false);
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
                if (Notification.permission === 'granted') {
                    syncPushSubscription();
                }
                refreshUnreadCount();
                startPolling();
                loadDialogs();
            })
            .catch(() => {});
    }

    fab.addEventListener('click', () => {
        primeUnreadSound();
        primeUnreadNotifications();
        panel.classList.toggle('hidden');
        if (!panel.classList.contains('hidden')) {
            setSidebarCollapsed(!shouldOpenDialogsListByDefault());
            loadDialogs().then(() => {
                return ensureStudentDialogSelected();
            }).then((activated) => {
                if (activeDialogId && !activated) loadMessages(true);
            }).catch(() => {});
        }
    });

    const primeNotificationsOnInteract = () => {
        primeUnreadSound();
        primeUnreadNotifications();
        if (Notification.permission === 'granted') syncPushSubscription();
    };

    document.addEventListener('keydown', primeNotificationsOnInteract, { once: true });
    document.addEventListener('click', primeNotificationsOnInteract, { once: true });
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            primeUnreadSound();
            primeUnreadNotifications();
            if (Notification.permission === 'granted') syncPushSubscription();
        }
    });

    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.addEventListener('message', (event) => {
            const msg = event && event.data ? event.data : null;
            if (!msg || msg.type !== 'chat-open') return;
            panel.classList.remove('hidden');
            setSidebarCollapsed(true);
            loadDialogs().then(() => ensureStudentDialogSelected()).then((activated) => {
                if (activeDialogId && !activated) loadMessages(true);
            }).catch(() => {});
        });
    }

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
