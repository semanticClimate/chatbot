window.addEventListener('message', function(e) {
    var data = e.data;
    if (!data || !data.type) return;

    // ── Remove all previous highlights ──────────────────────────────────────
    document.querySelectorAll('.ca-highlight').forEach(function(el) {
        el.classList.remove('ca-highlight');
    });
    document.querySelectorAll('.ca-para-highlight').forEach(function(el) {
        el.classList.remove('ca-para-highlight');
    });

    // ── PARAGRAPH jump (precise — from "View Source" button) ────────────────
    if (data.type === 'ca-jump-para') {
        var anchorId = data.anchor_id || '';
        var target   = anchorId ? document.getElementById(anchorId) : null;

        // Fallback: try section-level wrapper if paragraph not found
        if (!target && data.section) {
            target = document.querySelector('.ca-section[data-section-number="' + data.section + '"]');
            if (target) target.classList.add('ca-highlight');
        } else if (target) {
            target.classList.add('ca-para-highlight');
        }

        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        return;
    }

    // ── SECTION jump (legacy, from chip buttons) ─────────────────────────────
    if (data.type === 'ca-jump') {
        var sec    = data.section;
        var kws    = data.keywords || [];
        var origId = data.heading_id || '';
        var target = null;

        target = document.querySelector('.ca-section[data-section-number="' + sec + '"]');
        if (!target) target = document.querySelector('[data-section-number="' + sec + '"]');
        if (!target) target = document.getElementById('section-' + sec.replace(/\./g, '-'));
        if (!target && origId) {
            target = document.getElementById(origId);
            if (target) { var w = target.closest('.ca-section'); if (w) target = w; }
        }

        if (target) {
            target.classList.add('ca-highlight');
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
});
