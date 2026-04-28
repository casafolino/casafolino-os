/** @odoo-module **/
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class WorkspaceQuickActions extends Component {
    static template = "casafolino_workspace.QuickActions";
    static props = ["*"];

    setup() {
        this.action = useService("action");
    }

    openLead() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            views: [[false, "form"]],
            target: "new",
            context: { default_type: "lead" },
        });
    }

    openOpportunity() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            views: [[false, "form"]],
            target: "new",
            context: { default_type: "opportunity" },
        });
    }

    openMeeting() {
        const start = new Date(Date.now() + 60 * 60 * 1000);
        const startStr = start.toISOString().slice(0, 19).replace("T", " ");
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "calendar.event",
            views: [[false, "form"]],
            target: "new",
            context: { default_start: startStr, default_duration: 1.0 },
        });
    }

    openContact() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            views: [[false, "form"]],
            target: "new",
            context: { default_company_type: "company" },
        });
    }

    openProject() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "project.project",
            views: [[false, "form"]],
            target: "new",
        });
    }
}
