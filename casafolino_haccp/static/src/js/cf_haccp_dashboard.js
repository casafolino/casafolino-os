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
            lotSearchExpanded: false,
            recallCreatingLotId: null,
            recallCreated: null,
            inlineDetail: null,
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
            this.state.lotSearchExpanded = false;
            this.state.recallCreated = null;
            this.state.inlineDetail = null;
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

    onShowAllSearch() {
        this.state.lotSearchExpanded = true;
    }

    async onCreateRecall(ev) {
        const lotId = Number(ev.currentTarget.dataset.lotId || 0);
        if (!lotId) {
            return;
        }
        this.state.recallCreatingLotId = lotId;
        this.state.lotSearchError = null;
        try {
            const action = await rpc("/web/dataset/call_kw", {
                model: "cf.haccp.nc",
                method: "dashboard_create_lot_recall",
                args: [lotId],
                kwargs: {},
            });
            if (action && action.error) {
                this.state.lotSearchError = action.error;
                return;
            }
            this.state.recallCreated = action;
            this.state.inlineDetail = {
                type: "Richiamo creato",
                title: action.reference,
                subtitle: action.summary || "Sessione richiamo creata.",
                model: action.model,
                resId: action.id,
            };
        } catch (e) {
            this.state.lotSearchError = "Creazione richiamo non riuscita.";
        } finally {
            this.state.recallCreatingLotId = null;
        }
    }

    onInspectItem(ev) {
        this.state.inlineDetail = {
            type: ev.currentTarget.dataset.kind || "Dettaglio",
            title: ev.currentTarget.dataset.title || "Dettaglio",
            subtitle: ev.currentTarget.dataset.subtitle || "",
            model: ev.currentTarget.dataset.model || "",
            resId: Number(ev.currentTarget.dataset.resId || 0),
        };
    }

    async onOpenInlineDetailInOdoo() {
        const detail = this.state.inlineDetail || {};
        const model = detail.model;
        const resId = Number(detail.resId || 0);
        if (!model || !resId) {
            return;
        }
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: detail.title || "Dettaglio",
            res_model: model,
            res_id: resId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    visibleSearchItems(items) {
        const values = items || [];
        return this.state.lotSearchExpanded ? values : values.slice(0, 6);
    }

    hiddenSearchCount(items) {
        const values = items || [];
        return this.state.lotSearchExpanded ? 0 : Math.max(values.length - 6, 0);
    }

    onLotSearchInput(ev) {
        this.state.lotSearchQuery = ev.target.value;
        if (!this.state.lotSearchQuery) {
            this.state.lotSearchResult = null;
            this.state.lotSearchError = null;
            this.state.lotSearchExpanded = false;
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
