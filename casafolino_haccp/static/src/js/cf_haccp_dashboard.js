/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

class CfHaccpDashboard extends Component {
    static template = "casafolino_haccp.CfHaccpDashboard";
    static props = ["*"];

    setup() {
        this.state = useState({ data: null, loading: true, error: null });
        this.action = useService("action");
        onWillStart(async () => { await this._load(); });
    }

    async _load() {
        try {
            const result = await rpc("/web/dataset/call_kw", {
                model: "cf.haccp.nc",
                method: "get_dashboard_data",
                args: [],
                kwargs: {},
            });
            this.state.data = result;
        } catch (e) {
            this.state.error = "Errore caricamento dati HACCP.";
        } finally {
            this.state.loading = false;
        }
    }

    onRefresh() {
        this.state.loading = true;
        this._load();
    }

    onOpenNcOpen() {
        this._openModel("cf.haccp.nc", [["state", "=", "open"]]);
    }

    onOpenNcCritical() {
        this._openModel("cf.haccp.nc", [["state", "not in", ["closed", "cancelled"]], ["severity", "in", ["high", "critical"]]]);
    }

    onOpenCalibExpired() {
        this._openModel("cf.haccp.calibration", [["state", "=", "expired"]]);
    }

    onOpenCalibExpiring() {
        this._openModel("cf.haccp.calibration", [["state", "in", ["expiring", "expired"]]]);
    }

    onOpenDocsExpiring() {
        this._openModel("cf.haccp.document", [["state", "in", ["expiring", "expired"]]]);
    }

    async _openModel(model, domain) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: model,
            res_model: model,
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            context: {},
        });
    }
}

registry.category("actions").add("cf_haccp_dashboard", CfHaccpDashboard);
