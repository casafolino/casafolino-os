/** @odoo-module **/
import { Component } from "@odoo/owl";

export class ThreadList extends Component {
    static template = "casafolino_mail.ThreadList";
    static props = ["*"];

    selectThread(threadId) {
        this.props.onSelect(threadId);
    }

    toggleSelect(threadId) {
        if (this.props.onToggleSelect) {
            this.props.onToggleSelect(threadId);
        }
    }

    isSelected(threadId) {
        const ids = this.props.selectedThreadIds || [];
        return ids.includes(threadId);
    }

    getAccountColor(accountId) {
        const colors = ['#5A6E3A', '#2980B9', '#8E44AD'];
        const accounts = this.props.accounts || [];
        const idx = accounts.findIndex(a => a.id === accountId);
        return colors[idx >= 0 ? idx % colors.length : 0];
    }
}
