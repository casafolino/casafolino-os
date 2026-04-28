/** @odoo-module **/
/**
 * Mail V3 Autoresponder Settings — OWL component for "Fuori Sede" configuration.
 *
 * Renders inside the settings drawer autoresponder tab.
 * Manages: date range, body per language, toggle, preview.
 */
import { Component, useState, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class MailV3SettingsAutoresponder extends Component {
    static template = "casafolino_mail.SettingsAutoresponder";
    static props = ["*"];

    setup() {
        this.state = useState({
            loading: true,
            saving: false,
            exists: false,
            active: false,
            date_start: '',
            date_end: '',
            subject_prefix: '[Fuori sede] ',
            body_html_it: '',
            body_html_en: '',
            body_html_es: '',
            contact_alternate_id: false,
            sent_count: 0,
            alternate_users: [],
            // UI state
            activeBodyTab: 'it',
            previewVisible: false,
            previewSubject: '',
            previewBody: '',
            toastMessage: '',
            toastType: 'success',
        });
        onWillStart(() => this.loadAutoresponder());
    }

    async loadAutoresponder() {
        this.state.loading = true;
        try {
            const res = await rpc('/cf/mail/v3/autoresponder/get');
            if (res.exists) {
                this.state.exists = true;
                this.state.active = res.active;
                this.state.date_start = res.date_start || '';
                this.state.date_end = res.date_end || '';
                this.state.subject_prefix = res.subject_prefix || '[Fuori sede] ';
                this.state.body_html_it = res.body_html_it || '';
                this.state.body_html_en = res.body_html_en || '';
                this.state.body_html_es = res.body_html_es || '';
                this.state.contact_alternate_id = res.contact_alternate_id || false;
                this.state.sent_count = res.sent_count || 0;
                this.state.alternate_users = res.alternate_users || [];
            } else {
                this.state.exists = false;
                this.state.alternate_users = res.alternate_users || [];
            }
        } catch (e) {
            console.error('[autoresponder] load error:', e);
        }
        this.state.loading = false;
    }

    onDateStartChange(ev) {
        this.state.date_start = ev.target.value;
    }

    onDateEndChange(ev) {
        this.state.date_end = ev.target.value;
    }

    onSubjectPrefixChange(ev) {
        this.state.subject_prefix = ev.target.value;
    }

    onBodyItChange(ev) {
        this.state.body_html_it = ev.target.value;
    }

    onBodyEnChange(ev) {
        this.state.body_html_en = ev.target.value;
    }

    onBodyEsChange(ev) {
        this.state.body_html_es = ev.target.value;
    }

    onAlternateChange(ev) {
        this.state.contact_alternate_id = ev.target.value ? parseInt(ev.target.value) : false;
    }

    switchBodyTab(ev) {
        const lang = ev.target.dataset.lang;
        if (lang) this.state.activeBodyTab = lang;
    }

    async save() {
        this.state.saving = true;
        try {
            const res = await rpc('/cf/mail/v3/autoresponder/save', {
                date_start: this.state.date_start || false,
                date_end: this.state.date_end || false,
                subject_prefix: this.state.subject_prefix,
                body_html_it: this.state.body_html_it,
                body_html_en: this.state.body_html_en,
                body_html_es: this.state.body_html_es,
                contact_alternate_id: this.state.contact_alternate_id,
            });
            if (res.success) {
                this.state.exists = true;
                this._showToast('Autoresponder salvato', 'success');
            }
        } catch (e) {
            console.error('[autoresponder] save error:', e);
            this._showToast('Errore salvataggio', 'danger');
        }
        this.state.saving = false;
    }

    async toggle() {
        try {
            const res = await rpc('/cf/mail/v3/autoresponder/toggle', {
                active: !this.state.active,
            });
            if (res.success) {
                this.state.active = res.active;
                this._showToast(
                    res.active ? 'Autoresponder attivato' : 'Autoresponder disattivato',
                    res.active ? 'success' : 'warning'
                );
            } else {
                this._showToast(res.error || 'Errore', 'danger');
            }
        } catch (e) {
            console.error('[autoresponder] toggle error:', e);
            this._showToast('Errore attivazione', 'danger');
        }
    }

    async preview() {
        try {
            // Save first to ensure server has latest data
            await this.save();
            const res = await rpc('/cf/mail/v3/autoresponder/preview', {
                lang: this.state.activeBodyTab,
                sender_name: 'Mario Rossi',
            });
            if (res.success) {
                this.state.previewSubject = res.subject;
                this.state.previewBody = res.body_html;
                this.state.previewVisible = true;
            }
        } catch (e) {
            console.error('[autoresponder] preview error:', e);
        }
    }

    closePreview() {
        this.state.previewVisible = false;
    }

    _showToast(message, type) {
        this.state.toastMessage = message;
        this.state.toastType = type;
        setTimeout(() => {
            this.state.toastMessage = '';
        }, 3000);
    }
}
