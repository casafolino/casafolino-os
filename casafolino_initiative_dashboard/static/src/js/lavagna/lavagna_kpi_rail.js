/** @odoo-module **/
import { Component, useEnv } from "@odoo/owl";

export class LavagnaKpiRail extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaKpiRail";
    static props = ["*"];

    setup() {
        this.env = useEnv();
    }

    onKpiClick(kpi) {
        this.env.actions.filterByKpi(kpi);
    }

    isActive(kpi) {
        const filter = this.env.lavagnaState.kpiFilter;
        return filter && filter.id === kpi.id;
    }
}
