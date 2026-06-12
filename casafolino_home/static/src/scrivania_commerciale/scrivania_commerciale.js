/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { registry } from "@web/core/registry";

export class CFScrivaniaCommerciale extends Component {
    static template = "casafolino_home.CFScrivaniaCommerciale";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            isLoading: true,
            kpi: {
                mail_pending: null,
                lead_aperti: null,
                lead_caldi: null,
                progetti_attivi: null,
                sla_scadenza: null,
                fatturato_mese: null,
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
            const result = await this.orm.call("cf.home.kpi", "cf_get_kpi_commerciale", []);
            Object.assign(this.state.kpi, result);
        } catch (err) {
            console.warn("KPI commerciale load failed:", err);
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
        return String(Math.round(value));
    }

    // === Quick actions ===

    async onNewProject() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "project.project",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_cf_status_dossier: "active",
                default_user_id: user.userId,
            },
        });
    }

    async onNewLead() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            views: [[false, "form"]],
            target: "current",
            context: { default_type: "lead", default_user_id: user.userId },
        });
    }

    async onNewContact() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            views: [[false, "form"]],
            target: "current",
        });
    }

    async onOpenPosizionatore() {
        try {
            await this.action.doAction("casafolino_mail.action_mail_v3_client");
        } catch {
            await this.action.doAction({
                type: "ir.actions.client",
                tag: "cf_mail_v3_client",
            });
        }
    }

    async onOpenMiaCasella() {
        try {
            await this.action.doAction("casafolino_mail.action_mail_v3_client");
        } catch {
            await this.action.doAction({
                type: "ir.actions.client",
                tag: "cf_mail_v3_client",
            });
        }
    }

    // === Sezioni ===

    async onOpenPipeline() {
        try {
            await this.action.doAction("casafolino_crm_export.action_cf_crm_all");
        } catch {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "crm.lead",
                views: [[false, "kanban"], [false, "list"], [false, "form"]],
                domain: [["type", "=", "lead"], ["active", "=", true]],
                target: "current",
            });
        }
    }

    async onOpenProjects() {
        try {
            await this.action.doAction("casafolino_crm_export.action_cf_project_dossier");
        } catch {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "project.project",
                views: [[false, "kanban"], [false, "list"], [false, "form"]],
                domain: [["cf_status_dossier", "!=", false]],
                target: "current",
            });
        }
    }

    async onOpenLavagna() {
        try {
            await this.action.doAction("casafolino_initiative_dashboard.action_lavagna_template");
        } catch {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "project.project",
                views: [[false, "kanban"], [false, "list"]],
                target: "current",
            });
        }
    }

    async onOpenAnalytics() {
        try {
            await this.action.doAction("casafolino_pipeline_control.action_cf_pipeline_control");
        } catch {
            await this.onOpenProjects();
        }
    }

    onSwitchOperativa() {
        this.action.doAction("casafolino_home.action_scrivania_operativa");
    }

    onSwitchAdmin() {
        this.action.doAction("casafolino_home.action_scrivania_admin");
    }

    async onRefresh() {
        await this._loadKpi();
    }
}

registry.category("actions").add("cf_scrivania_commerciale", CFScrivaniaCommerciale);
