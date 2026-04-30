/** @odoo-module **/
import { Component, useEnv } from "@odoo/owl";

export class LavagnaPanelMail extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaPanelMail";
    static props = ["*"];

    setup() {
        this.env = useEnv();
    }

    onMailClick(msg) {
        if (msg.task_id) {
            this.env.actions.openTaskDrawer(msg.task_id);
        }
    }

    formatDate(isoStr) {
        if (!isoStr) return '';
        const d = new Date(isoStr);
        const now = new Date();
        const diff = (now - d) / (1000 * 60 * 60);
        if (diff < 1) return 'ora';
        if (diff < 24) return Math.floor(diff) + 'h';
        if (diff < 48) return 'ieri';
        return d.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' });
    }
}
