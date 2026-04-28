/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class LavagnaPlaceholder extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaPlaceholder";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ initiative: null, loading: true });
        onWillStart(async () => {
            const initiativeId = this.props.action.params.initiative_id;
            const [init] = await this.orm.read(
                "cf.initiative",
                [initiativeId],
                ["name", "lavagna_swimlane_category", "lavagna_kpi_ids",
                 "lavagna_task_count", "lavagna_panels", "family_id"]
            );
            this.state.initiative = init;
            this.state.loading = false;
        });
    }

    backToForm() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cf.initiative",
            res_id: this.props.action.params.initiative_id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("casafolino_lavagna", LavagnaPlaceholder);
