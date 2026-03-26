/* ─── VeloSite Marketing — Interactions ─── */

(function () {
    'use strict';

    // ── Overlay menu toggle ──
    const toggles = document.querySelectorAll('[data-menu-toggle]');
    const overlay = document.querySelector('[data-overlay]');
    const header  = document.querySelector('[data-m-header]');

    function openMenu() {
        if (!overlay) return;
        overlay.classList.add('is-open');
        overlay.setAttribute('aria-hidden', 'false');
        document.body.classList.add('menu-is-open');

        // Hide the underlying header so there's no double nav
        if (header) header.classList.add('is-hidden');

        // Update all toggle buttons
        toggles.forEach(t => t.setAttribute('aria-expanded', 'true'));

        // Focus the first link in the overlay
        requestAnimationFrame(() => {
            const first = overlay.querySelector('.m-overlay-link, .m-overlay-close');
            if (first) first.focus();
        });
    }

    function closeMenu() {
        if (!overlay) return;
        overlay.classList.remove('is-open');
        overlay.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('menu-is-open');

        // Show the header again
        if (header) header.classList.remove('is-hidden');

        // Update all toggle buttons
        toggles.forEach(t => {
            t.setAttribute('aria-expanded', 'false');
            t.classList.remove('is-open');
        });

        // Return focus to the original hamburger
        const hamburger = document.querySelector('.m-menu-toggle');
        if (hamburger) hamburger.focus();
    }

    if (toggles.length && overlay) {
        toggles.forEach(btn => {
            btn.addEventListener('click', () => {
                const isOpen = overlay.classList.contains('is-open');
                if (isOpen) closeMenu();
                else openMenu();
            });
        });

        // Close on link click inside overlay
        overlay.querySelectorAll('a, button[type="submit"]').forEach(el => {
            el.addEventListener('click', () => {
                // Small delay so the navigation starts before closing
                setTimeout(closeMenu, 80);
            });
        });

        // Close on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && overlay.classList.contains('is-open')) {
                closeMenu();
            }
        });

        // Focus trap inside overlay
        overlay.addEventListener('keydown', (e) => {
            if (e.key !== 'Tab') return;
            const focusable = overlay.querySelectorAll(
                'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
            );
            if (!focusable.length) return;
            const first = focusable[0];
            const last  = focusable[focusable.length - 1];

            if (e.shiftKey) {
                if (document.activeElement === first) {
                    e.preventDefault();
                    last.focus();
                }
            } else {
                if (document.activeElement === last) {
                    e.preventDefault();
                    first.focus();
                }
            }
        });
    }

    // ── Scrolled header ──
    if (header) {
        const onScroll = () => {
            header.classList.toggle('is-scrolled', window.scrollY > 20);
        };
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }

    // ── Showcase filter ──
    const filters = document.querySelectorAll('[data-showcase-filter]');
    const cards = document.querySelectorAll('[data-showcase-card]');

    if (filters.length && cards.length) {
        filters.forEach((btn) => {
            btn.addEventListener('click', () => {
                filters.forEach((f) => f.classList.remove('is-active'));
                btn.classList.add('is-active');

                const filter = btn.dataset.showcaseFilter;
                cards.forEach((card) => {
                    const categories = (card.dataset.category || '').toLowerCase();
                    const show = filter === 'all' || categories.includes(filter);
                    card.style.display = show ? '' : 'none';
                });
            });
        });
    }
})();
