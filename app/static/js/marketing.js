/* ─── VeloSite Marketing — Interactions ─── */

(function () {
    'use strict';

    // ── Overlay menu toggle ──
    const toggle = document.querySelector('[data-menu-toggle]');
    const overlay = document.querySelector('[data-overlay]');

    if (toggle && overlay) {
        toggle.addEventListener('click', () => {
            const isOpen = overlay.classList.toggle('is-open');
            toggle.classList.toggle('is-open', isOpen);
            toggle.setAttribute('aria-expanded', String(isOpen));
            overlay.setAttribute('aria-hidden', String(!isOpen));
            document.body.style.overflow = isOpen ? 'hidden' : '';
        });

        // Close on link click
        overlay.querySelectorAll('a').forEach((link) => {
            link.addEventListener('click', () => {
                overlay.classList.remove('is-open');
                toggle.classList.remove('is-open');
                toggle.setAttribute('aria-expanded', 'false');
                overlay.setAttribute('aria-hidden', 'true');
                document.body.style.overflow = '';
            });
        });

        // Close on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && overlay.classList.contains('is-open')) {
                overlay.classList.remove('is-open');
                toggle.classList.remove('is-open');
                toggle.setAttribute('aria-expanded', 'false');
                overlay.setAttribute('aria-hidden', 'true');
                document.body.style.overflow = '';
            }
        });
    }

    // ── Scrolled header ──
    const header = document.querySelector('.m-header');
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
