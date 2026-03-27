/** @odoo-module **/
import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

const AVATAR_COLORS = [
    "linear-gradient(135deg,#5A6E3A,#3d4d27)",
    "linear-gradient(135deg,#1a73e8,#1557b0)",
    "linear-gradient(135deg,#e65c00,#bf360c)",
    "linear-gradient(135deg,#9c27b0,#6a1b9a)",
    "linear-gradient(135deg,#00897b,#004d40)",
    "linear-gradient(135deg,#d32f2f,#b71c1c)",
    "linear-gradient(135deg,#1565c0,#003c8f)",
    "linear-gradient(135deg,#558b2f,#1b5e20)",
];

class CfMailClient extends Component {
    static template = "cf_mail_client.App";
    static components = {};

    setup() {
        this.notification = useService("notification");
        this.emailContent = useRef("emailContent");
        this.composerBody = useRef("composerBody");
        this._searchTimer = null;

        this.state = useState({
            accounts: [],
            messages: [],
            selectedMsg: null,
            msgDetail: {},
            loading: false,
            loadingDetail: false,
            selectedAccount: null,
            folder: "INBOX",
            search: "",
            selectedIds: [],
            totalUnread: 0,
            showComposer: false,
            composerMode: "reply",
            composerTo: "",
            composerSubject: "",
            users: [],
            leads: [],
            allTags: [],
            showTagDropdown: false,
            showSnoozeMenu: false,
            showBulkTagMenu: false,
            newTagName: "",
            newTagColor: "#5A6E3A",
            threadExpanded: false,
        });

        onMounted(() => { this.init(); });
    }

    async _rpc(model, method, kwargs = {}) {
        return await rpc("/web/dataset/call_kw", { model, method, args: [], kwargs });
    }

    async init() {
        await Promise.all([this.loadAccounts(), this.loadUsers(), this.loadLeads(), this.loadTags()]);
        await this.loadMessages();
    }

    async loadAccounts() {
        try {
            const accounts = await this._rpc("cf.mail.account", "get_accounts");
            this.state.accounts = accounts || [];
            if (accounts && accounts.length > 0 && !this.state.selectedAccount)
                this.state.selectedAccount = accounts[0].id;
            this.state.totalUnread = (accounts || []).reduce((s, a) => s + (a.unread || 0), 0);
        } catch (e) { console.error("loadAccounts error:", e); }
    }

    async loadMessages() {
        if (!this.state.selectedAccount) return;
        this.state.loading = true;
        try {
            const msgs = await this._rpc("cf.mail.message", "get_messages", {
                account_id: this.state.selectedAccount,
                folder: this.state.folder,
                limit: 50,
                offset: 0,
                search: this.state.search,
            });
            this.state.messages = msgs || [];
            this.state.selectedIds = [];
        } catch (e) { console.error("loadMessages error:", e); }
        finally { this.state.loading = false; }
    }

    async loadUsers() {
        try { this.state.users = await this._rpc("cf.mail.message", "get_users_list") || []; } catch (e) {}
    }

    async loadLeads() {
        try { this.state.leads = await this._rpc("cf.mail.message", "get_leads_list") || []; } catch (e) {}
    }

    async loadTags() {
        try { this.state.allTags = await this._rpc("cf.mail.message", "get_tags_list") || []; } catch (e) {}
    }

    async selectMsg(msg, ev) {
        if (ev && ev.target.type === "checkbox") return;
        this.state.selectedMsg = msg;
        this.state.msgDetail = {};
        this.state.loadingDetail = true;
        this.state.showComposer = false;
        this.state.showTagDropdown = false;
        this.state.showSnoozeMenu = false;
        this.state.threadExpanded = false;
        try {
            const detail = await this._rpc("cf.mail.message", "get_message_detail", { message_id: msg.id });
            this.state.msgDetail = detail || {};
            const idx = this.state.messages.findIndex(m => m.id === msg.id);
            if (idx !== -1) this.state.messages[idx].is_read = true;
            await this._renderEmailBody(detail.body_html || detail.body_text || "");
        } catch (e) { console.error("loadDetail error:", e); }
        finally { this.state.loadingDetail = false; }
    }

    async _renderEmailBody(html) {
        const el = this.emailContent.el;
        if (!el) return;
        el.innerHTML = "";
        const iframe = document.createElement("iframe");
        iframe.style.cssText = "width:100%;border:none;flex:1;min-height:200px;";
        iframe.setAttribute("sandbox", "allow-same-origin");
        el.appendChild(iframe);
        iframe.onload = () => {
            try { iframe.style.height = iframe.contentDocument.body.scrollHeight + 40 + "px"; } catch (e) {}
        };
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        doc.open();
        doc.write(`<style>body{font-family:'Plus Jakarta Sans',sans-serif;font-size:14px;line-height:1.6;color:#202124;padding:16px;margin:0}a{color:#5A6E3A}img{max-width:100%}</style>${html}`);
        doc.close();
    }

    async selectAccount(accountId) {
        this.state.selectedAccount = accountId;
        this.state.selectedMsg = null;
        this.state.msgDetail = {};
        await this.loadMessages();
    }

    async setFolder(folder) {
        this.state.folder = folder;
        this.state.selectedMsg = null;
        this.state.msgDetail = {};
        await this.loadMessages();
    }

    onSearch(ev) {
        this.state.search = ev.target.value;
        if (this._searchTimer) clearTimeout(this._searchTimer);
        this._searchTimer = setTimeout(() => this.loadMessages(), 400);
    }

    toggleSelect(id, ev) {
        ev.stopPropagation();
        const idx = this.state.selectedIds.indexOf(id);
        if (idx === -1) this.state.selectedIds = [...this.state.selectedIds, id];
        else this.state.selectedIds = this.state.selectedIds.filter(i => i !== id);
    }

    toggleSelectAll(ev) {
        this.state.selectedIds = ev.target.checked ? this.state.messages.map(m => m.id) : [];
    }

    async bulkAction(action, extraKwargs = {}) {
        if (!this.state.selectedIds.length) return;
        try {
            await this._rpc("cf.mail.message", "do_bulk_action", { ids: this.state.selectedIds, action, ...extraKwargs });
            this.showToast(action === "delete" ? "Email eliminate" : "Azione completata");
            this.state.showBulkTagMenu = false;
            await this.loadMessages();
        } catch (e) { console.error("bulkAction error:", e); }
    }

    async quickStar(msgId, ev) {
        if (ev) ev.stopPropagation();
        try {
            const starred = await this._rpc("cf.mail.message", "do_toggle_star", { message_id: msgId });
            const idx = this.state.messages.findIndex(m => m.id === msgId);
            if (idx !== -1) this.state.messages[idx].is_starred = starred;
            if (this.state.selectedMsg && this.state.selectedMsg.id === msgId)
                this.state.selectedMsg.is_starred = starred;
        } catch (e) {}
    }

    async quickArchive(msgId, ev) {
        if (ev) ev.stopPropagation();
        try {
            await this._rpc("cf.mail.message", "do_bulk_action", { ids: [msgId], action: "archive" });
            this.state.messages = this.state.messages.filter(m => m.id !== msgId);
            if (this.state.selectedMsg && this.state.selectedMsg.id === msgId) {
                this.state.selectedMsg = null;
                this.state.msgDetail = {};
            }
            this.showToast("Email archiviata");
        } catch (e) {}
    }

    async addTag(tagId) {
        if (!this.state.selectedMsg) return;
        try {
            const tags = await this._rpc("cf.mail.message", "do_add_tag", { message_id: this.state.selectedMsg.id, tag_id: tagId });
            this.state.msgDetail.tags = tags;
            const idx = this.state.messages.findIndex(m => m.id === this.state.selectedMsg.id);
            if (idx !== -1) this.state.messages[idx].tags = tags;
            this.state.showTagDropdown = false;
        } catch (e) {}
    }

    async removeTag(tagId) {
        if (!this.state.selectedMsg) return;
        try {
            const tags = await this._rpc("cf.mail.message", "do_remove_tag", { message_id: this.state.selectedMsg.id, tag_id: tagId });
            this.state.msgDetail.tags = tags;
            const idx = this.state.messages.findIndex(m => m.id === this.state.selectedMsg.id);
            if (idx !== -1) this.state.messages[idx].tags = tags;
        } catch (e) {}
    }

    async createNewTag() {
        if (!this.state.newTagName.trim()) return;
        try {
            const tag = await this._rpc("cf.mail.message", "create_tag", { name: this.state.newTagName.trim(), color: this.state.newTagColor });
            this.state.allTags = [...this.state.allTags, tag];
            this.state.newTagName = "";
            if (this.state.selectedMsg) await this.addTag(tag.id);
        } catch (e) {}
    }

    async snooze(minutes) {
        if (!this.state.selectedMsg) return;
        const until = new Date(Date.now() + minutes * 60000).toISOString();
        try {
            await this._rpc("cf.mail.message", "do_snooze", { message_id: this.state.selectedMsg.id, until });
            this.state.showSnoozeMenu = false;
            this.showToast("Email posticipata");
            this.state.messages = this.state.messages.filter(m => m.id !== this.state.selectedMsg.id);
            this.state.selectedMsg = null;
            this.state.msgDetail = {};
        } catch (e) {}
    }

    async createLead() {
        if (!this.state.selectedMsg) return;
        try {
            const res = await this._rpc("cf.mail.message", "create_lead_from_email", { message_id: this.state.selectedMsg.id });
            if (res && res.success) {
                this.showToast("Trattativa creata: " + res.lead_name);
                this.state.msgDetail.lead_id = res.lead_id;
                this.state.msgDetail.lead_name = res.lead_name;
                await this.loadLeads();
            } else {
                this.showToast("Errore: " + (res.error || "sconosciuto"));
            }
        } catch (e) { console.error("createLead error:", e); }
    }

    async onAssignChange(ev) {
        const userId = ev.target.value;
        if (!this.state.selectedMsg) return;
        try {
            const name = await this._rpc("cf.mail.message", "do_assign", { message_id: this.state.selectedMsg.id, user_id: userId || false });
            this.state.msgDetail.assigned_user_name = name || "";
            this.state.msgDetail.assigned_user_id = userId ? parseInt(userId) : false;
            this.showToast(name ? "Assegnata a " + name : "Assegnazione rimossa");
        } catch (e) {}
    }

    async onLeadLinkChange(ev) {
        const leadId = ev.target.value;
        if (!this.state.selectedMsg) return;
        try {
            await this._rpc("cf.mail.message", "do_link_lead", { message_id: this.state.selectedMsg.id, lead_id: leadId || false });
            this.state.msgDetail.lead_id = leadId ? parseInt(leadId) : false;
            this.showToast("Trattativa collegata");
        } catch (e) {}
    }

    openReply() {
        this.state.showComposer = true;
        this.state.composerMode = "reply";
        this.state.composerTo = this.state.msgDetail.from_address || "";
        this.state.composerSubject = "Re: " + (this.state.msgDetail.subject || "");
    }

    openForward() {
        this.state.showComposer = true;
        this.state.composerMode = "forward";
        this.state.composerTo = "";
        this.state.composerSubject = "Fwd: " + (this.state.msgDetail.subject || "");
    }

    openComposer() {
        this.state.showComposer = true;
        this.state.composerMode = "new";
        this.state.composerTo = "";
        this.state.composerSubject = "";
    }

    closeComposer() { this.state.showComposer = false; }

    async sendEmail() {
        const bodyEl = this.composerBody.el;
        const body = bodyEl ? bodyEl.innerHTML : "";
        if (!this.state.composerTo || !body) { this.showToast("Compilare destinatario e messaggio"); return; }
        try {
            const res = await this._rpc("cf.mail.message", "send_reply", {
                message_id: this.state.selectedMsg ? this.state.selectedMsg.id : false,
                to_address: this.state.composerTo,
                subject: this.state.composerSubject,
                body,
                account_id: this.state.selectedAccount,
            });
            if (res && res.success) { this.showToast("Email inviata!"); this.closeComposer(); }
            else this.showToast("Errore invio: " + (res.error || "sconosciuto"));
        } catch (e) { this.showToast("Errore invio email"); }
    }

    get listHeaderLabel() {
        const total = this.state.messages.length;
        const map = { INBOX: "Inbox", Starred: "Preferiti", Sent: "Inviati", Archived: "Archivio", Assigned: "Assegnate a me" };
        return (map[this.state.folder] || this.state.folder) + " — " + total;
    }

    avatarColor(name) {
        if (!name) return AVATAR_COLORS[0];
        let h = 0;
        for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffffffff;
        return AVATAR_COLORS[Math.abs(h) % AVATAR_COLORS.length];
    }

    avatarInitial(name) {
        if (!name) return "?";
        const parts = name.trim().split(/\s+/);
        if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
        return name[0].toUpperCase();
    }

    showToast(msg) {
        const el = document.createElement("div");
        el.className = "cf-mail-toast";
        el.textContent = msg;
        document.body.appendChild(el);
        setTimeout(() => el.remove(), 3000);
    }
}

registry.category("actions").add("cf_mail_client", CfMailClient);
