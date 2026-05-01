/** @odoo-module **/
/**
 * F2.6.4: Panel "Mail" — timeline of casafolino_mail.message for partner.
 */
import { Component, useEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class LavagnaPanelMailThread extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaPanelMailThread";
    static props = ["*"];

    setup() {
        this.env = useEnv();
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");
        this.orm = useService("orm");
    }

    get mails() {
        return this.props.mails || [];
    }

    get partnerName() {
        const init = this.env.lavagnaState.data ? this.env.lavagnaState.data.initiative : {};
        return init.partner_name || '';
    }

    get hasPartner() {
        const init = this.env.lavagnaState.data ? this.env.lavagnaState.data.initiative : {};
        return !!init.partner_id;
    }

    onMailClick(mail) {
        // Navigate to mail app
        this.actionService.doAction('casafolino_mail.action_mail_v3_client');
    }

    async onCompose() {
        const init = this.env.lavagnaState.data ? this.env.lavagnaState.data.initiative : {};
        const partnerId = init.partner_id || false;
        let partnerEmail = '';
        if (partnerId) {
            try {
                const [partner] = await this.orm.read('res.partner', [partnerId], ['email']);
                partnerEmail = partner.email || '';
            } catch {}
        }

        const { ComposeWizardDialog } = await import(
            "@casafolino_mail/js/mail_v3/compose_wizard_dialog"
        );
        this.dialogService.add(ComposeWizardDialog, {
            partnerEmail: partnerEmail,
            defaultSubject: '',
            onSent: () => {
                this.notificationService.add('Mail inviata', { type: 'success' });
                this.env.actions.refreshData();
            },
        });
    }

    formatDate(isoStr) {
        if (!isoStr) return '';
        const d = new Date(isoStr);
        const now = new Date();
        const diff = (now - d) / (1000 * 60 * 60);
        if (diff < 1) return 'ora';
        if (diff < 24) return Math.floor(diff) + 'h fa';
        if (diff < 48) return 'ieri';
        return d.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' });
    }
}
