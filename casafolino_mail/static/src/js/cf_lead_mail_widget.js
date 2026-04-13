/** @odoo-module **/
import { Component, useState, useRef, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

var _nextTempId = 1;

class CfLeadMailWidget extends Component {
    static template = "cf_lead_mail_widget.Main";
    static props = ["*"];

    setup() {
        this.notification = useService("notification");
        this.fileInputRef = useRef("fileInput");
        this.composerBodyRef = useRef("composerBody");
        this.state = useState({
            messages: [],
            loading: false,
            expandedId: null,
            expandedDetail: null,
            showComposer: false,
            composerTo: "",
            composerCc: "",
            composerSubject: "",
            composerBody: "",
            composerSending: false,
            composerAttachments: [],
            replyToId: null,
            showTemplates: false,
            templates: [],
            showAttachDropdown: false,
            showAttachModal: false, attachModalSearch: '',
            attachModalResults: [], attachModalSelected: [],
            showUrlModal: false, urlInput: '',
        });

        onWillStart(this.loadMessages.bind(this));
        onWillUpdateProps(this.onPropsUpdate.bind(this));
    }

    get leadId() {
        return this.props.record && this.props.record.resId;
    }

    async onPropsUpdate(nextProps) {
        if (nextProps.record && nextProps.record.resId !== this.leadId) {
            await this.loadMessages();
        }
    }

    async loadMessages() {
        var lid = this.leadId;
        if (!lid) { this.state.messages = []; return; }
        this.state.loading = true;
        try {
            var msgs = await rpc("/web/dataset/call_kw", {
                model: "casafolino.mail.message",
                method: "get_lead_emails",
                args: [],
                kwargs: { lead_id: lid },
            });
            this.state.messages = msgs || [];
        } catch (e) {
            console.error("CfLeadMailWidget loadMessages error", e);
        }
        this.state.loading = false;
    }

    async onClickRow(msgId) {
        if (this.state.expandedId === msgId) {
            this.state.expandedId = null;
            this.state.expandedDetail = null;
            return;
        }
        this.state.expandedId = msgId;
        this.state.expandedDetail = null;
        try {
            var detail = await rpc("/web/dataset/call_kw", {
                model: "casafolino.mail.message",
                method: "get_message_detail",
                args: [],
                kwargs: { message_id: msgId },
            });
            this.state.expandedDetail = detail;
        } catch (e) {
            console.error("CfLeadMailWidget detail error", e);
        }
    }

    onClickReply(msg) {
        this.state.showComposer = true;
        this.state.replyToId = msg.id;
        this.state.composerTo = msg.from_address || "";
        this.state.composerCc = "";
        this.state.composerSubject = msg.subject ? "Re: " + msg.subject.replace(/^Re:\s*/i, "") : "";
        this.state.composerBody = "";
        this.state.composerAttachments = [];
        this.state.showTemplates = false;
    }

    onClickNewEmail() {
        var rec = this.props.record;
        var partnerEmail = "";
        if (rec && rec.data && rec.data.email_from) {
            partnerEmail = rec.data.email_from;
        }
        this.state.showComposer = true;
        this.state.replyToId = null;
        this.state.composerTo = partnerEmail;
        this.state.composerCc = "";
        this.state.composerSubject = "";
        this.state.composerBody = "";
        this.state.composerAttachments = [];
        this.state.showTemplates = false;
    }

    onCloseComposer() {
        this.state.showComposer = false;
    }

    onInputTo(ev) { this.state.composerTo = ev.target.value; }
    onInputCc(ev) { this.state.composerCc = ev.target.value; }
    onInputSubject(ev) { this.state.composerSubject = ev.target.value; }
    onInputBody(ev) { this.state.composerBody = ev.target.innerHTML || ""; }

    // ── Attachments ──────────────────────────────────────────────

    onClickAttachFile() {
        if (this.fileInputRef.el) {
            this.fileInputRef.el.click();
        }
    }

    onFileSelected(ev) {
        var files = ev.target.files;
        if (!files || !files.length) return;
        var self = this;
        for (var i = 0; i < files.length; i++) {
            (function(file) {
                var reader = new FileReader();
                reader.onload = function(e) {
                    var b64 = e.target.result.split(",")[1] || "";
                    self.state.composerAttachments.push({
                        tempId: _nextTempId++,
                        name: file.name,
                        size: file.size,
                        mimetype: file.type || "application/octet-stream",
                        content_base64: b64,
                        source: "pc",
                    });
                };
                reader.readAsDataURL(file);
            })(files[i]);
        }
        ev.target.value = "";
    }

    onRemoveAttachment(att) {
        var idx = this.state.composerAttachments.indexOf(att);
        if (idx >= 0) {
            this.state.composerAttachments.splice(idx, 1);
        }
    }

    toggleAttachDropdown() {
        this.state.showAttachDropdown = !this.state.showAttachDropdown;
    }

    onAttachFromPC() {
        this.state.showAttachDropdown = false;
        this.onClickAttachFile();
    }

    async openAttachFromOdoo() {
        this.state.showAttachDropdown = false;
        this.state.showAttachModal = true;
        this.state.attachModalSearch = '';
        this.state.attachModalSelected = [];
        try {
            this.state.attachModalResults = await rpc("/web/dataset/call_kw", {
                model: "casafolino.mail.message", method: "get_odoo_attachments",
                args: [], kwargs: { search: '', limit: 30 },
            }) || [];
        } catch (e) { this.state.attachModalResults = []; }
    }

    async onAttachModalSearch(ev) {
        this.state.attachModalSearch = ev.target.value;
        try {
            this.state.attachModalResults = await rpc("/web/dataset/call_kw", {
                model: "casafolino.mail.message", method: "get_odoo_attachments",
                args: [], kwargs: { search: ev.target.value, limit: 30 },
            }) || [];
        } catch (e) { this.state.attachModalResults = []; }
    }

    toggleAttachSelect(id) {
        var idx = this.state.attachModalSelected.indexOf(id);
        if (idx >= 0) {
            this.state.attachModalSelected.splice(idx, 1);
        } else {
            this.state.attachModalSelected.push(id);
        }
    }

    confirmAttachFromOdoo() {
        for (var i = 0; i < this.state.attachModalResults.length; i++) {
            var r = this.state.attachModalResults[i];
            if (this.state.attachModalSelected.indexOf(r.id) >= 0 && r.id) {
                this.state.composerAttachments.push({
                    id: r.id, name: r.name, size: r.size || 0,
                    mimetype: r.mimetype || '', source: 'odoo',
                });
            }
        }
        this.state.showAttachModal = false;
    }

    closeAttachModal() { this.state.showAttachModal = false; }

    openUrlModal() {
        this.state.showAttachDropdown = false;
        this.state.showUrlModal = true;
        this.state.urlInput = '';
    }

    closeUrlModal() { this.state.showUrlModal = false; }

    onUrlInput(ev) { this.state.urlInput = ev.target.value; }

    async confirmUrlAttach() {
        var url = this.state.urlInput.trim();
        if (!url) return;
        var filename = url.split('/').pop().split('?')[0] || 'file';
        try {
            var res = await rpc("/web/dataset/call_kw", {
                model: "casafolino.mail.message", method: "attach_from_url",
                args: [], kwargs: { url: url, filename: filename },
            });
            if (res && res.success) {
                this.state.composerAttachments.push({
                    id: res.id, name: res.name || filename,
                    size: res.size || 0, source: 'url',
                });
                this.state.showUrlModal = false;
            } else {
                this.notification.add("Errore: " + (res.error || ""), { type: "danger" });
            }
        } catch (e) {
            this.notification.add("Errore download URL", { type: "danger" });
        }
    }

    // ── Templates ────────────────────────────────────────────────

    async onToggleTemplates() {
        this.state.showTemplates = !this.state.showTemplates;
        if (this.state.showTemplates && !this.state.templates.length) {
            try {
                this.state.templates = await rpc("/web/dataset/call_kw", {
                    model: "casafolino.mail.message",
                    method: "get_templates",
                    args: [],
                    kwargs: {},
                }) || [];
            } catch (e) {
                console.error("Error loading templates", e);
            }
        }
    }

    onSelectTemplate(tpl) {
        this.state.composerSubject = tpl.subject || this.state.composerSubject;
        // Sostituisci variabili
        var body = tpl.body_html || "";
        var rec = this.props.record;
        var partnerName = (rec && rec.data && rec.data.partner_name) || "";
        var companyName = "";
        body = body.replace(/\{\{partner_name\}\}/g, partnerName);
        body = body.replace(/\{\{company_name\}\}/g, companyName);
        body = body.replace(/\{\{user_name\}\}/g, this.env.services.user ? this.env.services.user.name || "" : "");
        body = body.replace(/\{\{user_email\}\}/g, "");
        this.state.composerBody = body;
        if (this.composerBodyRef.el) {
            this.composerBodyRef.el.innerHTML = body;
        }
        // Aggiungi allegati di default del template
        for (var i = 0; i < (tpl.attachments || []).length; i++) {
            var ta = tpl.attachments[i];
            this.state.composerAttachments.push({
                id: ta.id,
                name: ta.name,
                size: ta.size || 0,
                source: "odoo",
            });
        }
        this.state.showTemplates = false;
    }

    // ── Send ─────────────────────────────────────────────────────

    async onSendEmail() {
        if (!this.state.composerTo || !this.state.composerBody) {
            this.notification.add("Destinatario e corpo obbligatori", { type: "warning" });
            return;
        }
        this.state.composerSending = true;
        // Separa allegati PC (base64) da allegati Odoo (ids)
        var pcAttachments = [];
        var odooIds = [];
        for (var i = 0; i < this.state.composerAttachments.length; i++) {
            var att = this.state.composerAttachments[i];
            if (att.content_base64) {
                pcAttachments.push({
                    filename: att.name,
                    content_base64: att.content_base64,
                    mimetype: att.mimetype || "application/octet-stream",
                });
            } else if (att.id) {
                odooIds.push(att.id);
            }
        }
        try {
            var res = await rpc("/web/dataset/call_kw", {
                model: "casafolino.mail.message",
                method: "send_from_lead",
                args: [],
                kwargs: {
                    lead_id: this.leadId,
                    to_address: this.state.composerTo,
                    cc_address: this.state.composerCc,
                    subject: this.state.composerSubject,
                    body: this.state.composerBody,
                    reply_to_id: this.state.replyToId || false,
                    attachments: pcAttachments,
                    attachment_ids: odooIds,
                },
            });
            if (res && res.success) {
                this.notification.add("Email inviata", { type: "success" });
                this.state.showComposer = false;
                await this.loadMessages();
            } else {
                this.notification.add("Errore: " + (res.error || "sconosciuto"), { type: "danger" });
            }
        } catch (e) {
            this.notification.add("Errore invio: " + e.message, { type: "danger" });
        }
        this.state.composerSending = false;
    }
}

registry.category("fields").add("cf_lead_mail_widget", {
    component: CfLeadMailWidget,
    supportedTypes: ["one2many"],
});
