/** @odoo-module **/

/**
 * Keyboard shortcuts for Orphan Triage form.
 * Keys 1-5 trigger triage buttons, S triggers skip.
 * Disabled when focus is on input/textarea to avoid conflicts.
 */
document.addEventListener('keydown', (ev) => {
    const tag = (ev.target && ev.target.tagName) || '';
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag.toUpperCase())) {
        return;
    }
    if (ev.target && ev.target.isContentEditable) {
        return;
    }

    const triageForm = document.querySelector('.o_casafolino_triage_form');
    if (!triageForm) {
        return;
    }

    const keyMap = {
        '1': 'action_triage_lead',
        '2': 'action_triage_assign',
        '3': 'action_triage_snippet',
        '4': 'action_triage_ignore_sender',
        '5': 'action_triage_ignore_domain',
        's': 'action_triage_skip',
        'S': 'action_triage_skip',
    };

    const actionName = keyMap[ev.key];
    if (!actionName) {
        return;
    }

    const btn = triageForm.querySelector(`button[name="${actionName}"]`);
    if (btn && !btn.disabled) {
        ev.preventDefault();
        btn.click();
    }
});
