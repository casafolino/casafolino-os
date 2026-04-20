/** @odoo-module **/
import { Component } from "@odoo/owl";

export class Sidebar360 extends Component {
    static template = "casafolino_mail.Sidebar360";
    static props = ["*"];

    getHotnessClass(tier) {
        return 'mv3-hotness-badge--' + (tier || 'dormant');
    }

    formatCurrency(val) {
        if (!val && val !== 0) return '-';
        return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(val);
    }

    onQuickAction(key) {
        if (this.props.onQuickAction) {
            this.props.onQuickAction(key);
        }
    }
}
