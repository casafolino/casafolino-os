/** @odoo-module **/
/**
 * Client action wrapper: opens ComposeWizardDialog from casafolino_mail
 * as a dialog, then closes itself. Allows Python buttons to invoke the
 * F8 Outlook-style composer via ir.actions.client.
 *
 * Context keys:
 *   default_partner_email — pre-fill "To" field
 *   default_subject       — pre-fill subject
 *   default_body          — pre-fill body HTML
 */
import { Component, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class ComposeF8Action extends Component {
    static template = "casafolino_crm_export.ComposeF8Action";
    static props = ["*"];

    setup() {
        this.dialog = useService("dialog");
        this.action = useService("action");

        onMounted(async () => {
            try {
                const { ComposeWizardDialog } = await import(
                    "@casafolino_mail/js/mail_v3/compose_wizard_dialog"
                );
                const ctx = this.props.action?.context || {};
                this.dialog.add(ComposeWizardDialog, {
                    partnerEmail: ctx.default_partner_email || "",
                    defaultSubject: ctx.default_subject || "",
                    defaultBody: ctx.default_body || "",
                    onSent: () => {},
                });
            } catch (e) {
                console.error("ComposeF8Action: failed to open composer", e);
            }
            // Close the action (navigate back to previous view)
            this.action.doAction({ type: "ir.actions.act_window_close" });
        });
    }
}

registry.category("actions").add("casafolino_mail.compose_f8", ComposeF8Action);
