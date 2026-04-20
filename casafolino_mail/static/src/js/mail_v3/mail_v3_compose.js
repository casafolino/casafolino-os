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
            attachments: [],
            dragOver: false,
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

    onToChange(ev) { this.state.to = ev.target.value; }
    onCcChange(ev) { this.state.cc = ev.target.value; }
    onBccChange(ev) { this.state.bcc = ev.target.value; }
    onSubjectChange(ev) { this.state.subject = ev.target.value; }
    onBodyChange(ev) { this.state.body = ev.target.value; }
    toggleBcc() { this.state.showBcc = !this.state.showBcc; }

    // ── Drag & Drop ─────────────────────────────────────────

    onDragOver(ev) {
        ev.preventDefault();
        this.state.dragOver = true;
    }

    onDragLeave(ev) {
        ev.preventDefault();
        this.state.dragOver = false;
    }

    async onDrop(ev) {
        ev.preventDefault();
        this.state.dragOver = false;
        const files = ev.dataTransfer?.files;
        if (!files || files.length === 0) return;
        for (const file of files) {
            await this._uploadFile(file);
        }
    }

    async onFileSelect(ev) {
        const files = ev.target.files;
        if (!files || files.length === 0) return;
        for (const file of files) {
            await this._uploadFile(file);
        }
        ev.target.value = '';
    }

    async _uploadFile(file) {
        try {
            const formData = new FormData();
            formData.append('ufile', file);
            formData.append('csrf_token', odoo.csrf_token);

            const res = await fetch('/web/binary/upload_attachment', {
                method: 'POST',
                body: formData,
            });
            const data = await res.json();
            if (data && data[0] && data[0].id) {
                this.state.attachments.push({
                    id: data[0].id,
                    name: file.name,
                    size: file.size,
                });
            }
        } catch (e) {
            console.error('[mail v3] upload error:', e);
        }
    }

    removeAttachment(index) {
        this.state.attachments.splice(index, 1);
    }

    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    // ── Autosave & Send ─────────────────────────────────────

    async autosave() {
        if (!this.props.draftId) return;
        try {
            await rpc('/cf/mail/v3/draft/' + this.props.draftId + '/autosave', {
                to_emails: this.state.to,
                cc_emails: this.state.cc,
                bcc_emails: this.state.bcc,
                subject: this.state.subject,
                body_html: this.state.body,
                attachment_ids: this.state.attachments.map(a => a.id),
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
        await this.autosave();

        try {
            const res = await rpc('/cf/mail/v3/draft/' + this.props.draftId + '/send');
            if (res.success) {
                if (this.props.onSent) this.props.onSent();
            } else {
                this.state.error = res.error || 'Errore invio';
            }
        } catch (e) {
            this.state.error = 'Errore: ' + (e.message || e);
        }
        this.state.sending = false;
    }

    discard() {
        if (this.props.onClose) this.props.onClose();
    }
}
