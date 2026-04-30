/** @odoo-module **/
import { Component, useEnv } from "@odoo/owl";

export class LavagnaTaskCard extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaTaskCard";
    static props = ["*"];

    setup() {
        this.env = useEnv();
    }

    onClick() {
        this.env.actions.openTaskDrawer(this.props.task.id);
    }

    onMailClick(ev) {
        ev.stopPropagation();
        this.env.actions.openTaskDrawer(this.props.task.id);
    }

    onPartnerClick(ev) {
        ev.stopPropagation();
        if (this.props.task.partner_id) {
            this.env.actions.openOdooRecord('res.partner', this.props.task.partner_id);
        }
    }

    getActivityClass() {
        const last = this.props.task.last_activity;
        if (!last) return 'o_dormant';
        const days = (Date.now() - new Date(last).getTime()) / (1000 * 60 * 60 * 24);
        if (days > 30) return 'o_dormant';
        if (days > 7) return 'o_inactive';
        return '';
    }

    hasUnread() {
        return (this.props.task.unread_count || 0) > 0;
    }

    getUserInitials() {
        const users = this.props.task.user_ids || [];
        return users.slice(0, 2).map(u => u.initials).join(' ');
    }
}
