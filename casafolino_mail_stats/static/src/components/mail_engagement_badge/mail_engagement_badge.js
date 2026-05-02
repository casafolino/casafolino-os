/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const STATUS_CONFIG = {
    cold: { label: "Cold", color: "#9e9e9e", icon: "⚪" },
    warm: { label: "Warm", color: "#ffb300", icon: "🟡" },
    hot: { label: "Hot", color: "#43a047", icon: "🟢" },
    replied: { label: "Replied", color: "#7b1fa2", icon: "🟣" },
    bounced: { label: "Bounced", color: "#e53935", icon: "🔴" },
};

export class MailEngagementBadge extends Component {
    static template = "casafolino_mail_stats.MailEngagementBadge";
    static props = { ...standardFieldProps };

    get statusConfig() {
        const value = this.props.record.data[this.props.name];
        return STATUS_CONFIG[value] || STATUS_CONFIG.cold;
    }

    get displayValue() {
        const config = this.statusConfig;
        return `${config.icon} ${config.label}`;
    }
}

registry.category("fields").add("mail_engagement_badge", {
    component: MailEngagementBadge,
});
