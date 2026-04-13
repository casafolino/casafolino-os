/** @odoo-module **/
import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class CfLeadMailWidget extends Component {
    static template = "cf_lead_mail_widget.Main";
    static props = ["*"];

    setup() {
        this.notification = useService("notification");
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
            replyToId: null,
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
    }

    onCloseComposer() {
        this.state.showComposer = false;
    }

    onInputTo(ev) { this.state.composerTo = ev.target.value; }
    onInputCc(ev) { this.state.composerCc = ev.target.value; }
    onInputSubject(ev) { this.state.composerSubject = ev.target.value; }
    onInputBody(ev) { this.state.composerBody = ev.target.innerHTML || ev.target.textContent || ""; }

    async onSendEmail() {
        if (!this.state.composerTo || !this.state.composerBody) {
            this.notification.add("Destinatario e corpo obbligatori", { type: "warning" });
            return;
        }
        this.state.composerSending = true;
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
