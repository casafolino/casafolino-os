/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class CFScrivaniaOperativa extends Component {
    static template = "casafolino_home.CFScrivaniaOperativa";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            isLoading: true,
            kpi: {
                lotti_produzione: null,
                haccp_scadenze: null,
                nc_aperte: null,
                produzioni_attive: null,
                lotti_scadenza: null,
            },
        });

        onWillStart(async () => {
            await this._loadKpi();
        });
    }

    async _loadKpi() {
        this.state.isLoading = true;
        try {
            const result = await this.orm.call("cf.home.kpi", "cf_get_kpi_operativa", []);
            Object.assign(this.state.kpi, result);
        } catch (err) {
            console.warn("KPI operativa load failed:", err);
        } finally {
            this.state.isLoading = false;
        }
    }

    formatKpi(value) {
        if (value === null || value === undefined) return "\u2014";
        return String(Math.round(value));
    }

    // === Quick actions ===

    async onNewLot() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "stock.lot",
            views: [[false, "form"]],
            target: "current",
        });
    }

    async onNewProduction() {
        try {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "mrp.production",
                views: [[false, "form"]],
                target: "current",
            });
        } catch {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "cf.production.job",
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    async onOpenHACCP() {
        try {
            await this.action.doAction("casafolino_haccp.action_cf_haccp_dashboard");
        } catch {
            console.warn("HACCP dashboard not available");
        }
    }

    async onOpenEtichette() {
        try {
            await this.action.doAction("casafolino_labels.action_cf_label_kanban");
        } catch {
            console.warn("Labels action not available");
        }
    }

    async onOpenFornitori() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            views: [[false, "list"], [false, "form"]],
            domain: [["supplier_rank", ">", 0]],
            target: "current",
            name: "Fornitori",
        });
    }

    // === Sezioni ===

    async onOpenProduzione() {
        try {
            await this.action.doAction("casafolino_operations.action_cf_production_jobs");
        } catch {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "stock.lot",
                views: [[false, "list"], [false, "form"]],
                target: "current",
            });
        }
    }

    async onOpenQualita() {
        try {
            await this.action.doAction("casafolino_haccp.action_cf_haccp_nc");
        } catch {
            console.warn("HACCP NC not available");
        }
    }

    async onOpenEtichetteSection() {
        try {
            await this.action.doAction("casafolino_labels.action_cf_label_list");
        } catch {
            console.warn("Labels list not available");
        }
    }

    async onOpenFornitoriSection() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            views: [[false, "list"], [false, "form"]],
            domain: [["supplier_rank", ">", 0]],
            target: "current",
            name: "Fornitori Qualificati",
        });
    }

    onSwitchCommerciale() {
        this.action.doAction("casafolino_home.action_scrivania_commerciale");
    }

    onSwitchAdmin() {
        this.action.doAction("casafolino_home.action_scrivania_admin");
    }

    async onRefresh() {
        await this._loadKpi();
    }
}

registry.category("actions").add("cf_scrivania_operativa", CFScrivaniaOperativa);
