(function (global) {
    const DISMISS_KEY = 'mispring-push-banner-dismissed-until';
    const DISMISS_MS = 24 * 60 * 60 * 1000;
    let bannerEl = null;

    function isDismissed() {
        try {
            const until = parseInt(global.localStorage.getItem(DISMISS_KEY) || '0', 10);
            return until > Date.now();
        } catch (_) {
            return false;
        }
    }

    function dismissBanner() {
        try {
            global.localStorage.setItem(DISMISS_KEY, String(Date.now() + DISMISS_MS));
        } catch (_) {
            // ignore
        }
        hideBanner();
    }

    function clearDismissIfActive(active) {
        if (!active) return;
        try {
            global.localStorage.removeItem(DISMISS_KEY);
        } catch (_) {
            // ignore
        }
    }

    function getGreeting() {
        const hour = new Date().getHours();
        if (hour >= 5 && hour < 12) return 'Доброе утро!';
        if (hour >= 12 && hour < 18) return 'Добрый день!';
        return 'Добрый вечер!';
    }

    function getBannerCopy(variant) {
        if (variant === 'teacher') {
            return {
                lines: [
                    'На сайте есть удобный чат, в котором вы можете переписываться с учениками.',
                    'Чтобы не пропустить сообщение, включите уведомления в разделе «Настройки → Ссылки и интеграции».',
                    'Важно! На каждом устройстве нужно отдельно включить уведомления — такая вот особенность =)',
                ],
            };
        }
        return {
            lines: [
                'На сайте есть удобный чат, в котором вы можете переписываться с учителем.',
                'Чтобы не пропустить сообщение, включите уведомления в Личном кабинете.',
                'Важно! На каждом устройстве нужно отдельно включить уведомления — такая вот особенность =)',
            ],
        };
    }

    function hideBanner() {
        if (!bannerEl) return;
        bannerEl.classList.add('hidden');
        document.body.classList.remove('push-banner-visible');
    }

    function removeBanner() {
        if (!bannerEl) return;
        bannerEl.remove();
        bannerEl = null;
        document.body.classList.remove('push-banner-visible');
    }

    function openPushSettings() {
        if (typeof global.MiSpringOpenPushSettings === 'function') {
            global.MiSpringOpenPushSettings();
            return;
        }
        if (typeof global.MiSpringOpenPushSettingsFallback === 'function') {
            global.MiSpringOpenPushSettingsFallback();
        }
    }

    function renderBanner(variant) {
        const copy = getBannerCopy(variant);
        const el = document.createElement('div');
        el.id = 'push-prompt-banner';
        el.className = 'push-prompt-banner';
        el.setAttribute('role', 'region');
        el.setAttribute('aria-label', 'Напоминание об уведомлениях');

        const textHtml = [
            `<p class="push-prompt-banner-greeting">${getGreeting()}</p>`,
            ...copy.lines.map((line) => `<p>${line}</p>`),
        ].join('');

        el.innerHTML = `
            <button type="button" class="push-prompt-banner-close" aria-label="Закрыть">&times;</button>
            <div class="push-prompt-banner-content">
                <div class="push-prompt-banner-text">${textHtml}</div>
                <button type="button" class="btn-primary push-prompt-banner-action">Настройка уведомлений</button>
            </div>
        `;

        el.querySelector('.push-prompt-banner-close').addEventListener('click', dismissBanner);
        el.querySelector('.push-prompt-banner-action').addEventListener('click', openPushSettings);

        const anchor = document.querySelector('.sd-topbar')
            || document.querySelector('.top-bar')
            || document.body.firstChild;
        if (anchor && anchor.parentNode) {
            anchor.insertAdjacentElement('afterend', el);
        } else {
            document.body.prepend(el);
        }

        bannerEl = el;
        document.body.classList.add('push-banner-visible');
    }

    async function refresh(options) {
        const push = global.MiSpringWebPush;
        if (!push || typeof push.getDevicePushState !== 'function') return;

        let state;
        try {
            if ('serviceWorker' in navigator) {
                await navigator.serviceWorker.ready;
            }
            state = await push.getDevicePushState();
        } catch (_) {
            return;
        }

        clearDismissIfActive(state.active);

        if (state.active) {
            removeBanner();
            return;
        }
        if (!state.shouldPrompt || isDismissed()) {
            hideBanner();
            return;
        }

        const variant = (options && options.variant) || 'student';
        if (!bannerEl) {
            renderBanner(variant);
        } else {
            bannerEl.classList.remove('hidden');
            document.body.classList.add('push-banner-visible');
        }
    }

    async function init(options) {
        await refresh(options);
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') refresh(options);
        });
    }

    global.MiSpringPushBanner = {
        init,
        refresh,
        dismiss: dismissBanner,
        hide: hideBanner,
    };
})(window);
