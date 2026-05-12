/** @odoo-module **/
/**
 * Client action: opens the F8 Outlook-style ComposeWizardDialog
 * from casafolino_mail as a dialog overlay, then navigates back.
 *
 * Context keys:
 *   default_partner_email  — pre-fill "To" field
 *   default_subject        — pre-fill subject
 *   default_body           — pre-fill body HTML
 *   default_partner_id     — partner record id (for AI/snippet context)
 *   default_thread_id      — source record id
 *   default_thread_model   — source model (crm.lead, res.partner, …)
 */
import { Component, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

class ComposeF8Action extends Component {
    static template = "casafolino_crm_export.ComposeF8Action";
    static props = ["*"];

    setup() {
        this.dialog = useService("dialog");
        this.actionService = useService("action");
        this.user = useService("user");

        onMounted(async () => {
            const ctx = this.props.action?.context || {};

            try {
                const { ComposeWizardDialog } = await import(
                    "@casafolino_mail/js/mail_v3/compose_wizard_dialog"
                );

                // Resolve account_id from current user via DB lookup
                let accountId = null;
                try {
                    const accounts = await rpc("/web/dataset/call_kw", {
                        model: "casafolino.mail.account",
                        method: "search_read",
                        args: [[
                            ["responsible_user_id", "=", this.user.userId],
                            ["active", "=", true],
                        ]],
                        kwargs: { fields: ["id"], limit: 1 },
                    });
                    if (accounts && accounts.length) {
                        accountId = accounts[0].id;
                    }
                } catch (e) {
                    console.warn("[ComposeF8] account lookup failed:", e);
                }

                this.dialog.add(ComposeWizardDialog, {
                    partnerEmail: ctx.default_partner_email || "",
                    defaultSubject: ctx.default_subject || "",
                    defaultBody: ctx.default_body || "",
                    partnerId: ctx.default_partner_id || null,
                    threadId: ctx.default_thread_id || null,
                    threadModel: ctx.default_thread_model || null,
                    accountId: accountId,
                    onSent: () => {},
                });
            } catch (e) {
                console.error("[ComposeF8] Failed to open composer:", e);
            }

            // Navigate back to previous view after dialog is spawned.
            // The dialog lives in the dialog overlay, independent of actions.
            try {
                await this.actionService.restore();
            } catch (e) {
                console.warn("[ComposeF8] restore() failed (non-critical):", e);
            }
        });
    }
}

registry.category("actions").add("casafolino_mail.compose_f8", ComposeF8Action);
