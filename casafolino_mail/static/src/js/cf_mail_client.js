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

const RATING_STARS = { '1': '★', '2': '★★', '3': '★★★', '4': '★★★★', '5': '★★★★★' };

class CfMailClient extends Component {
    static template = "cf_mail_client.App";
    static components = {};

    setup() {
        this.notification = useService("notification");
        this.emailContent = useRef("emailContent");
        this.composerBody = useRef("composerBody");
        this._searchTimer = null;

        this.state = useState({
            accounts: [], messages: [], selectedMsg: null, msgDetail: {},
            loading: false, loadingDetail: false, selectedAccount: null,
            folder: "INBOX", search: "", selectedIds: [], totalUnread: 0,
            quickFilter: "all",
            showComposer: false, composerMode: "reply", composerTo: "", composerSubject: "",
            composerFrom: null, composerCc: "", composerBcc: "",
            composerShowCc: false, composerShowBcc: false,
            composerMinimized: false, composerMaximized: false,
            users: [], leads: [], allTags: [], contactTags: [],
            showTagDropdown: false, showSnoozeMenu: false, showBulkTagMenu: false,
            newTagName: "", newTagColor: "#5A6E3A", threadExpanded: false,
            groupBy: "date",
            showLeadModal: false, crmPipelines: [], crmPartners: [], crmSources: [],
            leadForm: { name: "", partner_id: "", partner_name: "", contact_name: "", function: "", email_from: "", phone: "", stage_id: "", expected_revenue: "", description: "", cf_market: "", cf_channel: "", cf_language: "", source: "" },
            leadPartnerSearch: "", leadPartnerResults: [],
            showAccountModal: false,
            accountForm: { id: null, name: "", email: "", signature: "", imap_host: "imap.gmail.com", imap_port: 993, imap_ssl: true, imap_password: "", imap_enabled: false, imap_status: "", smtp_host: "smtp.gmail.com", smtp_port: 587, smtp_tls: true, color: "#5A6E3A", ooo_enabled: false, ooo_subject: "Sono fuori ufficio", ooo_message: "", ooo_start: "", ooo_end: "" },
            showContactModal: false,
            contactDetail: {},
            showEnrichment: false, enrichPartnerSearch: "", enrichPartnerResults: [],
            enrichNote: "", enrichSaved: false,
            showSearchPanel: false,
            searchForm: { query: "", date_from: "", date_to: "", tag_id: "", has_attachments: false },
            isAdmin: false,
            activeView: "mail",
            contacts: [], contactSearch: "", contactTagFilter: "",
            show007Panel: false, data007: {}, loading007: false,
            showAIPanel: false, aiLoading: false, aiResult: "", composerAILoading: false,
        });

        onMounted(() => { this.init(); });
    }

    async _rpc(model, method, kwargs = {}) {
        return await rpc("/web/dataset/call_kw", { model, method, args: [], kwargs });
    }

    async init() {
        await Promise.all([this.loadAccounts(), this.loadUsers(), this.loadLeads(), this.loadTags(), this.loadContactTags(), this.checkAdmin()]);
        await this.loadMessages();
    }

    async checkAdmin() {
        try {
            const result = await this._rpc("cf.mail.account", "is_admin");
            this.state.isAdmin = result || false;
        } catch (e) { this.state.isAdmin = false; }
    }

    async loadAccounts() {
        try {
            const accounts = await this._rpc("cf.mail.account", "get_accounts");
            this.state.accounts = accounts || [];
            if (accounts && accounts.length > 0 && !this.state.selectedAccount)
                this.state.selectedAccount = accounts[0].id;
            this.state.totalUnread = (accounts || []).reduce((s, a) => s + (a.unread || 0), 0);
        } catch (e) { console.error(e); }
    }

    async loadMessages() {
        if (!this.state.selectedAccount) return;
        this.state.loading = true;
        try {
            const msgs = await this._rpc("cf.mail.message", "get_messages", {
                account_id: this.state.selectedAccount,
                folder: this.state.folder,
                limit: 100, offset: 0, search: this.state.search,
            });
            this.state.messages = msgs || [];
            this.state.selectedIds = [];
        } catch (e) { console.error(e); }
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
    async loadContactTags() {
        try { this.state.contactTags = await this._rpc("cf.contact.tag", "get_all_tags") || []; } catch (e) {}
    }
    async loadCrmData() {
        try {
            const data = await this._rpc("cf.mail.message", "get_crm_data");
            this.state.crmPipelines = data.pipelines || [];
            this.state.crmPartners = data.partners || [];
            this.state.crmSources = data.sources || [];
        } catch (e) {}
    }

    async loadContacts() {
        try {
            const contacts = await this._rpc("res.partner", "search_contacts", {
                query: this.state.contactSearch,
                tag_ids: this.state.contactTagFilter ? [this.state.contactTagFilter] : [],
            });
            this.state.contacts = contacts || [];
        } catch (e) { console.error(e); }
    }

    get filteredMessages() {
        const msgs = this.state.messages;
        const f = this.state.quickFilter;
        if (f === 'unread') return msgs.filter(m => !m.is_read);
        if (f === 'starred') return msgs.filter(m => m.is_starred);
        if (f === 'inbox') return msgs.filter(m => m.direction !== 'out');
        if (f === 'sent') return msgs.filter(m => m.direction === 'out');
        return msgs;
    }

    setQuickFilter(filter) {
        this.state.quickFilter = filter;
    }

    // Navigation methods (replace sidebar block {} arrows)
    navInbox()    { this.state.activeView = 'mail'; this.setFolder('INBOX'); }
    navStarred()  { this.state.activeView = 'mail'; this.setFolder('Starred'); }
    navAssigned() { this.state.activeView = 'mail'; this.setFolder('Assigned'); }
    navSent()     { this.state.activeView = 'mail'; this.setFolder('Sent'); }
    navArchived() { this.state.activeView = 'mail'; this.setFolder('Archived'); }
    navContacts() { this.state.activeView = 'contacts'; this.loadContacts(); }
    navTag(tagId) { this.state.activeView = 'mail'; this.setFolder('TAG_' + tagId); }

    // Quick filter dedicated methods
    onQfAll()      { this.setQuickFilter('all'); }
    onQfUnread()   { this.setQuickFilter('unread'); }
    onQfStarred()  { this.setQuickFilter('starred'); }
    onQfIncoming() { this.setQuickFilter('inbox'); }
    onQfOutgoing() { this.setQuickFilter('sent'); }

    // Groupby dedicated methods
    setGroupByDate()     { this.state.groupBy = 'date'; }
    setGroupBySender()   { this.state.groupBy = 'sender'; }
    setGroupByLead()     { this.state.groupBy = 'lead'; }
    setGroupByPipeline() { this.state.groupBy = 'pipeline'; }

    // UI state toggle methods
    toggleTagDropdown()    { this.state.showTagDropdown = !this.state.showTagDropdown; this.state.showSnoozeMenu = false; }
    toggleSnoozeMenu()     { this.state.showSnoozeMenu = !this.state.showSnoozeMenu; this.state.showTagDropdown = false; }
    toggleThreadExpanded() { this.state.threadExpanded = !this.state.threadExpanded; }
    toggleSearchPanel()    { this.state.showSearchPanel = !this.state.showSearchPanel; }
    toggleBulkTagMenu()    { this.state.showBulkTagMenu = !this.state.showBulkTagMenu; }
    noop() {}

    // Search panel t-on-change handlers (no arrows allowed in t-on-change)
    onSearchTagChange(ev)         { this.state.searchForm.tag_id = ev.target.value; }
    onSearchAttachmentsChange(ev) { this.state.searchForm.has_attachments = ev.target.checked; }

    // Contacts handlers
    onContactSearchInput(ev)     { this.state.contactSearch = ev.target.value; this.loadContacts(); }
    onContactTagFilterChange(ev) { this.state.contactTagFilter = ev.target.value; this.loadContacts(); }

    // Item checkbox t-on-change via data attribute (no inline arrow with msg.id)
    onItemCheckChange(ev) {
        const msgId = parseInt(ev.currentTarget.dataset.msgId);
        if (msgId) this.toggleSelect(msgId, ev);
    }

    // ── Generic form handlers (data-form + data-field pattern) ──
    onFormInput(ev) {
        const { form, field } = ev.target.dataset;
        if (form && field) this.state[form][field] = ev.target.value;
    }
    onFormChange(ev) {
        const { form, field } = ev.target.dataset;
        const isChecked = ev.target.dataset.type === 'checked';
        if (form && field) this.state[form][field] = isChecked ? ev.target.checked : ev.target.value;
    }
    onStateInput(ev) {
        const key = ev.target.dataset.stateKey;
        if (key) this.state[key] = ev.target.value;
    }

    // ── Data-driven click handlers ──
    onNavTag(ev) { this.navTag(parseInt(ev.currentTarget.dataset.tagId)); }
    onSelectAccount(ev) { this.selectAccount(parseInt(ev.currentTarget.dataset.accountId)); }
    onOpenEditAccount(ev) { this.openEditAccount(parseInt(ev.currentTarget.dataset.accountId)); }
    onSelectMsg(ev) {
        const msgId = parseInt(ev.currentTarget.dataset.msgId);
        const msg = this.state.messages.find(m => m.id === msgId);
        if (msg) this.selectMsg(msg, ev);
    }
    onQuickStar(ev) { this.quickStar(parseInt(ev.currentTarget.dataset.msgId), ev); }
    onQuickArchive(ev) { this.quickArchive(parseInt(ev.currentTarget.dataset.msgId), ev); }
    onDetailStar() { if (this.state.selectedMsg) this.quickStar(this.state.selectedMsg.id, null); }
    onDetailArchive() { if (this.state.selectedMsg) this.quickArchive(this.state.selectedMsg.id, null); }
    async onKeepSender() {
        if (!this.state.selectedMsg) return;
        const res = await rpc("/web/dataset/call_kw", {
            model: "cf.mail.message", method: "rpc_keep_sender",
            args: [[], this.state.selectedMsg.id], kwargs: { message_id: this.state.selectedMsg.id },
        });
        if (res && res.success) {
            this.state.msgDetail.sender_action = "keep";
            const msg = this.state.messages.find(m => m.id === this.state.selectedMsg.id);
            if (msg) msg.sender_action = "keep";
        }
    }
    async onExcludeSender() {
        if (!this.state.selectedMsg) return;
        const from = this.state.msgDetail.from_name || this.state.msgDetail.from_address || "";
        if (!confirm("Escludi mittente " + from + "?\nTutte le sue email verranno eliminate.")) return;
        const res = await rpc("/web/dataset/call_kw", {
            model: "cf.mail.message", method: "rpc_exclude_sender",
            args: [[], this.state.selectedMsg.id], kwargs: { message_id: this.state.selectedMsg.id },
        });
        if (res && res.success) {
            this.state.selectedMsg = null;
            this.state.msgDetail = {};
            await this.loadMessages();
        }
    }
    toggleEnrichment() { this.state.showEnrichment = !this.state.showEnrichment; }
    async onEnrichPartnerSearch(ev) {
        const q = ev.target.value;
        this.state.enrichPartnerSearch = q;
        if (q.length < 2) { this.state.enrichPartnerResults = []; return; }
        const res = await rpc("/web/dataset/call_kw", {
            model: "cf.mail.message", method: "rpc_search_partners",
            args: [[], q], kwargs: { query: q },
        });
        this.state.enrichPartnerResults = res || [];
    }
    onEnrichSelectPartner(ev) {
        const pid = parseInt(ev.currentTarget.dataset.partnerId);
        const p = this.state.enrichPartnerResults.find(x => x.id === pid);
        if (p) {
            this.state.msgDetail.partner_id = p.id;
            this.state.msgDetail.partner_name = p.name;
        }
        this.state.enrichPartnerResults = [];
        this.state.enrichPartnerSearch = "";
    }
    async onSaveEnrichment() {
        if (!this.state.selectedMsg) return;
        this.state.enrichSaved = false;
        const d = this.state.msgDetail;
        await rpc("/web/dataset/call_kw", {
            model: "cf.mail.message", method: "rpc_save_enrichment",
            args: [[]], kwargs: {
                message_id: this.state.selectedMsg.id,
                partner_id: d.partner_id || false,
                tag_ids: (d.tags || []).map(t => t.id),
                assigned_user_id: d.assigned_user_id || false,
                lead_id: d.lead_id || false,
                note: this.state.enrichNote || "",
            },
        });
        this.state.enrichSaved = true;
    }
    onAddTag(ev) { this.addTag(parseInt(ev.currentTarget.dataset.tagId)); }
    onRemoveTag(ev) { this.removeTag(parseInt(ev.currentTarget.dataset.tagId)); }
    onNewTagNameInput(ev) { this.state.newTagName = ev.target.value; }
    onNewTagColorInput(ev) { this.state.newTagColor = ev.target.value; }
    onSearchQueryInput(ev) { this.state.searchForm.query = ev.target.value; }
    onSearchDateFromInput(ev) { this.state.searchForm.date_from = ev.target.value; }
    onSearchDateToInput(ev) { this.state.searchForm.date_to = ev.target.value; }

    // Bulk actions
    onBulkRead() { this.bulkAction('read'); }
    onBulkUnread() { this.bulkAction('unread'); }
    onBulkStar() { this.bulkAction('star'); }
    onBulkArchive() { this.bulkAction('archive'); }
    onBulkDelete() { this.bulkAction('delete'); }
    onBulkAddTag(ev) { this.bulkAction('add_tag', { tag_id: parseInt(ev.currentTarget.dataset.tagId) }); }

    // Snooze, contact, format
    onSnooze(ev) { this.snooze(parseInt(ev.currentTarget.dataset.minutes)); }
    onOpenContactDetail(ev) { this.openContactDetail(parseInt(ev.currentTarget.dataset.contactId)); }
    onRemoveContactTag(ev) { this.removeContactTag(parseInt(ev.currentTarget.dataset.tagId)); }
    onExecFormat(ev) { this.execFormat(ev.currentTarget.dataset.command); }
    onComposerHeaderClick() { if (this.state.composerMinimized) this.toggleComposerMinimized(); }

    get groupedMessages() {
        const msgs = this.filteredMessages;
        const groupBy = this.state.groupBy;

        if (groupBy === "date") {
            const now = new Date();
            const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            const days = ["Domenica","Lunedì","Martedì","Mercoledì","Giovedì","Venerdì","Sabato"];
            const months = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"];

            const getLabel = (dateStr) => {
                if (!dateStr) return "Senza data";
                const parts = dateStr.split(/[\/\s:]/);
                const d = parts.length >= 3 && parts[2].length === 4
                    ? new Date(parseInt(parts[2]), parseInt(parts[1])-1, parseInt(parts[0]))
                    : new Date(dateStr.replace(' ', 'T'));
                if (isNaN(d.getTime())) return "Senza data";
                const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
                const diffDays = Math.round((today - day) / 86400000);
                if (diffDays === 0) return "Oggi";
                if (diffDays === 1) return "Ieri";
                if (diffDays < 7) return days[day.getDay()];
                if (diffDays < 14) return "Settimana scorsa";
                return months[d.getMonth()] + " " + d.getFullYear();
            };

            const order = [];
            const map = {};
            for (const m of msgs) {
                const label = getLabel(m.date);
                if (!map[label]) { map[label] = []; order.push(label); }
                map[label].push(m);
            }
            return order.map(label => ({ label, items: map[label] }));
        }

        if (groupBy === "sender") {
            const map = {};
            const order = [];
            for (const m of msgs) {
                const key = m.from_name || m.from_address || "Sconosciuto";
                if (!map[key]) { map[key] = []; order.push(key); }
                map[key].push(m);
            }
            return order.sort((a,b) => map[b].length - map[a].length)
                .map(label => ({ label, items: map[label], count: map[label].length }));
        }

        if (groupBy === "lead") {
            const map = {};
            const order = [];
            for (const m of msgs) {
                const key = m.lead_name || "Senza trattativa";
                if (!map[key]) { map[key] = []; order.push(key); }
                map[key].push(m);
            }
            return order.sort((a,b) => {
                if (a === "Senza trattativa") return 1;
                if (b === "Senza trattativa") return -1;
                return a.localeCompare(b);
            }).map(label => ({ label, items: map[label] }));
        }

        if (groupBy === "pipeline") {
            const map = {};
            const order = [];
            for (const m of msgs) {
                const key = m.lead_stage || "Senza pipeline";
                if (!map[key]) { map[key] = []; order.push(key); }
                map[key].push(m);
            }
            return order.map(label => ({ label, items: map[label] }));
        }

        return [{ label: null, items: msgs }];
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
        this.state.showLeadModal = false;
        try {
            const detail = await this._rpc("cf.mail.message", "get_message_detail", { message_id: msg.id });
            this.state.msgDetail = detail || {};
            this.state.enrichNote = detail.note || "";
            this.state.enrichPartnerSearch = "";
            this.state.enrichPartnerResults = [];
            this.state.enrichSaved = false;
            const idx = this.state.messages.findIndex(m => m.id === msg.id);
            if (idx !== -1) this.state.messages[idx].is_read = true;
            await this._renderEmailBody(detail.body_html || detail.body_text || "");
            if (detail.partner_id) {
                this.load007Data(detail.partner_id);
            } else {
                this.state.data007 = {};
            }
        } catch (e) { console.error(e); }
        finally { this.state.loadingDetail = false; }
    }

    async _renderEmailBody(html) {
        const el = this.emailContent.el;
        if (!el) return;
        el.innerHTML = "";
        const iframe = document.createElement("iframe");
        iframe.style.cssText = "width:100%;border:none;min-height:200px;pointer-events:none;";
        iframe.setAttribute("sandbox", "allow-same-origin");
        el.appendChild(iframe);
        iframe.onload = () => {
            try { iframe.style.height = iframe.contentDocument.body.scrollHeight + 40 + "px"; } catch (e) {}
        };
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        doc.open();
        doc.write(`<style>body{font-family:'Plus Jakarta Sans',sans-serif;font-size:14px;line-height:1.6;color:#202124;padding:16px;margin:0}a{color:#5A6E3A}img{max-width:100%}ul,ol{margin:8px 0 8px 20px}</style>${html}`);
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

    async runAdvancedSearch() {
        this.state.loading = true;
        try {
            const msgs = await this._rpc("cf.mail.message", "advanced_search", {
                ...this.state.searchForm,
                account_id: this.state.selectedAccount,
                folder: this.state.folder,
            });
            this.state.messages = msgs || [];
            this.state.showSearchPanel = false;
        } catch (e) { console.error(e); }
        finally { this.state.loading = false; }
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
        } catch (e) { console.error(e); }
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

    async openContactDetail(partnerId) {
        if (!partnerId) return;
        try {
            const data = await this._rpc("res.partner", "get_contact_detail", { partner_id: partnerId });
            this.state.contactDetail = data || {};
            this.state.showContactModal = true;
        } catch (e) { console.error(e); }
    }


    openNewContact() {
        this.state.contactDetail = { name: "", email: "", phone: "", tags: [] };
        this.state.showContactModal = true;
    }
    closeContactModal() { this.state.showContactModal = false; }

    async saveContact() {
        try {
            const res = await this._rpc("res.partner", "save_contact", { ...this.state.contactDetail });
            if (res && res.success) {
                this.showToast("Contatto salvato");
                this.state.showContactModal = false;
            }
        } catch (e) { console.error(e); }
    }

    async addContactTag(tagId) {
        if (!this.state.contactDetail.id) return;
        const current = this.state.contactDetail.tags || [];
        if (!current.find(t => t.id === tagId)) {
            const tag = this.state.contactTags.find(t => t.id === tagId);
            if (tag) this.state.contactDetail.tags = [...current, tag];
        }
    }

    onAddContactTag(ev) {
        const val = parseInt(ev.target.value);
        if (val) this.addContactTag(val);
        ev.target.value = "";
    }

    async removeContactTag(tagId) {
        this.state.contactDetail.tags = (this.state.contactDetail.tags || []).filter(t => t.id !== tagId);
    }

    async onEnrich007() {
        if (!this.state.contactDetail.id) return;
        try {
            this.showToast("Agente 007 in azione...");
            await rpc("/web/dataset/call_kw", {
                model: "res.partner",
                method: "action_enrich_007",
                args: [[this.state.contactDetail.id]],
                kwargs: {},
            });
            const data = await this._rpc("res.partner", "get_contact_detail", { partner_id: this.state.contactDetail.id });
            this.state.contactDetail = data || {};
            this.showToast("Agente 007: enrichment completato!");
        } catch (e) {
            console.error(e);
            this.notification.add("Errore Agente 007", { type: "danger" });
        }
    }

    toggle007Panel() { this.state.show007Panel = !this.state.show007Panel; }

    async load007Data(partnerId) {
        if (!partnerId) return;
        this.state.loading007 = true;
        try {
            const data = await this._rpc("res.partner", "rpc_get_007_data", { partner_id: partnerId });
            this.state.data007 = data || {};
        } catch (e) { this.state.data007 = {}; }
        finally { this.state.loading007 = false; }
    }

    async onEnrich007FromPanel() {
        const pid = this.state.msgDetail.partner_id;
        if (!pid) {
            this.notification.add("Nessun partner collegato", { type: "warning" });
            return;
        }
        this.state.loading007 = true;
        try {
            this.showToast("Agente 007 in azione...");
            await rpc("/web/dataset/call_kw", {
                model: "res.partner",
                method: "action_enrich_007",
                args: [[pid]],
                kwargs: {},
            });
            await this.load007Data(pid);
            this.showToast("Agente 007: enrichment completato!");
        } catch (e) {
            console.error(e);
            this.notification.add("Errore Agente 007", { type: "danger" });
            this.state.loading007 = false;
        }
    }

    onLeadPartnerSearch(ev) {
        const q = (ev.target.value || "").toLowerCase().trim();
        this.state.leadPartnerSearch = ev.target.value;
        if (q.length < 2) {
            this.state.leadPartnerResults = [];
            return;
        }
        this.state.leadPartnerResults = (this.state.crmPartners || []).filter(
            function(p) {
                return p.is_company && (
                    (p.name || "").toLowerCase().indexOf(q) >= 0 ||
                    (p.email || "").toLowerCase().indexOf(q) >= 0
                );
            }
        ).slice(0, 15);
    }

    onLeadPartnerSelect(ev) {
        const pid = parseInt(ev.currentTarget.dataset.partnerId);
        const p = this.state.crmPartners.find(function(x) { return x.id === pid; });
        if (p) {
            this.state.leadForm.partner_id = '' + p.id;
            this.state.leadForm.partner_name = p.name;
        }
        this.state.leadPartnerResults = [];
        this.state.leadPartnerSearch = p ? p.name : '';
    }

    onLeadPartnerClear() {
        this.state.leadForm.partner_id = '';
        this.state.leadForm.partner_name = '';
        this.state.leadPartnerSearch = '';
    }

    async openLeadModal() {
        if (!this.state.selectedMsg) return;
        await this.loadCrmData();
        const detail = this.state.msgDetail;
        this.state.leadForm = {
            name: detail.subject || "",
            partner_id: detail.partner_id ? '' + detail.partner_id : "",
            partner_name: detail.partner_name || "",
            contact_name: detail.from_name || "",
            function: "",
            email_from: detail.from_address || "",
            phone: "",
            stage_id: this.state.crmPipelines.length > 0 ? '' + this.state.crmPipelines[0].id : "",
            expected_revenue: "",
            description: "",
            cf_market: "",
            cf_channel: "",
            cf_language: "",
            source: "",
        };
        this.state.leadPartnerSearch = detail.partner_name || '';
        this.state.leadPartnerResults = [];
        this.state.showLeadModal = true;
    }

    closeLeadModal() { this.state.showLeadModal = false; }

    async submitLeadForm() {
        try {
            const res = await this._rpc("cf.mail.message", "create_lead_from_form", {
                message_id: this.state.selectedMsg ? this.state.selectedMsg.id : false,
                name: this.state.leadForm.name,
                partner_id: this.state.leadForm.partner_id || false,
                contact_name: this.state.leadForm.contact_name || "",
                function: this.state.leadForm.function || "",
                email_from: this.state.leadForm.email_from || "",
                phone: this.state.leadForm.phone || "",
                stage_id: this.state.leadForm.stage_id || false,
                expected_revenue: this.state.leadForm.expected_revenue || 0,
                description: this.state.leadForm.description || "",
                cf_market: this.state.leadForm.cf_market || "",
                cf_channel: this.state.leadForm.cf_channel || "",
                cf_language: this.state.leadForm.cf_language || "",
                source: this.state.leadForm.source || false,
            });
            if (res && res.success) {
                this.showToast("Trattativa creata: " + res.lead_name);
                this.state.msgDetail.lead_id = res.lead_id;
                this.state.msgDetail.lead_name = res.lead_name;
                this.state.showLeadModal = false;
                await this.loadLeads();
            } else {
                this.showToast("Errore: " + (res.error || "sconosciuto"));
            }
        } catch (e) { console.error(e); }
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

    _resetComposerState() {
        this.state.composerFrom = this.state.selectedAccount;
        this.state.composerCc = "";
        this.state.composerBcc = "";
        this.state.composerShowCc = false;
        this.state.composerShowBcc = false;
        this.state.composerMinimized = false;
        this.state.composerMaximized = false;
    }

    openReply() {
        this.state.showComposer = true;
        this.state.composerMode = "reply";
        this.state.composerTo = this.state.msgDetail.from_address || "";
        this.state.composerSubject = "Re: " + (this.state.msgDetail.subject || "");
        this._resetComposerState();
        this._initComposerBody();
    }
    openForward() {
        this.state.showComposer = true;
        this.state.composerMode = "forward";
        this.state.composerTo = "";
        this.state.composerSubject = "Fwd: " + (this.state.msgDetail.subject || "");
        this._resetComposerState();
        this._initComposerBody();
    }
    openComposer() {
        this.state.showComposer = true;
        this.state.composerMode = "new";
        this.state.composerTo = "";
        this.state.composerSubject = "";
        this._resetComposerState();
        this._initComposerBody();
    }
    closeComposer() { this.state.showComposer = false; }

    // ── Composer v2 helpers ─────────────────────────────────────────────────

    onComposerFromChange(ev) {
        const val = ev.target.value;
        this.state.composerFrom = val ? parseInt(val) : null;
    }

    toggleComposerCc() {
        this.state.composerShowCc = !this.state.composerShowCc;
        if (!this.state.composerShowCc) this.state.composerCc = "";
    }

    toggleComposerBcc() {
        this.state.composerShowBcc = !this.state.composerShowBcc;
        if (!this.state.composerShowBcc) this.state.composerBcc = "";
    }

    toggleComposerMinimized() {
        this.state.composerMinimized = !this.state.composerMinimized;
    }

    toggleComposerMaximized() {
        this.state.composerMaximized = !this.state.composerMaximized;
        if (this.state.composerMaximized) this.state.composerMinimized = false;
    }

    execFormat(cmd) {
        document.execCommand(cmd, false, null);
        const el = this.composerBody.el;
        if (el) el.focus();
    }

    async insertLink() {
        const url = window.prompt("Inserisci URL:");
        if (url) {
            document.execCommand("createLink", false, url);
            const el = this.composerBody.el;
            if (el) el.focus();
        }
    }

    async saveDraft() {
        const bodyEl = this.composerBody.el;
        const body = bodyEl ? bodyEl.innerHTML : "";
        try {
            const res = await this._rpc("cf.mail.message", "save_draft", {
                account_id: this.state.composerFrom || this.state.selectedAccount,
                to_address: this.state.composerTo || "",
                cc_address: this.state.composerCc || "",
                bcc_address: this.state.composerBcc || "",
                subject: this.state.composerSubject || "",
                body,
            });
            if (res && res.success) this.showToast("Bozza salvata");
            else this.showToast("Bozza salvata in locale");
        } catch (e) { this.showToast("Bozza salvata in locale"); }
    }

    async _initComposerBody() {
        // Carica firma fresca dall'account
        let freshSig = "";
        try {
            const accountId = this.state.composerFrom || this.state.selectedAccount;
            if (accountId) {
                const detail = await this._rpc("cf.mail.account", "get_account_detail", { account_id: accountId });
                freshSig = detail.signature || "";
            }
        } catch(e) {}
        requestAnimationFrame(() => {
            const el = this.composerBody.el;
            if (!el) return;
            const sig = freshSig || this.currentSignature;

            const sigHtml = sig
                ? '<br><div class="cf-composer-sig-divider">—</div><div class="cf-composer-sig">' + sig + "</div>"
                : "";
            const quotedHtml = (this.state.composerMode === "reply" && this.state.msgDetail.body_html)
                ? '<br><blockquote class="cf-composer-quote">' + this.state.msgDetail.body_html + "</blockquote>"
                : "";
            el.innerHTML = sigHtml + quotedHtml;
            el.focus();
            const range = document.createRange();
            range.setStart(el, 0);
            range.collapse(true);
            const sel = window.getSelection();
            if (sel) { sel.removeAllRanges(); sel.addRange(range); }
        });
    }

    async sendEmail() {
        const bodyEl = this.composerBody.el;
        const body = bodyEl ? bodyEl.innerHTML : "";
        if (!this.state.composerTo || !body.trim()) { this.showToast("Compilare destinatario e messaggio"); return; }
        try {
            const res = await this._rpc("cf.mail.message", "send_reply", {
                message_id: this.state.selectedMsg ? this.state.selectedMsg.id : false,
                to_address: this.state.composerTo,
                cc_address: this.state.composerCc || "",
                bcc_address: this.state.composerBcc || "",
                subject: this.state.composerSubject,
                body,
                account_id: this.state.composerFrom || this.state.selectedAccount,
            });
            if (res && res.success) { this.showToast("Email inviata!"); this.closeComposer(); }
            else this.showToast("Errore invio: " + (res.error || "sconosciuto"));
        } catch (e) { this.showToast("Errore invio email"); }
    }

    openNewAccount() {
        this.state.accountForm = { id: null, name: "", email: "", signature: "", imap_host: "imap.gmail.com", imap_port: 993, imap_ssl: true, imap_password: "", imap_enabled: false, imap_status: "", smtp_host: "smtp.gmail.com", smtp_port: 587, smtp_tls: true, color: "#5A6E3A", ooo_enabled: false, ooo_subject: "Sono fuori ufficio", ooo_message: "", ooo_start: "", ooo_end: "" };
        this.state.showAccountModal = true;
    }

    async openEditAccount(accountId) {
        try {
            const data = await this._rpc("cf.mail.account", "get_account_detail", { account_id: accountId });
            this.state.accountForm = { ...data, imap_password: "" };
            this.state.showAccountModal = true;
        } catch (e) { console.error(e); }
    }

    closeAccountModal() { this.state.showAccountModal = false; }

    async submitAccountForm() {
        try {
            const res = await this._rpc("cf.mail.account", "save_account", { ...this.state.accountForm });
            if (res && res.success) {
                this.showToast("Account salvato");
                this.state.showAccountModal = false;
                await this.loadAccounts();
            }
        } catch (e) { console.error(e); }
    }

    async testConnection() {
        try {
            this.showToast("Test connessione...");
            const res = await this._rpc("cf.mail.account", "test_connection", { account_id: this.state.accountForm.id });
            if (res.success) {
                this.showToast("Connessione OK ✓");
                this.state.accountForm.imap_status = "Connessione OK ✓";
            } else {
                this.showToast("Errore: " + res.error);
                this.state.accountForm.imap_status = "Errore: " + res.error;
            }
        } catch (e) { this.showToast("Errore connessione"); }
    }

    async syncNow() {
        try {
            this.showToast("Sincronizzazione in corso...");
            await this._rpc("cf.mail.account", "sync_now", { account_id: this.state.accountForm.id });
            this.showToast("Sincronizzazione completata");
            this.state.showAccountModal = false;
            await this.loadAccounts();
            await this.loadMessages();
        } catch (e) { this.showToast("Errore sync"); }
    }

    async syncAllAccounts() {
        try {
            this.showToast("Sincronizzazione in corso...");
            await this._rpc("cf.mail.account", "sync_now", {});
            this.showToast("Sincronizzazione completata");
            await this.loadAccounts();
            await this.loadMessages();
        } catch (e) { this.showToast("Errore sync"); }
    }

    get listHeaderLabel() {
        const total = this.filteredMessages.length;
        const map = { INBOX: "Inbox", Starred: "Preferiti", Sent: "Inviati", Archived: "Archivio", Assigned: "Assegnate a me" };
        return (map[this.state.folder] || this.state.folder) + " — " + total;
    }

    get currentSignature() {
        const accountId = this.state.composerFrom || this.state.selectedAccount;
        if (!accountId) return "";
        const acc = this.state.accounts.find(a => a.id === accountId);
        return acc ? (acc.signature || "") : "";
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

    // AI ASSISTANT

    async _callAI(action) {
        const msg = this.state.msgDetail;
        const text = msg.body_plain || msg.body_html || '';
        const context = {
            partner: msg.partner_name || '',
            company_name: msg.partner_company || '',
            leads: (msg.partner_leads || []).map(function(l) { return l.name; }).join(', '),
        };
        this.state.aiLoading = true;
        this.state.aiResult = '';
        try {
            const res = await this._rpc('cf.mail.message', 'ai_action', {
                action: action, text: text, context: context
            });
            this.state.aiResult = res.result || res.error || 'Nessun risultato';
            this.state.showAIPanel = true;
        } catch(e) {
            this.state.aiResult = 'Errore: ' + e.message;
        } finally {
            this.state.aiLoading = false;
        }
    }

    async onTranslate() {
        const msg = this.state.msgDetail;
        const text = msg.body_plain || msg.body_html || '';
        this.state.aiLoading = true;
        try {
            const res = await this._rpc('cf.mail.message', 'ai_action', { action: 'translate', text: text });
            if (res.result) {
                const wrap = this.__owl__.refs.emailContent;
                if (wrap) wrap.innerHTML = '<div style="padding:8px;background:#e3f2fd;border-radius:6px;font-size:13px;line-height:1.6">' + res.result.replace(/\n/g, '<br>') + '</div>';
                this.state.aiResult = res.result;
                this.state.showAIPanel = true;
            }
        } catch(e) {} finally { this.state.aiLoading = false; }
    }

    toggleAIPanel() { this.state.showAIPanel = !this.state.showAIPanel; }
    async onAISummarize() { await this._callAI('summarize'); }
    async onAIAnalyze() { await this._callAI('analyze'); }
    async onAISuggestReply() { await this._callAI('suggest_reply'); }

    onAIUseAsReply() {
        if (!this.state.aiResult) return;
        this.state.showComposer = true;
        this.state.composerMode = 'reply';
        this.state.composerTo = this.state.msgDetail.from_address || '';
        this.state.composerSubject = 'Re: ' + (this.state.msgDetail.subject || '');
        const self = this;
        setTimeout(function() {
            const body = self.__owl__.refs.composerBody;
            if (body) body.innerHTML = self.state.aiResult.replace(/\n/g, '<br>');
        }, 100);
    }

    async onComposerAIDraft() {
        const subject = this.state.composerSubject || '';
        if (!subject) { alert('Inserisci prima un oggetto'); return; }
        this.state.composerAILoading = true;
        try {
            const res = await this._rpc('cf.mail.message', 'ai_action', {
                action: 'draft', text: subject
            });
            if (res.result) {
                const body = this.__owl__.refs.composerBody;
                if (body) body.innerHTML = res.result.replace(/\n/g, '<br>');
            }
        } catch(e) {} finally { this.state.composerAILoading = false; }
    }

    async onComposerAIImprove() {
        const body = this.__owl__.refs.composerBody;
        const text = body ? body.innerText : '';
        if (!text.trim()) { alert('Scrivi prima qualcosa da migliorare'); return; }
        this.state.composerAILoading = true;
        try {
            const res = await this._rpc('cf.mail.message', 'ai_action', {
                action: 'draft', text: 'Migliora e professionalizza questa email mantenendo il senso: ' + text
            });
            if (res.result && body) body.innerHTML = res.result.replace(/\n/g, '<br>');
        } catch(e) {} finally { this.state.composerAILoading = false; }
    }

    async onComposerAISuggest() {
        const msg = this.state.msgDetail;
        if (!msg) { alert('Seleziona prima un messaggio'); return; }
        this.state.composerAILoading = true;
        try {
            const res = await this._rpc('cf.mail.message', 'ai_action', {
                action: 'suggest_reply',
                text: msg.body_plain || msg.body_html || '',
                context: { partner: msg.partner_name || '', company_name: msg.partner_company || '' }
            });
            if (res.result) {
                const body = this.__owl__.refs.composerBody;
                if (body) body.innerHTML = res.result.replace(/\n/g, '<br>');
            }
        } catch(e) {} finally { this.state.composerAILoading = false; }
    }


}
registry.category("actions").add("cf_mail_client", CfMailClient);
