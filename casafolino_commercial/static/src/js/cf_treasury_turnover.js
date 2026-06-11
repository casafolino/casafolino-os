/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

class CfTreasuryTurnover extends Component {
    static template = "casafolino_treasury.CfTreasuryTurnover";
    static props = ["*"];

    setup() {
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        this.state = useState({
            data: null,
            loading: true,
            error: null,
            dateFrom: this._toInputDate(firstDay),
            dateTo: this._toInputDate(today),
        });
        onWillStart(async () => { await this._load(); });
    }

    _toInputDate(dateObj) {
        const year = dateObj.getFullYear();
        const month = String(dateObj.getMonth() + 1).padStart(2, "0");
        const day = String(dateObj.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    async _load() {
        this.state.loading = true;
        this.state.error = null;
        try {
            this.state.data = await rpc("/web/dataset/call_kw", {
                model: "cf.treasury.snapshot",
                method: "get_period_turnover_expense_analysis",
                args: [this.state.dateFrom, this.state.dateTo],
                kwargs: {},
            });
        } catch (e) {
            this.state.error = "Errore caricamento fatturato e spese.";
        } finally {
            this.state.loading = false;
        }
    }

    onDateFrom(ev) {
        this.state.dateFrom = ev.target.value;
    }

    onDateTo(ev) {
        this.state.dateTo = ev.target.value;
    }

    onApply() {
        this._load();
    }

    onPresetMonth() {
        this.onPreset("month");
    }

    onPresetQuarter() {
        this.onPreset(90);
    }

    onPresetYear() {
        this.onPreset("year");
    }

    onPreset(days) {
        const today = new Date();
        let start;
        if (days === "month") {
            start = new Date(today.getFullYear(), today.getMonth(), 1);
        } else if (days === "year") {
            start = new Date(today.getFullYear(), 0, 1);
        } else {
            start = new Date(today);
            start.setDate(start.getDate() - Number(days) + 1);
        }
        this.state.dateFrom = this._toInputDate(start);
        this.state.dateTo = this._toInputDate(today);
        this._load();
    }

    formatAmount(val) {
        const value = val || 0;
        const abs = Math.abs(value);
        const sign = value < 0 ? "-" : "";
        return sign + new Intl.NumberFormat("it-IT", {
            style: "currency",
            currency: "EUR",
            maximumFractionDigits: abs >= 1000 ? 0 : 2,
        }).format(abs);
    }

    deltaClass(item, inverse = false) {
        const up = inverse ? !item.up : item.up;
        return up ? "text-success" : "text-danger";
    }

    deltaSymbol(item) {
        return item.delta >= 0 ? "+" : "";
    }
}

registry.category("actions").add("cf_treasury_turnover", CfTreasuryTurnover);
