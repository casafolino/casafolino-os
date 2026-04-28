/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class WorkspaceCal extends Component {
    static template = "casafolino_workspace.WorkspaceCal";
    static props = ["*"];

    setup() {
        this.state = useState({
            loading: true, data: null, error: null,
            view: "giorno",
            dayData: null, weekData: null, monthData: null,
            currentDate: null, currentWeekStart: null, currentMonthStart: null,
            selectedEvent: null, detailData: null,
        });
        onWillStart(async () => { await this._loadAll(); });
    }

    async _loadAll() {
        try {
            const [data, dayData] = await Promise.all([
                rpc("/workspace/cal/data", {}),
                rpc("/workspace/cal/day", {}),
            ]);
            this.state.data = data;
            this.state.dayData = dayData;
            this.state.currentDate = dayData.date;
            this.state.loading = false;
        } catch (e) {
            this.state.error = e.message || "Errore";
            this.state.loading = false;
        }
    }

    async onViewChange(v) {
        this.state.view = v;
        if (v === "settimana" && !this.state.weekData) {
            try {
                const res = await rpc("/workspace/cal/week", {});
                this.state.weekData = res;
                this.state.currentWeekStart = res.week_start;
            } catch (e) { this.state.weekData = {days: []}; }
        }
        if (v === "mese" && !this.state.monthData) {
            try {
                const res = await rpc("/workspace/cal/month", {});
                this.state.monthData = res;
                this.state.currentMonthStart = res.month_start;
            } catch (e) { this.state.monthData = {weeks: []}; }
        }
    }

    async onDayNav(delta) {
        const d = new Date(this.state.currentDate);
        d.setDate(d.getDate() + delta);
        const ds = d.toISOString().split("T")[0];
        try {
            const res = await rpc("/workspace/cal/day", { date: ds });
            this.state.dayData = res;
            this.state.currentDate = res.date;
        } catch (e) {}
    }

    async onWeekNav(delta) {
        const d = new Date(this.state.currentWeekStart);
        d.setDate(d.getDate() + delta * 7);
        const ds = d.toISOString().split("T")[0];
        try {
            const res = await rpc("/workspace/cal/week", { week_start: ds });
            this.state.weekData = res;
            this.state.currentWeekStart = res.week_start;
        } catch (e) {}
    }

    async onMonthNav(delta) {
        const d = new Date(this.state.currentMonthStart);
        d.setMonth(d.getMonth() + delta);
        const ds = d.toISOString().split("T")[0].substring(0, 8) + "01";
        try {
            const res = await rpc("/workspace/cal/month", { month_start: ds });
            this.state.monthData = res;
            this.state.currentMonthStart = res.month_start;
        } catch (e) {}
    }

    async onSelectEvent(ev) {
        this.state.selectedEvent = ev;
        try {
            const res = await rpc("/workspace/cal/detail", { event_id: ev.id });
            this.state.detailData = res;
        } catch (e) { this.state.detailData = null; }
    }

    onCloseDetail() { this.state.selectedEvent = null; this.state.detailData = null; }
    onGoHome() { this.props.onGoHome(); }

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
