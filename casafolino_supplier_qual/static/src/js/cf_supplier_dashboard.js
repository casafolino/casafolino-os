/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

class CfSupplierDashboard extends Component {
    static template = "casafolino_supplier_qual.CfSupplierDashboard";
    static props = {};

    setup() {
        this.state = useState({ data: null, loading: true, error: null });
        this.action = useService("action");
        onWillStart(async () => { await this._load(); });
    }

    async _load() {
        try {
            this.state.data = await rpc("/web/dataset/call_kw", {
                model: "casafolino.supplier.qualification",
                method: "get_dashboard_data",
                args: [], kwargs: {},
            });
        } catch (e) {
            this.state.error = "Errore caricamento dati fornitori.";
        } finally {
            this.state.loading = false;
        }
    }

    onRefresh() { this.state.loading = true; this._load(); }

    onOpenApproved() { this._open([["status", "=", "approved"]]); }
    onOpenEvaluation() { this._open([["status", "=", "evaluation"]]); }
    onOpenSuspended() { this._open([["status", "in", ["suspended", "excluded"]]]); }
    onOpenRed() { this._open([["traffic_light", "=", "red"]]); }
    onOpenDocsExpiring() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Documenti in scadenza",
            res_model: "casafolino.supplier.document",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["doc_status", "in", ["expiring", "expired"]]],
            context: {},
        });
    }

    async _open(domain) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Fornitori",
            res_model: "casafolino.supplier.qualification",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            context: {},
        });
    }
}

registry.category("actions").add("cf_supplier_dashboard", CfSupplierDashboard);
