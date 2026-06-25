/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class WorkspaceMail extends Component {
    static template = "casafolino_workspace.WorkspaceMail";
    static props = ["*"];

    setup() {
        this.state = useState({
            loading: true, data: null, error: null,
            view: "inbox", filter: "tutte",
            mails: [], mailsLoading: false,
            threads: null, triage: null,
            selectedMail: null, detailData: null,
            actionMsg: null,
        });
        onWillStart(async () => { await this._loadAll(); });
    }

    async _loadAll() {
        try {
            const [data, inbox] = await Promise.all([
                rpc("/workspace/mail/data", {}),
                rpc("/workspace/mail/inbox", { filter_key: "tutte" }),
            ]);
            this.state.data = data;
            this.state.mails = inbox.mails || [];
            this.state.loading = false;
        } catch (e) {
            this.state.error = e.message || "Errore";
            this.state.loading = false;
        }
    }

    async onFilterChange(fk) {
        this.state.filter = fk;
        this.state.mailsLoading = true;
        try {
            const res = await rpc("/workspace/mail/inbox", { filter_key: fk });
            this.state.mails = res.mails || [];
        } catch (e) { this.state.mails = []; }
        this.state.mailsLoading = false;
    }

    async onViewChange(v) {
        this.state.view = v;
        if (v === "threads" && !this.state.threads) {
            try {
                const res = await rpc("/workspace/mail/threads", {});
                this.state.threads = res.threads || [];
            } catch (e) { this.state.threads = []; }
        }
        if (v === "triage" && !this.state.triage) {
            try {
                const res = await rpc("/workspace/mail/triage", {});
                this.state.triage = res.mails || [];
            } catch (e) { this.state.triage = []; }
        }
    }

    async onSelectMail(mail) {
        this.state.selectedMail = mail;
        this.state.actionMsg = null;
        try {
            const res = await rpc("/workspace/mail/detail", { mail_id: mail.id });
            this.state.detailData = res;
        } catch (e) { this.state.detailData = null; }
    }

    onCloseDetail() {
        this.state.selectedMail = null;
        this.state.detailData = null;
        this.state.actionMsg = null;
    }

    async onAction(mailId, action) {
        this.state.actionMsg = null;
        try {
            const res = await rpc("/workspace/mail/action", { mail_id: mailId, action: action });
            this.state.actionMsg = res.message || (res.ok ? "OK" : "Errore");
            if (res.ok && action === "archive") {
                this.state.mails = this.state.mails.filter(m => m.id !== mailId);
                if (this.state.selectedMail && this.state.selectedMail.id === mailId) {
                    this.state.selectedMail = null;
                    this.state.detailData = null;
                }
            }
        } catch (e) { this.state.actionMsg = "Errore: " + (e.message || e); }
    }

    onGoHome() { this.props.onGoHome(); }

    getFilterKey(label) {
        return {"Tutte":"tutte","Importanti":"importanti","Buyer":"buyer","Decisioni":"decisioni","Archiviate":"archiviate"}[label] || "tutte";
    }

    getRelativeTime(isoDate) {
        if (!isoDate) return "";
        const now = luxon.DateTime.now();
        const dt = luxon.DateTime.fromISO(isoDate);
        const diff = now.diff(dt, ["days", "hours", "minutes"]);
        if (diff.days >= 1) { const d = Math.floor(diff.days); return d === 1 ? "ieri" : d + " gg fa"; }
        if (diff.hours >= 1) return Math.floor(diff.hours) + " h fa";
        return Math.max(1, Math.floor(diff.minutes)) + " min fa";
    }
}
