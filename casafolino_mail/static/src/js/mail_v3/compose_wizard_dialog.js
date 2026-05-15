/** @odoo-module **/
/**
 * Standalone Dialog wrapper for ComposeWizard.
 * Allows other modules to open the F8 Outlook-style composer as a popup
 * without navigating to the full Mail CRM app.
 *
 * Usage from another module:
 *   const { ComposeWizardDialog } = await import(
 *       "@casafolino_mail/js/mail_v3/compose_wizard_dialog"
 *   );
 *   this.dialogService.add(ComposeWizardDialog, {
 *       partnerEmail: "buyer@example.com",
 *       defaultSubject: "Re: Quotation",
 *       projectId: 42,
 *       onSent: () => { ... },
 *   });
 */
import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";
import { ComposeWizard } from "./mail_v3_compose";

export class ComposeWizardDialog extends Component {
    static template = "casafolino_mail.ComposeWizardDialog";
    static components = { Dialog, ComposeWizard };
    static props = ["*"];

    setup() {
        this.state = useState({
            loading: true,
            draftId: null,
            prefilled: null,
            accountId: null,
            noAccount: false,
            error: null,
        });

        onWillStart(async () => {
            try {
                const prepareParams = {
                    mode: 'new',
                    prefilled_body: '',
                    project_id: this.props.projectId || false,
                };
                // Pass caller-resolved account_id to prepare endpoint
                if (this.props.accountId) {
                    prepareParams.account_id = this.props.accountId;
                }

                const result = await rpc('/cf/mail/v3/compose/prepare', prepareParams);
                if (!result || !result.draft_id) {
                    this.state.error = 'Impossibile creare bozza mail';
                    return;
                }
                this.state.draftId = result.draft_id;

                // Merge caller defaults into prefilled
                const pf = result.prefilled || {};
                if (this.props.partnerEmail) {
                    pf.to = this.props.partnerEmail;
                }
                if (this.props.defaultSubject) {
                    pf.subject = this.props.defaultSubject;
                }
                if (this.props.defaultBody) {
                    pf.body_html = (this.props.defaultBody || '') + (pf.body_html || '');
                }
                // Inject context props for AI/snippet/template features
                if (this.props.partnerId) {
                    pf.partner_id = this.props.partnerId;
                }
                if (this.props.threadId) {
                    pf.thread_id = this.props.threadId;
                }
                if (this.props.threadModel) {
                    pf.thread_model = this.props.threadModel;
                }

                this.state.prefilled = pf;
                this.state.accountId = pf.account_id || this.props.accountId || null;
                this.state.noAccount = !this.state.accountId;
            } catch (e) {
                this.state.error = 'Errore preparazione composer: ' + (e.message || e);
            } finally {
                this.state.loading = false;
            }
        });
    }

    onComposeSent() {
        this.props.close();
        if (this.props.onSent) this.props.onSent();
    }

    onComposeClose() {
        this.props.close();
        if (this.props.onClose) this.props.onClose();
    }
}
