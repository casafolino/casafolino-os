/** @odoo-module **/
/**
 * Legacy mail timeline panel. Mail V2 has been removed, so compose/open actions
 * fall back to native partner chatter.
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
        if (mail && mail.partner_id) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "res.partner",
                res_id: mail.partner_id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    async onCompose() {
        const init = this.env.lavagnaState.data ? this.env.lavagnaState.data.initiative : {};
        const partnerId = init.partner_id || false;
        if (!partnerId) {
            this.notificationService.add("Nessun partner collegato", { type: "warning" });
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
            target: "current",
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
