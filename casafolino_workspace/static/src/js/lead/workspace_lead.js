/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class WorkspaceLead extends Component {
    static template = "casafolino_workspace.WorkspaceLead";
    static props = ["*"];

    setup() {
        this.state = useState({
            loading: true,
            data: null,
            error: null,
            view: "tutti",
            filter: "tutti",
            leads: [],
            leadsLoading: false,
            pipeline: null,
            markets: null,
            selectedLead: null,
            detailData: null,
        });
        onWillStart(async () => {
            await this._loadAll();
        });
    }

    async _loadAll() {
        try {
            const [data, listData] = await Promise.all([
                rpc("/workspace/lead/data", {}),
                rpc("/workspace/lead/list", { filter_key: "tutti" }),
            ]);
            this.state.data = data;
            this.state.leads = listData.leads || [];
            this.state.loading = false;
        } catch (e) {
            this.state.error = e.message || "Errore";
            this.state.loading = false;
        }
    }

    async onFilterChange(filterKey) {
        this.state.filter = filterKey;
        this.state.leadsLoading = true;
        try {
            const res = await rpc("/workspace/lead/list", { filter_key: filterKey });
            this.state.leads = res.leads || [];
        } catch (e) {
            this.state.leads = [];
        }
        this.state.leadsLoading = false;
    }

    async onViewChange(view) {
        this.state.view = view;
        if (view === "pipeline" && !this.state.pipeline) {
            try {
                const res = await rpc("/workspace/lead/pipeline", {});
                this.state.pipeline = res.stages || [];
            } catch (e) {
                this.state.pipeline = [];
            }
        }
        if (view === "mercati" && !this.state.markets) {
            try {
                const res = await rpc("/workspace/lead/markets", {});
                this.state.markets = res.markets || [];
            } catch (e) {
                this.state.markets = [];
            }
        }
    }

    async onSelectLead(lead) {
        this.state.selectedLead = lead;
        try {
            const res = await rpc("/workspace/lead/detail", { lead_id: lead.id });
            this.state.detailData = res;
        } catch (e) {
            this.state.detailData = null;
        }
    }

    onCloseDetail() {
        this.state.selectedLead = null;
        this.state.detailData = null;
    }

    onGoHome() {
        this.props.onGoHome();
    }

    fmtEuro(val) {
        if (!val) return "€ 0";
        if (Math.abs(val) >= 1000000) return "€ " + (val / 1000000).toFixed(2) + "M";
        if (Math.abs(val) >= 1000) return "€ " + (val / 1000).toFixed(1) + "K";
        return "€ " + Math.round(val);
    }

    getRelativeTime(isoDate) {
        if (!isoDate) return "";
        const now = luxon.DateTime.now();
        const dt = luxon.DateTime.fromISO(isoDate);
        const diff = now.diff(dt, ["days", "hours", "minutes"]);
        if (diff.days >= 1) {
            const d = Math.floor(diff.days);
            return d === 1 ? "ieri" : d + " gg fa";
        }
        if (diff.hours >= 1) return Math.floor(diff.hours) + " h fa";
        return Math.max(1, Math.floor(diff.minutes)) + " min fa";
    }

    getFilterKey(label) {
        const map = {
            "Tutti": "tutti",
            "Caldi": "caldi",
            "Silenti": "silenti",
            "Nuovi sett.": "nuovi",
            "In chiusura": "chiusura",
        };
        return map[label] || "tutti";
    }
}
