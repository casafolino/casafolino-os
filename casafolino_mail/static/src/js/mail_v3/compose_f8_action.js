/** @odoo-module **/

import { Component, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ComposeWizardDialog } from "./compose_wizard_dialog";

export class ComposeF8Action extends Component {
    static template = "casafolino_mail.ComposeF8Action";
    static props = ["*"];

    setup() {
        this.dialog = useService("dialog");
        this.actionService = useService("action");
        this.opened = false;

        onMounted(() => {
            if (this.opened) {
                return;
            }
            this.opened = true;
            const action = this.props.action || {};
            const ctx = action.context || {};
            const replyToId = ctx.default_thread_model === "casafolino.mail.message"
                ? ctx.default_thread_id
                : (ctx.default_in_reply_to_message_id || false);

            const closeAction = () => {
                this.actionService.doAction({ type: "ir.actions.act_window_close" });
            };

            this.dialog.add(ComposeWizardDialog, {
                accountId: ctx.default_account_id || false,
                partnerEmail: ctx.default_partner_email || ctx.default_to_emails || "",
                defaultSubject: ctx.default_subject || "",
                defaultBody: ctx.default_body_html || "",
                partnerId: ctx.default_partner_id || false,
                threadId: ctx.default_thread_id || false,
                threadModel: ctx.default_thread_model || "",
                replyToId,
                mode: ctx.default_mode || (replyToId ? "reply" : "new"),
                onSent: closeAction,
                onClose: closeAction,
            });
        });
    }
}

registry.category("actions").add("casafolino_mail.compose_f8", ComposeF8Action);
