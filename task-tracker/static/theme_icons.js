/* Подставляет light/dark иконки и manifest по системной теме устройства. */
(function () {
  function isDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function syncAppIcons() {
    const dark = isDark();
    const manifest = document.getElementById('app-manifest');
    if (manifest) {
      manifest.href = dark ? '/static/manifest-dark.json' : '/static/manifest-light.json';
    }
    const apple = document.getElementById('app-apple-touch-icon');
    if (apple) {
      apple.href = dark ? '/static/apple-touch-icon-dark.png' : '/static/apple-touch-icon-light.png';
    }
  }

  syncAppIcons();
  if (window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    if (typeof mq.addEventListener === 'function') {
      mq.addEventListener('change', syncAppIcons);
    } else if (typeof mq.addListener === 'function') {
      mq.addListener(syncAppIcons);
    }
  }
})();
