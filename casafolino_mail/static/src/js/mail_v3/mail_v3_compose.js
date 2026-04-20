/** @odoo-module **/
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class ComposeWizard extends Component {
    static template = "casafolino_mail.ComposeWizard";
    static props = ["*"];

    setup() {
        this.state = useState({
            to: this.props.prefilled?.to || '',
            cc: this.props.prefilled?.cc || '',
            bcc: this.props.prefilled?.bcc || '',
            subject: this.props.prefilled?.subject || '',
            body: this.props.prefilled?.body_html || '',
            sending: false,
            showBcc: false,
            error: '',
        });

        this._autosaveTimer = null;
        onMounted(() => {
            this._autosaveTimer = setInterval(() => this.autosave(), 30000);
        });
        onWillUnmount(() => {
            if (this._autosaveTimer) {
                clearInterval(this._autosaveTimer);
            }
        });
    }

    onToChange(ev) {
        this.state.to = ev.target.value;
    }

    onCcChange(ev) {
        this.state.cc = ev.target.value;
    }

    onBccChange(ev) {
        this.state.bcc = ev.target.value;
    }

    onSubjectChange(ev) {
        this.state.subject = ev.target.value;
    }

    onBodyChange(ev) {
        this.state.body = ev.target.value;
    }

    toggleBcc() {
        this.state.showBcc = !this.state.showBcc;
    }

    async autosave() {
        if (!this.props.draftId) return;
        try {
            await rpc('/cf/mail/v3/draft/' + this.props.draftId + '/autosave', {
                to_emails: this.state.to,
                cc_emails: this.state.cc,
                bcc_emails: this.state.bcc,
                subject: this.state.subject,
                body_html: this.state.body,
            });
        } catch (e) {
            console.warn('[mail v3] autosave error:', e);
        }
    }

    async send() {
        if (!this.state.to.trim()) {
            this.state.error = 'Inserisci almeno un destinatario';
            return;
        }
        this.state.sending = true;
        this.state.error = '';

        // Save latest values first
        await this.autosave();

        try {
            const res = await rpc('/cf/mail/v3/draft/' + this.props.draftId + '/send');
            if (res.success) {
                if (this.props.onSent) {
                    this.props.onSent();
                }
            } else {
                this.state.error = res.error || 'Errore invio';
            }
        } catch (e) {
            this.state.error = 'Errore: ' + (e.message || e);
        }
        this.state.sending = false;
    }

    discard() {
        if (this.props.onClose) {
            this.props.onClose();
        }
    }
}
