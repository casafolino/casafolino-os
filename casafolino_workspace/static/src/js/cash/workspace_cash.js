/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class WorkspaceCash extends Component {
    static template = "casafolino_workspace.WorkspaceCash";
    static props = ["*"];

    setup() {
        this.state = useState({
            loading: true, data: null, error: null,
            view: "conti", filter: "tutte",
            items: [], itemsLoading: false,
            accounts: null,
            selectedItem: null, detailData: null,
        });
        onWillStart(async () => { await this._loadAll(); });
    }

    async _loadAll() {
        try {
            const [data, accounts] = await Promise.all([
                rpc("/workspace/cash/data", {}),
                rpc("/workspace/cash/accounts", {}),
            ]);
            this.state.data = data;
            this.state.accounts = accounts;
            this.state.loading = false;
        } catch (e) {
            this.state.error = e.message || "Errore";
            this.state.loading = false;
        }
    }

    async onViewChange(v) {
        this.state.view = v;
        if (v === "bsl" && this.state.items.length === 0) {
            this.state.itemsLoading = true;
            try {
                const res = await rpc("/workspace/cash/bsl", { filter_key: this.state.filter });
                this.state.items = res.items || [];
            } catch (e) { this.state.items = []; }
            this.state.itemsLoading = false;
        }
        if (v === "fatture") {
            this.state.itemsLoading = true;
            try {
                const res = await rpc("/workspace/cash/invoices", { filter_key: this.state.filter });
                this.state.items = res.items || [];
            } catch (e) { this.state.items = []; }
            this.state.itemsLoading = false;
        }
    }

    async onFilterChange(fk) {
        this.state.filter = fk;
        this.state.itemsLoading = true;
        try {
            if (this.state.view === "bsl") {
                const res = await rpc("/workspace/cash/bsl", { filter_key: fk });
                this.state.items = res.items || [];
            } else if (this.state.view === "fatture") {
                const fmap = {"tutte": "tutte", "qonto": "tutte", "revolut": "tutte", "bcc": "tutte"};
                const res = await rpc("/workspace/cash/invoices", { filter_key: fmap[fk] || "tutte" });
                this.state.items = res.items || [];
            }
        } catch (e) { this.state.items = []; }
        this.state.itemsLoading = false;
    }

    async onSelectItem(item) {
        this.state.selectedItem = item;
        try {
            const res = await rpc("/workspace/cash/detail", { item_type: item.type, item_id: item.item_id || item.id });
            this.state.detailData = res;
        } catch (e) { this.state.detailData = null; }
    }

    onCloseDetail() { this.state.selectedItem = null; this.state.detailData = null; }
    onGoHome() { this.props.onGoHome(); }

    getFilterKey(label) {
        return {"Tutte": "tutte", "Qonto": "qonto", "Revolut": "revolut", "BCC": "bcc"}[label] || "tutte";
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
