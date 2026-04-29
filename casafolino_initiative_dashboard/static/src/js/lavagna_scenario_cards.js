/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class LavagnaScenarioCards extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaScenarioCards";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ scenarios: [], loading: true });

        onWillStart(() => this.loadScenarios());

        // Reload when record changes (family_id change triggers re-render)
        onWillUpdateProps(() => this.loadScenarios());
    }

    async loadScenarios() {
        const familyData = this.props.record.data.family_id;
        if (!familyData || !familyData[0]) {
            this.state.scenarios = [];
            this.state.loading = false;
            return;
        }
        this.state.loading = true;
        const scenarios = await this.orm.searchRead(
            "casafolino.lavagna.template",
            [
                ["family_id", "=", familyData[0]],
                ["active", "=", true],
            ],
            ["id", "name", "description", "suggested_stage_names", "default_panels"],
            { order: "sequence, id" }
        );
        this.state.scenarios = scenarios;
        this.state.loading = false;
    }

    selectScenario(scenarioId) {
        this.props.record.update({ [this.props.name]: [scenarioId, ""] });
    }

    isSelected(scenarioId) {
        const value = this.props.record.data[this.props.name];
        return value && value[0] === scenarioId;
    }

    parseStages(csv) {
        if (!csv) return [];
        return csv.split(",").map((s) => s.trim()).filter(Boolean);
    }
}

registry.category("fields").add("lavagna_scenario_cards", {
    component: LavagnaScenarioCards,
    supportedTypes: ["many2one"],
});
