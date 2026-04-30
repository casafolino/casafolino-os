/** @odoo-module **/
import { Component, useEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class LavagnaHeader extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaHeader";
    static props = ["*"];

    setup() {
        this.env = useEnv();
        this.actionService = useService("action");
    }

    backToInitiativesList() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Iniziative",
            res_model: "cf.initiative",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    backToInitiative() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "cf.initiative",
            res_id: this.props.initiative.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    formatDate(isoStr) {
        if (!isoStr) return '';
        return new Date(isoStr).toLocaleDateString('it-IT', {
            day: 'numeric', month: 'short', year: 'numeric',
        });
    }
}
