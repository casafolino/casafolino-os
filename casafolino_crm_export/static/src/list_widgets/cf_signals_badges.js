/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class CfSignalsBadges extends Component {
    static template = "casafolino_crm_export.CfSignalsBadges";
    static props = { ...standardFieldProps };

    get hasOpenIssue() {
        return this.props.record.data.casafolino_has_open_issue;
    }
    get hasOverdueFollowup() {
        return this.props.record.data.casafolino_has_overdue_followup;
    }
    get unreadCount() {
        return this.props.record.data.casafolino_unread_mail_count || 0;
    }
    get noActivityWarning() {
        return this.props.record.data.casafolino_no_activity_warning;
    }
    get daysSinceLastActivity() {
        return this.props.record.data.casafolino_days_since_last_activity || 0;
    }
    get fairTagName() {
        const tag = this.props.record.data.casafolino_origin_fair_tag_id;
        return tag ? tag[1] : "";
    }
}

registry.category("fields").add("cf_signals_badges", {
    component: CfSignalsBadges,
    supportedTypes: ["selection"],
});
