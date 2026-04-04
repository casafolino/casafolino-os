/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

class CfTreasuryDashboard extends Component {
    static template = "casafolino_treasury.CfTreasuryDashboard";
    static props = {};

    setup() {
        this.state = useState({ data: null, loading: true, error: null });
        onWillStart(async () => { await this._load(); });
    }

    async _load() {
        try {
            this.state.data = await rpc("/web/dataset/call_kw", {
                model: "cf.treasury.snapshot",
                method: "get_dashboard_data",
                args: [], kwargs: {},
            });
        } catch (e) {
            this.state.error = "Errore caricamento tesoreria.";
        } finally {
            this.state.loading = false;
        }
    }

    onRefresh() { this.state.loading = true; this._load(); }

    formatAmount(val) {
        if (val === null || val === undefined) return "€ 0";
        const abs = Math.abs(val);
        const sign = val < 0 ? "-" : "";
        if (abs >= 1_000_000) return `${sign}€ ${(abs / 1_000_000).toFixed(2)}M`;
        if (abs >= 1_000) return `${sign}€ ${(abs / 1_000).toFixed(1)}K`;
        return `${sign}€ ${Math.round(abs)}`;
    }

    balanceClass(val) {
        if (!val) return "";
        return val > 0 ? "text-success" : "text-danger";
    }

    // Compute bar heights for mini sparkline (0-100% relative)
    sparkBars() {
        const d = this.state.data;
        if (!d || !d.history || !d.history.length) return [];
        const vals = d.history.map(h => h.balance);
        const min = Math.min(...vals);
        const max = Math.max(...vals);
        const range = max - min || 1;
        return d.history.map(h => ({
            date: h.date,
            pct: Math.max(4, Math.round(((h.balance - min) / range) * 100)),
            positive: h.balance >= 0,
        }));
    }
}

registry.category("actions").add("cf_treasury_dashboard", CfTreasuryDashboard);
