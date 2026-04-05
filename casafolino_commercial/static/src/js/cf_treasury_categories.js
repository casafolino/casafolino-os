/** @odoo-module **/
import {
    Component, useState, onMounted, onWillStart, onPatched, onWillUnmount, useRef,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

class CfTreasuryCategories extends Component {
    static template = "casafolino_treasury.CfTreasuryCategories";
    static props = ["*"];

    setup() {
        this.state = useState({ data: null, loading: true, error: null, view: "table" });
        this.chartRef = useRef("pieChart");
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
                method: "get_category_analysis",
                args: [],
                kwargs: {},
            });
        } catch (e) {
            this.state.error = "Errore caricamento analisi categorie.";
        } finally {
            this.state.loading = false;
        }
    }

    onRefresh() {
        this._chartHash = null;
        if (this._chart) { this._chart.destroy(); this._chart = null; }
        this._load();
    }

    onViewTable() { this.state.view = "table"; }
    onViewChart() { this.state.view = "chart"; }

    _renderChart() {
        const canvas = this.chartRef.el;
        if (!canvas || !this.state.data || this.state.view !== "chart") return;
        const cats = this.state.data.categories;
        if (!cats || !cats.length) return;

        const hash = JSON.stringify(cats);
        if (this._chartHash === hash) return;
        this._chartHash = hash;
        if (this._chart) { this._chart.destroy(); this._chart = null; }

        const palette = [
            "#5A6E3A","#3b82f6","#f59e0b","#ef4444","#8b5cf6",
            "#06b6d4","#ec4899","#10b981","#f97316","#6366f1",
        ];

        this._chart = new window.Chart(canvas, {
            type: "pie",
            data: {
                labels: cats.map(c => c.name),
                datasets: [{
                    data: cats.map(c => c.amount),
                    backgroundColor: cats.map((_, i) => palette[i % palette.length]),
                    borderWidth: 2,
                    borderColor: "#fff",
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right", labels: { font: { size: 11 }, boxWidth: 14 } },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                const v = ctx.parsed;
                                const f = v >= 1000 ? (v / 1000).toFixed(1) + "K" : v.toFixed(0);
                                return " € " + f;
                            },
                        },
                    },
                },
            },
        });
    }

    formatAmount(val) {
        if (!val && val !== 0) return "€ 0";
        const abs = Math.abs(val);
        const sign = val < 0 ? "-" : "";
        if (abs >= 1_000_000) return sign + "€ " + (abs / 1_000_000).toFixed(2) + "M";
        if (abs >= 1_000) return sign + "€ " + (abs / 1_000).toFixed(1) + "K";
        return sign + "€ " + Math.round(abs);
    }

    yoyArrow(item) { return item.yoy_up ? "↑" : "↓"; }
    yoyClass(item) { return item.yoy_up ? "text-success" : "text-danger"; }
}

registry.category("actions").add("cf_treasury_categories", CfTreasuryCategories);
