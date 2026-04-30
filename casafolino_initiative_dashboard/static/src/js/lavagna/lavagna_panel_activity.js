/** @odoo-module **/
import { Component, useEnv } from "@odoo/owl";

export class LavagnaPanelActivity extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaPanelActivity";
    static props = ["*"];

    setup() {
        this.env = useEnv();
    }

    onActivityClick(item) {
        if (item.model === 'project.task' && item.res_id) {
            this.env.actions.openTaskDrawer(item.res_id);
        }
    }

    formatDate(isoStr) {
        if (!isoStr) return '';
        const d = new Date(isoStr);
        const now = new Date();
        const diff = (now - d) / (1000 * 60 * 60);
        if (diff < 1) return 'ora';
        if (diff < 24) return Math.floor(diff) + 'h';
        return d.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' });
    }

    stripHtml(html) {
        if (!html) return '';
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        return (tmp.textContent || tmp.innerText || '').substring(0, 120);
    }
}
