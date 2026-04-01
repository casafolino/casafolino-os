/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

class CfHomeDashboard extends Component {
    static template = "casafolino_home.HomeDashboard";

    setup() {
        this.action = useService("action");
        this.state = useState({
            loading: true,
            refreshing: false,
            error: null,
            dateLabel: new Date().toLocaleDateString("it-IT", {
                weekday: "long", day: "numeric", month: "long", year: "numeric",
            }),
            kpis: {
                mail_unread: 0,
                crm_active: 0, crm_rotting: 0, crm_followup_today: 0, crm_forecast: 0,
                haccp_nc_open: 0, haccp_nc_critical: 0,
                treasury_balance: 0,
                kpi_ytd: 0, kpi_mo_open: 0,
                prod_active: 0, prod_in_progress: 0,
                expiring_soon: 0,
            },
        });
        onWillStart(() => this._loadKpis());
    }

    async _loadKpis() {
        try {
            const data = await rpc("/web/dataset/call_kw", {
                model: "cf.home.dashboard",
                method: "get_all_kpis",
                args: [],
                kwargs: {},
            });
            Object.assign(this.state.kpis, data);
        } catch (e) {
            this.state.error = "Errore caricamento KPI: " + (e.message || String(e));
        } finally {
            this.state.loading = false;
            this.state.refreshing = false;
        }
    }

    async onRefresh() {
        this.state.refreshing = true;
        this.state.error = null;
        await this._loadKpis();
    }

    formatCurrency(val) {
        if (!val && val !== 0) return "—";
        const n = Number(val);
        if (Math.abs(n) >= 1000000) return (n / 1000000).toFixed(1) + "M";
        if (Math.abs(n) >= 1000) return (n / 1000).toFixed(1) + "k";
        return n.toFixed(0);
    }

    _doAction(model, name, domain = [], viewMode = "kanban,list,form", views = [[false, "kanban"], [false, "list"], [false, "form"]]) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: model,
            view_mode: viewMode,
            views,
            domain,
            context: {},
        });
    }

    onOpenMail() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "cf_mail_client",
        });
    }

    onOpenCrm() {
        this._doAction("cf.export.lead", "Pipeline Export");
    }

    onOpenFollowup() {
        const today = new Date().toISOString().slice(0, 10);
        this._doAction("cf.export.lead", "Follow-up Oggi",
            [["date_next_followup", "<=", today]]);
    }

    onOpenHaccp() {
        this._doAction("cf.haccp.nc", "Non Conformità HACCP",
            [["state", "not in", ["closed", "cancelled"]]]);
    }

    onOpenTreasury() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "cf_treasury_dashboard",
        });
    }

    onOpenProduction() {
        this._doAction("cf.production.job", "Commesse Produzione",
            [["state", "in", ["confirmed", "in_progress"]]]);
    }

    onOpenKpi() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "cf_kpi_dashboard",
        });
    }

    onOpenExpiring() {
        this._doAction("cf.haccp.instrument", "Strumenti in Scadenza",
            [], "list,form", [[false, "list"], [false, "form"]]);
    }
}

registry.category("actions").add("cf_home_dashboard", CfHomeDashboard);
