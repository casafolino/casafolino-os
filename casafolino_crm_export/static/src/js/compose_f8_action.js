/** @odoo-module **/
/**
 * Client action: opens the F8 Outlook-style ComposeWizardDialog
 * from casafolino_mail as a dialog overlay, then navigates back.
 *
 * Context keys:
 *   default_partner_email — pre-fill "To" field
 *   default_subject       — pre-fill subject
 *   default_body          — pre-fill body HTML
 *   default_project_id    — link outbound email to this dossier
 */
import { Component, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class ComposeF8Action extends Component {
    static template = "casafolino_crm_export.ComposeF8Action";
    static props = ["*"];

    setup() {
        this.dialog = useService("dialog");
        this.actionService = useService("action");

        onMounted(async () => {
            const ctx = this.props.action?.context || {};

            try {
                const { ComposeWizardDialog } = await import(
                    "@casafolino_mail/js/mail_v3/compose_wizard_dialog"
                );

                this.dialog.add(ComposeWizardDialog, {
                    partnerEmail: ctx.default_partner_email || "",
                    defaultSubject: ctx.default_subject || "",
                    defaultBody: ctx.default_body || "",
                    projectId: ctx.default_project_id || false,
                    onSent: () => {},
                });
            } catch (e) {
                console.error("[ComposeF8] Failed to open composer:", e);
            }

            // Navigate back to previous view after dialog is spawned.
            // The dialog lives in the dialog overlay, independent of actions.
            this.actionService.restore();
        });
    }
}

registry.category("actions").add("casafolino_mail.compose_f8", ComposeF8Action);
