/** @odoo-module **/
import { Component, useEnv } from "@odoo/owl";

export class LavagnaPanelCalendar extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaPanelCalendar";
    static props = ["*"];

    setup() {
        this.env = useEnv();
    }

    onEventClick(evt) {
        this.env.actions.openOdooRecord('calendar.event', evt.id);
    }

    formatDate(isoStr) {
        if (!isoStr) return '';
        const d = new Date(isoStr);
        return d.toLocaleDateString('it-IT', {
            weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
        });
    }
}
