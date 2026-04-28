/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class WorkspaceQa extends Component {
    static template = "casafolino_workspace.WorkspaceQa";
    static props = ["*"];

    setup() {
        this.state = useState({
            loading: true, data: null, error: null,
            view: "tutto", filter: "tutto",
            items: [], itemsLoading: false,
            ccps: null, docs: null,
            selectedItem: null, detailData: null,
        });
        onWillStart(async () => { await this._loadAll(); });
    }

    async _loadAll() {
        try {
            const [data, list] = await Promise.all([
                rpc("/workspace/qa/data", {}),
                rpc("/workspace/qa/list", { filter_key: "tutto" }),
            ]);
            this.state.data = data;
            this.state.items = list.items || [];
            this.state.loading = false;
        } catch (e) {
            this.state.error = e.message || "Errore";
            this.state.loading = false;
        }
    }

    async onFilterChange(fk) {
        this.state.filter = fk;
        this.state.itemsLoading = true;
        try {
            const res = await rpc("/workspace/qa/list", { filter_key: fk });
            this.state.items = res.items || [];
        } catch (e) { this.state.items = []; }
        this.state.itemsLoading = false;
    }

    async onViewChange(v) {
        this.state.view = v;
        if (v === "ccp" && !this.state.ccps) {
            try { const r = await rpc("/workspace/qa/ccp", {}); this.state.ccps = r; }
            catch (e) { this.state.ccps = { ccps: [], empty_msg: "Errore caricamento" }; }
        }
        if (v === "docs" && !this.state.docs) {
            try { const r = await rpc("/workspace/qa/docs", {}); this.state.docs = r; }
            catch (e) { this.state.docs = { docs: [], empty_msg: "Errore caricamento" }; }
        }
    }

    async onSelectItem(item) {
        this.state.selectedItem = item;
        try {
            const res = await rpc("/workspace/qa/detail", { item_type: item.type, item_id: item.item_id || item.id });
            this.state.detailData = res;
        } catch (e) { this.state.detailData = null; }
    }

    onCloseDetail() { this.state.selectedItem = null; this.state.detailData = null; }
    onGoHome() { this.props.onGoHome(); }

    getFilterKey(label) {
        return {"Tutto":"tutto","Critici":"critici","NC":"nc","CCP":"ccp","Documenti":"documenti","Lotti":"lotti"}[label] || "tutto";
    }

    getRelativeTime(isoDate) {
        if (!isoDate) return "";
        const now = luxon.DateTime.now();
        const dt = luxon.DateTime.fromISO(isoDate);
        const diff = now.diff(dt, ["days", "hours", "minutes"]);
        if (diff.days >= 1) { const d = Math.floor(diff.days); return d === 1 ? "ieri" : d + " gg fa"; }
        if (diff.hours >= 1) return Math.floor(diff.hours) + " h fa";
        return Math.max(1, Math.floor(diff.minutes)) + " min fa";
    }
}
