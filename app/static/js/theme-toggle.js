/**
 * VeloSite — Theme Toggle
 * Persists user preference (light / dark) via localStorage.
 */
(function () {
    const STORAGE_KEY = 'theme';
    const DARK = 'dark';
    const root = document.documentElement;
    const btn = document.getElementById('theme-toggle');

    function isDark() {
        return root.getAttribute('data-theme') === DARK;
    }

    function updateIcon() {
        if (!btn) return;
        btn.setAttribute('aria-label', isDark() ? 'Switch to light mode' : 'Switch to dark mode');
        btn.textContent = isDark() ? '☀️' : '🌙';
    }

    // Apply saved preference (already done by inline <script> in <head>,
    // but this ensures the icon is correct).
    updateIcon();

    if (btn) {
        btn.addEventListener('click', function () {
            if (isDark()) {
                root.removeAttribute('data-theme');
                localStorage.setItem(STORAGE_KEY, 'light');
            } else {
                root.setAttribute('data-theme', DARK);
                localStorage.setItem(STORAGE_KEY, DARK);
            }
            updateIcon();
        });
    }
})();
