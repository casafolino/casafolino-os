/** @odoo-module **/
import { Component } from "@odoo/owl";

export class ThreadList extends Component {
    static template = "casafolino_mail.ThreadList";
    static props = ["*"];

    selectThread(threadId) {
        this.props.onSelect(threadId);
    }

    getAccountColor(accountId) {
        const colors = ['#5A6E3A', '#2980B9', '#8E44AD'];
        const accounts = this.props.accounts || [];
        const idx = accounts.findIndex(a => a.id === accountId);
        return colors[idx >= 0 ? idx % colors.length : 0];
    }
}
