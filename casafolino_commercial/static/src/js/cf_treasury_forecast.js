/** @odoo-module **/
import { Component, useState, onMounted, onWillStart, onPatched, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

class CfTreasuryForecast extends Component {
    static template = "casafolino_treasury.CfTreasuryForecast";
    static props = ["*"];

    setup() {
        this.state = useState({
            data: null,
            loading: true,
            error: null,
            optPct: 15,
            pesPctIn: 25,
            pesPctOut: 10,
        });
        this.chartRef = useRef("forecastChart");
        this._chart = null;
        this._chartHash = null;

        onWillStart(async () => { await this._load(); });
        onMounted(() => { this._renderChart(); });
        onPatched(() => { this._renderChart(); });
        onWillUnmount(() => {
            if (this._chart) { this._chart.destroy(); this._chart = null; }
        });
    }

    async _load() {
        this.state.loading = true;
        try {
            this.state.data = await rpc("/web/dataset/call_kw", {
                model: "cf.treasury.snapshot",
                method: "get_forecast_data",
                args: [],
                kwargs: {
                    opt_pct: this.state.optPct,
                    pes_pct_in: this.state.pesPctIn,
                    pes_pct_out: this.state.pesPctOut,
                },
            });
        } catch (e) {
            this.state.error = "Errore caricamento forecast.";
        } finally {
            this.state.loading = false;
        }
    }

    onRefresh() {
        this._chartHash = null;
        if (this._chart) { this._chart.destroy(); this._chart = null; }
        this._load();
    }

    onOptPctChange(ev) {
        this.state.optPct = parseFloat(ev.target.value) || 15;
    }

    onPesPctInChange(ev) {
        this.state.pesPctIn = parseFloat(ev.target.value) || 25;
    }

    onPesPctOutChange(ev) {
        this.state.pesPctOut = parseFloat(ev.target.value) || 10;
    }

    onApplyScenarios() {
        this._chartHash = null;
        if (this._chart) { this._chart.destroy(); this._chart = null; }
        this._load();
    }

    _renderChart() {
        const canvas = this.chartRef.el;
        if (!canvas || !this.state.data) return;
        const pts = this.state.data.chart_points;
        if (!pts || !pts.length) return;

        const hash = JSON.stringify(pts);
        if (this._chartHash === hash) return;
        this._chartHash = hash;
        if (this._chart) { this._chart.destroy(); this._chart = null; }

        this._chart = new window.Chart(canvas, {
            type: "line",
            data: {
                labels: pts.map(p => p.label),
                datasets: [
                    {
                        label: "Base",
                        data: pts.map(p => p.base),
                        borderColor: "#3b82f6",
                        backgroundColor: "rgba(59,130,246,0.08)",
                        borderWidth: 2,
                        pointRadius: 5,
                        fill: false,
                        tension: 0.3,
                    },
                    {
                        label: "Ottimistico",
                        data: pts.map(p => p.opt),
                        borderColor: "#22c55e",
                        backgroundColor: "rgba(34,197,94,0.08)",
                        borderWidth: 2,
                        borderDash: [6, 3],
                        pointRadius: 4,
                        fill: false,
                        tension: 0.3,
                    },
                    {
                        label: "Pessimistico",
                        data: pts.map(p => p.pes),
                        borderColor: "#ef4444",
                        backgroundColor: "rgba(239,68,68,0.08)",
                        borderWidth: 2,
                        borderDash: [4, 4],
                        pointRadius: 4,
                        fill: false,
                        tension: 0.3,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "top", labels: { font: { size: 11 }, boxWidth: 14 } },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                const v = ctx.parsed.y;
                                const f = Math.abs(v) >= 1000 ? (v / 1000).toFixed(1) + "K" : v.toFixed(0);
                                return " " + ctx.dataset.label + ": € " + f;
                            },
                        },
                    },
                },
                scales: {
                    y: {
                        ticks: {
                            font: { size: 10 },
                            callback: function (v) {
                                return "€" + (Math.abs(v) >= 1000 ? (v / 1000).toFixed(0) + "K" : v);
                            },
                        },
                        grid: { color: "rgba(0,0,0,0.06)" },
                    },
                    x: { ticks: { font: { size: 10 } }, grid: { display: false } },
                },
            },
        });
    }

    formatAmount(val) {
        if (val === null || val === undefined) return "€ 0";
        const abs = Math.abs(val);
        const sign = val < 0 ? "-" : "";
        if (abs >= 1_000_000) return sign + "€ " + (abs / 1_000_000).toFixed(2) + "M";
        if (abs >= 1_000) return sign + "€ " + (abs / 1_000).toFixed(1) + "K";
        return sign + "€ " + Math.round(abs);
    }

    deltaArrow(delta) {
        return delta && delta.up ? "↑" : "↓";
    }

    deltaClass(delta) {
        return delta && delta.up ? "text-success" : "text-danger";
    }
}

registry.category("actions").add("cf_treasury_forecast", CfTreasuryForecast);
