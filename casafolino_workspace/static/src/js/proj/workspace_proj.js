/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class WorkspaceProj extends Component {
    static template = "casafolino_workspace.WorkspaceProj";
    static props = ["*"];

    setup() {
        this.state = useState({
            loading: true,
            data: null,
            error: null,
            view: "tutti",
            filter: "tutti",
            projects: [],
            projLoading: false,
            kanban: null,
            timeline: null,
            selectedProj: null,
            detailData: null,
        });
        onWillStart(async () => {
            await this._loadAll();
        });
    }

    async _loadAll() {
        try {
            const [data, listData] = await Promise.all([
                rpc("/workspace/proj/data", {}),
                rpc("/workspace/proj/list", { filter_key: "tutti" }),
            ]);
            this.state.data = data;
            this.state.projects = listData.projects || [];
            this.state.loading = false;
        } catch (e) {
            this.state.error = e.message || "Errore";
            this.state.loading = false;
        }
    }

    async onFilterChange(filterKey) {
        this.state.filter = filterKey;
        this.state.projLoading = true;
        try {
            const res = await rpc("/workspace/proj/list", { filter_key: filterKey });
            this.state.projects = res.projects || [];
        } catch (e) {
            this.state.projects = [];
        }
        this.state.projLoading = false;
    }

    async onViewChange(view) {
        this.state.view = view;
        if (view === "lavagna" && !this.state.kanban) {
            try {
                const res = await rpc("/workspace/proj/kanban", {});
                this.state.kanban = res.columns || [];
            } catch (e) {
                this.state.kanban = [];
            }
        }
        if (view === "timeline" && !this.state.timeline) {
            try {
                const res = await rpc("/workspace/proj/timeline", {});
                this.state.timeline = res.timeline || [];
            } catch (e) {
                this.state.timeline = [];
            }
        }
    }

    async onSelectProj(proj) {
        this.state.selectedProj = proj;
        try {
            const res = await rpc("/workspace/proj/detail", { proj_id: proj.id });
            this.state.detailData = res;
        } catch (e) {
            this.state.detailData = null;
        }
    }

    onCloseDetail() {
        this.state.selectedProj = null;
        this.state.detailData = null;
    }

    onGoHome() {
        this.props.onGoHome();
    }

    getFilterKey(label) {
        const map = {
            "Tutti": "tutti", "Critici": "critici", "In scadenza": "scadenza",
            "Solo i miei": "miei", "Bloccati": "bloccati",
        };
        return map[label] || "tutti";
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
}
