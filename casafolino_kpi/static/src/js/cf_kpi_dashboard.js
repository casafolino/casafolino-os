/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

class CfKpiDashboard extends Component {
    static template = "casafolino_kpi.CfKpiDashboard";
    static props = ["*"];

    setup() {
        this.state = useState({
            data: null,
            loading: true,
            error: null,
            sections: {
                finanza: true,
                vendite: true,
                prodotti: true,
                operations: true,
                qualita: true,
            },
        });
        onWillStart(async () => { await this._load(); });
    }

    async _load() {
        try {
            this.state.data = await rpc("/web/dataset/call_kw", {
                model: "cf.kpi.snapshot",
                method: "get_dashboard_data",
                args: [],
                kwargs: {},
            });
        } catch (e) {
            this.state.error = "Errore caricamento KPI: " + (e.message || e);
        } finally {
            this.state.loading = false;
        }
    }

    onRefresh() {
        this.state.loading = true;
        this._load();
    }

    toggleSection(name) {
        this.state.sections[name] = !this.state.sections[name];
    }

    formatAmount(val) {
        if (!val) return "€ 0";
        if (val >= 1_000_000) return `€ ${(val / 1_000_000).toFixed(2)}M`;
        if (val >= 1_000) return `€ ${(val / 1_000).toFixed(1)}K`;
        return `€ ${Math.round(val)}`;
    }
}

registry.category("actions").add("cf_kpi_dashboard", CfKpiDashboard);
