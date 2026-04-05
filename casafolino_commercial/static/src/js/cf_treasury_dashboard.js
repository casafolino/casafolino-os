/** @odoo-module **/
import {
    Component,
    useState,
    onMounted,
    onWillStart,
    onWillUnmount,
    onPatched,
    useRef,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
// Chart.js caricato come UMD via CDN nel manifest — disponibile come window.Chart

// Data di oggi (stringa ISO) — costante per tutta la sessione
const TODAY_STR = new Date().toISOString().split("T")[0];

function addDays(isoDate, n) {
    const d = new Date(isoDate);
    d.setDate(d.getDate() + n);
    return d.toISOString().split("T")[0];
}

class CfTreasuryDashboard extends Component {
    static template = "casafolino_treasury.CfTreasuryDashboard";
    static props = ["*"];

    setup() {
        this.state = useState({
            data: null,
            loading: true,
            error: null,
            invoices: [],
            bills: [],
            agingLoading: true,
        });

        this.chartRef = useRef("cashflowChart");
        this._chart = null;
        this._chartHash = null;

        onWillStart(async () => {
            await Promise.all([this._load(), this._loadAging()]);
        });

        onMounted(() => {
            this._renderChart();
        });

        onPatched(() => {
            this._renderChart();
        });

        onWillUnmount(() => {
            if (this._chart) {
                this._chart.destroy();
                this._chart = null;
            }
        });
    }

    // -------------------------------------------------------------------------
    // Data loading
    // -------------------------------------------------------------------------

    async _load() {
        try {
            this.state.data = await rpc("/web/dataset/call_kw", {
                model: "cf.treasury.snapshot",
                method: "get_dashboard_data",
                args: [],
                kwargs: {},
            });
        } catch (e) {
            this.state.error = "Errore caricamento dati tesoreria.";
        } finally {
            this.state.loading = false;
        }
    }

    async _loadAging() {
        try {
            const d90 = addDays(TODAY_STR, 90);
            const [invoices, bills] = await Promise.all([
                rpc("/web/dataset/call_kw", {
                    model: "account.move",
                    method: "search_read",
                    args: [[
                        ["move_type", "=", "out_invoice"],
                        ["state", "=", "posted"],
                        ["payment_state", "not in", ["paid", "in_payment"]],
                        ["invoice_date_due", "<=", d90],
                    ]],
                    kwargs: {
                        fields: ["name", "partner_id", "invoice_date_due", "amount_residual"],
                        order: "invoice_date_due asc",
                        limit: 60,
                    },
                }),
                rpc("/web/dataset/call_kw", {
                    model: "account.move",
                    method: "search_read",
                    args: [[
                        ["move_type", "=", "in_invoice"],
                        ["state", "=", "posted"],
                        ["payment_state", "not in", ["paid", "in_payment"]],
                        ["invoice_date_due", "<=", d90],
                    ]],
                    kwargs: {
                        fields: ["name", "partner_id", "invoice_date_due", "amount_residual"],
                        order: "invoice_date_due asc",
                        limit: 60,
                    },
                }),
            ]);
            this.state.invoices = invoices;
            this.state.bills = bills;
        } catch (e) {
            // aging è secondario, non blocca il dashboard
        } finally {
            this.state.agingLoading = false;
        }
    }

    onRefresh() {
        this.state.loading = true;
        this.state.agingLoading = true;
        this._chartHash = null;
        if (this._chart) {
            this._chart.destroy();
            this._chart = null;
        }
        Promise.all([this._load(), this._loadAging()]);
    }

    // -------------------------------------------------------------------------
    // Chart.js
    // -------------------------------------------------------------------------

    _renderChart() {
        const canvas = this.chartRef.el;
        if (!canvas) return;
        const d = this.state.data;
        if (!d || !d.has_data || !d.cashflow || !d.cashflow.length) return;

        // Evita ridisegno se i dati non sono cambiati
        const hash = JSON.stringify(d.cashflow);
        if (this._chartHash === hash) return;
        this._chartHash = hash;

        if (this._chart) {
            this._chart.destroy();
            this._chart = null;
        }

        const labels = d.cashflow.map(x => x.month);
        const inflows = d.cashflow.map(x => x.inflow);
        const outflows = d.cashflow.map(x => x.outflow);
        const balances = d.cashflow.map(x => x.balance);

        this._chart = new window.Chart(canvas, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: "Entrate",
                        data: inflows,
                        backgroundColor: "rgba(90,110,58,0.75)",
                        borderColor: "#5A6E3A",
                        borderWidth: 1,
                        borderRadius: 4,
                        order: 2,
                    },
                    {
                        label: "Uscite",
                        data: outflows,
                        backgroundColor: "rgba(239,68,68,0.7)",
                        borderColor: "#ef4444",
                        borderWidth: 1,
                        borderRadius: 4,
                        order: 2,
                    },
                    {
                        label: "Saldo Netto",
                        data: balances,
                        type: "line",
                        borderColor: "#3b82f6",
                        backgroundColor: "rgba(59,130,246,0.08)",
                        borderWidth: 2,
                        pointRadius: 3,
                        pointBackgroundColor: "#3b82f6",
                        fill: false,
                        tension: 0.35,
                        order: 1,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: {
                        position: "top",
                        labels: { font: { size: 11 }, boxWidth: 12 },
                    },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                const v = ctx.parsed.y;
                                if (v === null || v === undefined) return "";
                                const formatted = Math.abs(v) >= 1000
                                    ? (v / 1000).toFixed(1) + "K"
                                    : v.toFixed(0);
                                return " " + ctx.dataset.label + ": € " + formatted;
                            },
                        },
                    },
                },
                scales: {
                    y: {
                        ticks: {
                            font: { size: 10 },
                            callback: function (v) {
                                if (Math.abs(v) >= 1000) return "€" + (v / 1000).toFixed(0) + "K";
                                return "€" + v;
                            },
                        },
                        grid: { color: "rgba(0,0,0,0.06)" },
                    },
                    x: {
                        ticks: { font: { size: 10 } },
                        grid: { display: false },
                    },
                },
            },
        });
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    formatAmount(val) {
        if (val === null || val === undefined) return "€ 0";
        const abs = Math.abs(val);
        const sign = val < 0 ? "-" : "";
        if (abs >= 1_000_000) return sign + "€ " + (abs / 1_000_000).toFixed(2) + "M";
        if (abs >= 1_000) return sign + "€ " + (abs / 1_000).toFixed(1) + "K";
        return sign + "€ " + Math.round(abs);
    }

    runwayColor() {
        const d = this.state.data;
        if (!d) return "#6b7280";
        if (d.runway_days > 30) return "#22c55e";
        if (d.runway_days >= 15) return "#f59e0b";
        return "#ef4444";
    }

    agingDiffDays(dueDateStr) {
        if (!dueDateStr) return -9999;
        const due = new Date(dueDateStr);
        const now = new Date(TODAY_STR);
        return Math.floor((due - now) / 86400000);
    }

    agingLabel(dueDateStr) {
        const diff = this.agingDiffDays(dueDateStr);
        if (diff < 0) return "Scaduto";
        if (diff <= 30) return "0-30 gg";
        if (diff <= 60) return "31-60 gg";
        return "61-90 gg";
    }

    agingBadgeClass(dueDateStr) {
        const diff = this.agingDiffDays(dueDateStr);
        if (diff < 0) return "bg-danger";
        if (diff <= 30) return "bg-warning text-dark";
        if (diff <= 60) return "bg-info text-dark";
        return "bg-secondary";
    }
}

registry.category("actions").add("cf_treasury_dashboard", CfTreasuryDashboard);
