/** @odoo-module **/
import {
    Component, useState, onMounted, onWillStart, onPatched, onWillUnmount, useRef,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

class CfTreasuryCostsRevenue extends Component {
    static template = "casafolino_treasury.CfTreasuryCostsRevenue";
    static props = ["*"];

    setup() {
        this.state = useState({ data: null, loading: true, error: null });
        this.costChartRef = useRef("costChart");
        this.revenueChartRef = useRef("revenueChart");
        this._costChart = null;
        this._revenueChart = null;
        this._chartHash = null;

        onWillStart(async () => { await this._load(); });
        onMounted(() => { this._renderCharts(); });
        onPatched(() => { this._renderCharts(); });
        onWillUnmount(() => {
            if (this._costChart) this._costChart.destroy();
            if (this._revenueChart) this._revenueChart.destroy();
        });
    }

    async _load() {
        this.state.loading = true;
        try {
            this.state.data = await rpc("/web/dataset/call_kw", {
                model: "cf.treasury.snapshot",
                method: "get_cost_revenue_dashboard",
                args: [],
                kwargs: {},
            });
        } catch (e) {
            this.state.error = "Errore caricamento costi e ricavi.";
        } finally {
            this.state.loading = false;
        }
    }

    onRefresh() {
        this._chartHash = null;
        if (this._costChart) { this._costChart.destroy(); this._costChart = null; }
        if (this._revenueChart) { this._revenueChart.destroy(); this._revenueChart = null; }
        this._load();
    }

    _renderCharts() {
        const d = this.state.data;
        if (!d) return;
        const hash = JSON.stringify({
            revenue: d.revenue,
            centers: d.costs.centers.map(c => [c.id, c.amount_2026_ytd]),
        });
        if (this._chartHash === hash) return;
        this._chartHash = hash;

        const palette = ["#5A6E3A", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#10b981", "#f97316"];

        const revenueCanvas = this.revenueChartRef.el;
        if (revenueCanvas) {
            if (this._revenueChart) this._revenueChart.destroy();
            this._revenueChart = new window.Chart(revenueCanvas, {
                type: "bar",
                data: {
                    labels: [`${d.years.previous} YTD`, `${d.years.current} YTD`, `${d.years.previous} totale`],
                    datasets: [{
                        label: "Ricavi",
                        data: [d.revenue.previous_ytd, d.revenue.current_ytd, d.revenue.previous_full],
                        backgroundColor: ["#94a3b8", "#5A6E3A", "#3b82f6"],
                        borderRadius: 4,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { ticks: { callback: v => this.formatShort(v) }, grid: { color: "rgba(0,0,0,0.06)" } },
                        x: { grid: { display: false } },
                    },
                },
            });
        }

        const costCanvas = this.costChartRef.el;
        if (costCanvas) {
            if (this._costChart) this._costChart.destroy();
            const centers = d.costs.centers.slice(0, 8);
            this._costChart = new window.Chart(costCanvas, {
                type: "doughnut",
                data: {
                    labels: centers.map(c => c.name),
                    datasets: [{
                        data: centers.map(c => c.amount_2026_ytd),
                        backgroundColor: centers.map((_, i) => palette[i % palette.length]),
                        borderColor: "#fff",
                        borderWidth: 2,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: "right", labels: { font: { size: 11 }, boxWidth: 12 } },
                        tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${this.formatAmount(ctx.parsed)}` } },
                    },
                },
            });
        }
    }

    formatShort(val) {
        const abs = Math.abs(val || 0);
        if (abs >= 1_000_000) return "€" + (val / 1_000_000).toFixed(1) + "M";
        if (abs >= 1_000) return "€" + (val / 1_000).toFixed(0) + "K";
        return "€" + Math.round(val || 0);
    }

    formatAmount(val) {
        if (val === null || val === undefined) return "€ 0";
        const abs = Math.abs(val);
        const sign = val < 0 ? "-" : "";
        if (abs >= 1_000_000) return sign + "€ " + (abs / 1_000_000).toFixed(2) + "M";
        if (abs >= 1_000) return sign + "€ " + (abs / 1_000).toFixed(1) + "K";
        return sign + "€ " + Math.round(abs);
    }

    deltaClass(value, expense = false) {
        if (!value) return "text-muted";
        const good = expense ? value <= 0 : value >= 0;
        return good ? "text-success" : "text-danger";
    }

    deltaText(value) {
        if (!value) return "0%";
        return (value > 0 ? "+" : "") + value + "%";
    }
}

registry.category("actions").add("cf_treasury_costs_revenue", CfTreasuryCostsRevenue);
