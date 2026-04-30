/** @odoo-module **/
import { Component } from "@odoo/owl";

export class LavagnaTimeline extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaTimeline";
    static props = ["*"];

    getProgress() {
        const data = this.props.data;
        if (!data || !data.date_start || !data.date_end) return null;
        const start = new Date(data.date_start).getTime();
        const end = new Date(data.date_end).getTime();
        const now = new Date(data.today).getTime();
        if (end <= start) return null;
        const pct = Math.max(0, Math.min(100, ((now - start) / (end - start)) * 100));
        return Math.round(pct);
    }

    formatDate(isoStr) {
        if (!isoStr) return '—';
        return new Date(isoStr).toLocaleDateString('it-IT', {
            day: 'numeric', month: 'short', year: 'numeric',
        });
    }
}
