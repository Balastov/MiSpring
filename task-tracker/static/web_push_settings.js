(function (global) {
    let pushEnabled = false;
    let pushPublicKey = '';
    let hasPushSubscription = false;

    function isBrowserSupported() {
        return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
    }

    function getPermission() {
        if (!('Notification' in window)) return 'unsupported';
        return Notification.permission;
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
        }).then((r) => r.json()).catch(() => ({}));
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
            .then((r) => r.json())
            .then((data) => {
                pushEnabled = !!(data && data.enabled && data.public_key);
                pushPublicKey = pushEnabled ? String(data.public_key) : '';
                return { enabled: pushEnabled, public_key: pushPublicKey };
            })
            .catch(() => {
                pushEnabled = false;
                pushPublicKey = '';
                return { enabled: false, public_key: '' };
            });
    }

    function fetchServerStatus() {
        return fetch('/api/chat/push/status')
            .then((r) => r.json())
            .catch(() => ({ server_enabled: false, subscribed: false, subscription_count: 0 }));
    }

    async function getLocalSubscription() {
        if (!isBrowserSupported()) return null;
        const reg = await navigator.serviceWorker.ready;
        return reg.pushManager.getSubscription();
    }

    async function syncSubscription() {
        if (!isBrowserSupported()) {
            hasPushSubscription = false;
            return false;
        }
        if (getPermission() !== 'granted') {
            hasPushSubscription = false;
            return false;
        }

        await fetchPushPublicKey();
        if (!pushEnabled || !pushPublicKey) {
            hasPushSubscription = false;
            return false;
        }

        try {
            const reg = await navigator.serviceWorker.ready;
            let sub = await reg.pushManager.getSubscription();
            if (!sub) {
                sub = await reg.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: urlBase64ToUint8Array(pushPublicKey),
                });
            }
            await sendPushSubscribe(sub);
            hasPushSubscription = true;
            return true;
        } catch (_) {
            hasPushSubscription = false;
            return false;
        }
    }

    async function enablePush() {
        if (!isBrowserSupported()) {
            throw new Error('Ваш браузер не поддерживает push-уведомления');
        }
        let perm = getPermission();
        if (perm === 'default') {
            perm = await Notification.requestPermission();
        }
        if (perm !== 'granted') {
            throw new Error('Разрешение на уведомления не получено. Разрешите уведомления в настройках браузера.');
        }
        const ok = await syncSubscription();
        if (!ok) {
            throw new Error('Не удалось подключить уведомления. Push может быть не настроен на сервере.');
        }
        return true;
    }

    async function disablePush() {
        if (isBrowserSupported()) {
            try {
                const reg = await navigator.serviceWorker.ready;
                const sub = await reg.pushManager.getSubscription();
                if (sub) {
                    const endpoint = sub.endpoint;
                    await sub.unsubscribe();
                    await sendPushUnsubscribe(endpoint);
                }
            } catch (_) {
                // ignore local unsubscribe errors
            }
        }
        await fetch('/api/chat/push/unsubscribe-all', { method: 'POST' });
        hasPushSubscription = false;
        return true;
    }

    async function sendTestPush() {
        const r = await fetch('/api/chat/push/test', { method: 'POST' });
        const data = await r.json().catch(() => ({}));
        if (!r.ok) {
            throw new Error(data.error || 'Не удалось отправить тестовое уведомление');
        }
        return data;
    }

    function isIos() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent)
            || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    }

    function buildStatusMessage(state) {
        if (!isBrowserSupported()) {
            return { type: 'error', text: 'Ваш браузер не поддерживает push-уведомления.' };
        }
        if (!state.serverEnabled) {
            return { type: 'warn', text: 'Push-уведомления временно недоступны (не настроены на сервере).' };
        }
        if (state.permission === 'denied') {
            return {
                type: 'error',
                text: 'Уведомления заблокированы в браузере. Разрешите их в настройках сайта и обновите страницу.',
            };
        }
        if (state.active) {
            return { type: 'ok', text: 'Уведомления включены на этом устройстве.' };
        }
        if (state.serverSubscribed && !state.localSubscribed) {
            return {
                type: 'info',
                text: 'Уведомления включены на другом устройстве. Нажмите «Включить», чтобы получать их здесь.',
            };
        }
        return { type: 'info', text: 'Уведомления выключены на этом устройстве.' };
    }

    function mount(container, options) {
        if (!container) return null;
        const opts = options || {};
        const showTitle = opts.showTitle !== false;

        container.innerHTML = `
            <div class="web-push-settings">
                ${showTitle ? '<h3>Настройка уведомлений</h3>' : ''}
                <p class="web-push-desc">
                    Push-уведомления в браузере на компьютере и телефоне — новые сообщения в чате и другие события,
                    даже когда вкладка закрыта.
                </p>
                <div class="web-push-status" id="web-push-status" aria-live="polite">Загрузка...</div>
                <div class="web-push-actions">
                    <button type="button" class="btn-primary" id="web-push-enable-btn">Включить уведомления</button>
                    <button type="button" class="btn-secondary hidden" id="web-push-disable-btn">Отключить</button>
                    <button type="button" class="btn-secondary hidden" id="web-push-test-btn">Проверить</button>
                </div>
                <p class="web-push-hint hidden" id="web-push-hint"></p>
                <p class="web-push-error hidden" id="web-push-error"></p>
            </div>
        `;

        const statusEl = container.querySelector('#web-push-status');
        const enableBtn = container.querySelector('#web-push-enable-btn');
        const disableBtn = container.querySelector('#web-push-disable-btn');
        const testBtn = container.querySelector('#web-push-test-btn');
        const hintEl = container.querySelector('#web-push-hint');
        const errorEl = container.querySelector('#web-push-error');

        function setError(msg) {
            if (!errorEl) return;
            if (!msg) {
                errorEl.classList.add('hidden');
                errorEl.textContent = '';
                return;
            }
            errorEl.textContent = msg;
            errorEl.classList.remove('hidden');
        }

        function setHint(msg) {
            if (!hintEl) return;
            if (!msg) {
                hintEl.classList.add('hidden');
                hintEl.textContent = '';
                return;
            }
            hintEl.textContent = msg;
            hintEl.classList.remove('hidden');
        }

        async function refresh() {
            setError('');
            statusEl.textContent = 'Загрузка...';
            statusEl.className = 'web-push-status';

            const server = await fetchServerStatus();
            const permission = getPermission();
            const localSub = await getLocalSubscription();
            const localSubscribed = !!localSub;
            const serverSubscribed = !!(server && server.subscribed);
            const serverEnabled = !!(server && server.server_enabled);
            const active = permission === 'granted' && localSubscribed && serverEnabled;

            hasPushSubscription = active || (permission === 'granted' && localSubscribed);

            const msg = buildStatusMessage({
                serverEnabled,
                permission,
                localSubscribed,
                serverSubscribed,
                active,
            });
            statusEl.textContent = msg.text;
            statusEl.classList.add(`web-push-status--${msg.type}`);

            enableBtn.classList.toggle('hidden', active || permission === 'denied' || !serverEnabled || !isBrowserSupported());
            disableBtn.classList.toggle('hidden', !active);
            testBtn.classList.toggle('hidden', !active);

            if (isIos() && !window.navigator.standalone) {
                setHint('На iPhone/iPad: откройте сайт в Safari, нажмите «Поделиться» → «На экран Домой», затем включите уведомления из приложения на главном экране.');
            } else if (permission === 'denied') {
                setHint('В Chrome: значок замка слева от адреса → Уведомления → Разрешить. В Safari: Настройки → Safari → Уведомления.');
            } else {
                setHint('');
            }
        }

        enableBtn.addEventListener('click', async () => {
            enableBtn.disabled = true;
            setError('');
            try {
                await enablePush();
                await refresh();
            } catch (e) {
                setError(e.message || 'Не удалось включить уведомления');
            } finally {
                enableBtn.disabled = false;
            }
        });

        disableBtn.addEventListener('click', async () => {
            disableBtn.disabled = true;
            setError('');
            try {
                await disablePush();
                await refresh();
            } catch (e) {
                setError(e.message || 'Не удалось отключить уведомления');
            } finally {
                disableBtn.disabled = false;
            }
        });

        testBtn.addEventListener('click', async () => {
            testBtn.disabled = true;
            setError('');
            try {
                await sendTestPush();
            } catch (e) {
                setError(e.message || 'Ошибка отправки');
            } finally {
                testBtn.disabled = false;
            }
        });

        refresh();
        return { refresh };
    }

    async function getDevicePushState() {
        const server = await fetchServerStatus();
        if (!server.server_enabled) {
            return {
                active: false,
                shouldPrompt: false,
                serverEnabled: false,
                supported: isBrowserSupported(),
            };
        }
        if (!isBrowserSupported()) {
            return {
                active: false,
                shouldPrompt: false,
                serverEnabled: true,
                supported: false,
            };
        }
        const permission = getPermission();
        const localSub = await getLocalSubscription();
        const active = permission === 'granted' && !!localSub;
        return {
            active,
            shouldPrompt: !active,
            serverEnabled: true,
            supported: true,
            permission,
            localSubscribed: !!localSub,
        };
    }

    global.MiSpringWebPush = {
        mount,
        enable: enablePush,
        disable: disablePush,
        syncSubscription,
        fetchPushPublicKey,
        getDevicePushState,
        isBrowserSupported,
        get hasPushSubscription() { return hasPushSubscription; },
    };
})(window);
