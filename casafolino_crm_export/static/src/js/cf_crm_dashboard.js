/** @odoo-module **/
// ═══════════════════════════════════════════════════════
//  CasaFolino CRM — Dashboard KPI (OWL 18)
// ═══════════════════════════════════════════════════════
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

class CfCrmDashboard extends Component {
    static template = "casafolino_crm_export.CfCrmDashboard";
    static props = ["*"];

    setup() {
        this.state = useState({ kpis: null, loading: true, error: null });
        this.action = useService("action");
        onWillStart(async () => {
            await this._loadKpis();
        });
    }

    async _loadKpis() {
        try {
            const result = await rpc("/web/dataset/call_kw", {
                model: "cf.export.lead",
                method: "get_dashboard_kpis",
                args: [],
                kwargs: {},
            });
            this.state.kpis = result;
        } catch (e) {
            this.state.error = "Errore nel caricamento KPI.";
        } finally {
            this.state.loading = false;
        }
    }

    // ── Format helpers ──
    formatAmount(val) {
        if (!val) return "€ 0";
        if (val >= 1_000_000) return `€ ${(val / 1_000_000).toFixed(1)}M`;
        if (val >= 1_000) return `€ ${(val / 1_000).toFixed(0)}K`;
        return `€ ${Math.round(val)}`;
    }

    stageBarPct(count) {
        if (!this.state.kpis || !this.state.kpis.total) return 0;
        return Math.round((count / this.state.kpis.total) * 100);
    }

    // ── Navigation handlers ──
    onClickAll() {
        this._openLeads([]);
    }

    onClickRotting() {
        this._openLeads([["rotting_state", "in", ["danger", "dead"]]]);
    }

    onClickFollowup() {
        const today = new Date().toISOString().split("T")[0];
        this._openLeads([["date_next_followup", "<=", today]]);
    }

    onClickScoreHigh() {
        this._openLeads([["lead_score", ">=", 70]]);
    }

    onRefresh() {
        this.state.loading = true;
        this._loadKpis();
    }

    async _openLeads(domain) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Trattative",
            res_model: "cf.export.lead",
            view_mode: "kanban,list,form",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: domain,
            context: {},
        });
    }
}

registry.category("actions").add("cf_crm_dashboard", CfCrmDashboard);
