/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

class CfTreasuryClients extends Component {
    static template = "casafolino_treasury.CfTreasuryClients";
    static props = ["*"];

    setup() {
        this.state = useState({ data: null, loading: true, error: null, tab: "revenue" });
        onWillStart(async () => { await this._load(); });
    }

    async _load() {
        this.state.loading = true;
        try {
            this.state.data = await rpc("/web/dataset/call_kw", {
                model: "cf.treasury.snapshot",
                method: "get_client_analysis",
                args: [],
                kwargs: {},
            });
        } catch (e) {
            this.state.error = "Errore caricamento analisi clienti.";
        } finally {
            this.state.loading = false;
        }
    }

    onRefresh() { this._load(); }

    onTabRevenue() { this.state.tab = "revenue"; }
    onTabOverdue() { this.state.tab = "overdue"; }
    onTabDso() { this.state.tab = "dso"; }

    formatAmount(val) {
        if (!val && val !== 0) return "€ 0";
        const abs = Math.abs(val);
        const sign = val < 0 ? "-" : "";
        if (abs >= 1_000_000) return sign + "€ " + (abs / 1_000_000).toFixed(2) + "M";
        if (abs >= 1_000) return sign + "€ " + (abs / 1_000).toFixed(1) + "K";
        return sign + "€ " + Math.round(abs);
    }
}

registry.category("actions").add("cf_treasury_clients", CfTreasuryClients);
