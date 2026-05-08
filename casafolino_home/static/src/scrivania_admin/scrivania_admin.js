/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class CFScrivaniaAdmin extends Component {
    static template = "casafolino_home.CFScrivaniaAdmin";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            isLoading: true,
            kpi: {
                cassa_qonto: null,
                cassa_revolut: null,
                cassa_bcc: null,
                fatture_aperte: null,
                prossima_fiera: null,
                currency: "€",
            },
        });

        onWillStart(async () => {
            await this._loadKpi();
        });
    }

    async _loadKpi() {
        this.state.isLoading = true;
        try {
            const result = await this.orm.call("cf.home.kpi", "cf_get_kpi_admin", []);
            Object.assign(this.state.kpi, result);
        } catch (err) {
            console.warn("KPI admin load failed:", err);
        } finally {
            this.state.isLoading = false;
        }
    }

    formatKpi(value, type) {
        if (value === null || value === undefined) return "\u2014";
        if (type === "currency") {
            const k = Math.round(value / 1000);
            return this.state.kpi.currency + k + "k";
        }
        if (type === "text") return String(value);
        return String(Math.round(value));
    }

    // === Quick actions ===

    async onNewInvoice() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            views: [[false, "form"]],
            target: "current",
            context: { default_move_type: "out_invoice" },
        });
    }

    async onNewBankMove() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.bank.statement",
            views: [[false, "form"]],
            target: "current",
        });
    }

    async onOpenDocumenti() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "ir.attachment",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            name: "Documenti",
        });
    }

    async onOpenCalendario() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "calendar.event",
            views: [[false, "calendar"], [false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async onNewFiera() {
        try {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "cf.export.fair",
                views: [[false, "form"]],
                target: "current",
            });
        } catch {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "calendar.event",
                views: [[false, "form"]],
                target: "current",
                context: { default_name: "Fiera - " },
            });
        }
    }

    // === Sezioni ===

    async onOpenTesoreria() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            views: [[false, "list"], [false, "form"]],
            domain: [["move_type", "=", "out_invoice"]],
            target: "current",
            name: "Tesoreria",
        });
    }

    async onOpenDocumentiSection() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "ir.attachment",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            name: "Documenti",
        });
    }

    async onOpenCalendarioSection() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "calendar.event",
            views: [[false, "calendar"], [false, "list"]],
            target: "current",
        });
    }

    async onOpenGDO() {
        try {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "cf.export.fair",
                views: [[false, "list"], [false, "form"]],
                target: "current",
                name: "Fiere & GDO",
            });
        } catch {
            console.warn("GDO/Fair action not available");
        }
    }

    onSwitchCommerciale() {
        this.action.doAction("casafolino_home.action_scrivania_commerciale");
    }

    onSwitchOperativa() {
        this.action.doAction("casafolino_home.action_scrivania_operativa");
    }

    async onRefresh() {
        await this._loadKpi();
    }
}

registry.category("actions").add("cf_scrivania_admin", CFScrivaniaAdmin);
