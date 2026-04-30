/** @odoo-module **/
import { Component, useEnv } from "@odoo/owl";

const SHORT_NAMES = {
    'Task in Scouting': 'Scouting',
    'In Campionatura': 'Camp.',
    'Appuntamenti': 'Appunt.',
    'Incontri': 'Incontri',
    'Lead CRM': 'Lead',
    'Spedizioni Campioni': 'Spediz.',
    'Mail Nuove': 'Mail',
};

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

    getDisplayName(kpi) {
        return SHORT_NAMES[kpi.name] || kpi.name;
    }
}
