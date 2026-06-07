/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

class CfHaccpDashboard extends Component {
    static template = "casafolino_haccp.CfHaccpDashboard";
    static props = ["*"];

    setup() {
        this.state = useState({
            data: null,
            loading: true,
            error: null,
            lotSearchQuery: "",
            lotSearchLoading: false,
            lotSearchError: null,
            lotSearchResult: null,
        });
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
            this.state.data = this._normalizeData(result);
        } catch (e) {
            this.state.error = "Errore caricamento dati HACCP.";
        } finally {
            this.state.loading = false;
        }
    }

    _normalizeData(data) {
        return {
            active_quarantine_rows: [],
            active_quarantines: 0,
            audit_alerts: 0,
            docs_expired: 0,
            docs_expiring: 0,
            instruments_expired: 0,
            instruments_expiring: 0,
            nc_action: 0,
            nc_analysis: 0,
            nc_closed: 0,
            nc_critical_open: 0,
            nc_open: 0,
            overall_state: "green",
            production_blocked: 0,
            production_pending: 0,
            receipt_blocked: 0,
            receipt_pending: 0,
            recent_traces: [],
            san_missing_today: 0,
            temp_ko_today: 0,
            temp_pending_today: 0,
            trace_coverage: 0,
            trace_ready_score: 0,
            trace_recall_tested: 0,
            trace_with_customer: 0,
            traced_lots: 0,
            ...(data || {}),
        };
    }

    onRefresh() {
        this.state.loading = true;
        this._load();
    }

    async onLotSearch(ev) {
        if (ev) {
            ev.preventDefault();
        }
        const query = (this.state.lotSearchQuery || "").trim();
        if (!query) {
            this.state.lotSearchResult = null;
            this.state.lotSearchError = "Inserisci barcode, SKU o lotto.";
            return;
        }
        this.state.lotSearchLoading = true;
        this.state.lotSearchError = null;
        try {
            const result = await rpc("/web/dataset/call_kw", {
                model: "cf.haccp.nc",
                method: "dashboard_lot_search",
                args: [query],
                kwargs: {},
            });
            this.state.lotSearchResult = result;
        } catch (e) {
            this.state.lotSearchError = "Ricerca lotto non riuscita.";
        } finally {
            this.state.lotSearchLoading = false;
        }
    }

    async onLotDrill(ev) {
        const query = ev.currentTarget.dataset.query;
        if (!query) {
            return;
        }
        this.state.lotSearchQuery = query;
        await this.onLotSearch();
    }

    onLotSearchInput(ev) {
        this.state.lotSearchQuery = ev.target.value;
        if (!this.state.lotSearchQuery) {
            this.state.lotSearchResult = null;
            this.state.lotSearchError = null;
        }
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

    onOpenReceiptPending() {
        this._openModel("stock.picking", [["picking_type_code", "=", "incoming"], ["haccp_state", "=", "pending"]], "Ricezioni HACCP da completare");
    }

    onOpenReceiptBlocked() {
        this._openModel("stock.picking", [["picking_type_code", "=", "incoming"], ["haccp_esito", "in", ["quarantena", "rifiutato"]]], "Ricezioni bloccate");
    }

    onOpenProductionPending() {
        this._openModel("mrp.production", [["haccp_state", "=", "pending"]], "Produzioni HACCP da completare");
    }

    onOpenProductionBlocked() {
        this._openModel("mrp.production", [["haccp_esito", "in", ["non_conforme", "bloccato", "attesa_analisi"]]], "Produzioni bloccate");
    }

    onOpenTraceability() {
        this._openModel("cf.haccp.tracciabilita", [], "Tracciabilita lotti");
    }

    onOpenQuarantine() {
        this._openModel("cf.haccp.quarantine", [["state", "=", "active"]], "Quarantene attive");
    }

    onOpenTemperatureToday() {
        this._openModel("cf.haccp.temperature.log", [["esito", "in", ["pending", "ko"]]], "Registro temperature");
    }

    onOpenSanificationToday() {
        this._openModel("cf.haccp.sanification.log", [["eseguita", "=", false]], "Sanificazioni da completare");
    }

    onOpenCcpKo() {
        this._openModel("cf.haccp.ccp.log", [["esito", "=", "fuori_limite"]], "CCP fuori limite");
    }

    async _openModel(model, domain, name = null) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: name || model,
            res_model: model,
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            context: {},
        });
    }
}

registry.category("actions").add("cf_haccp_dashboard", CfHaccpDashboard);
