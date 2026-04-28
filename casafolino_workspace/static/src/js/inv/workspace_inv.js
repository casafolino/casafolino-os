/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class WorkspaceInv extends Component {
    static template = "casafolino_workspace.WorkspaceInv";
    static props = ["*"];

    setup() {
        this.state = useState({
            loading: true, data: null, error: null,
            view: "eventi", filter: "tutti",
            items: [], itemsLoading: false,
            comms: null,
            selectedItem: null, detailData: null,
        });
        onWillStart(async () => { await this._loadAll(); });
    }

    async _loadAll() {
        try {
            const [data, events] = await Promise.all([
                rpc("/workspace/inv/data", {}),
                rpc("/workspace/inv/events", { filter_key: "tutti" }),
            ]);
            this.state.data = data;
            this.state.items = events.items || [];
            this.state.loading = false;
        } catch (e) {
            this.state.error = e.message || "Errore";
            this.state.loading = false;
        }
    }

    async onViewChange(v) {
        this.state.view = v;
        if (v === "comunicazioni" && !this.state.comms) {
            this.state.itemsLoading = true;
            try {
                const r = await rpc("/workspace/inv/comms", {});
                this.state.comms = r.items || [];
            } catch (e) { this.state.comms = []; }
            this.state.itemsLoading = false;
        }
    }

    async onFilterChange(fk) {
        this.state.filter = fk;
        this.state.itemsLoading = true;
        try {
            if (this.state.view === "eventi") {
                const res = await rpc("/workspace/inv/events", { filter_key: fk });
                this.state.items = res.items || [];
            }
        } catch (e) { this.state.items = []; }
        this.state.itemsLoading = false;
    }

    async onSelectItem(item) {
        this.state.selectedItem = item;
        try {
            const res = await rpc("/workspace/inv/detail", { item_type: item.type, item_id: item.item_id || item.id });
            this.state.detailData = res;
        } catch (e) { this.state.detailData = null; }
    }

    onCloseDetail() { this.state.selectedItem = null; this.state.detailData = null; }
    onGoHome() { this.props.onGoHome(); }

    getFilterKey(label) {
        return {"Tutti": "tutti", "CdA": "cda", "Crowdfunding": "crowdfunding", "Assemblea": "assemblea"}[label] || "tutti";
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
