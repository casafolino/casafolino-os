/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

export class CFSalaCommercialeV8 extends Component {
    static template = "casafolino_sala_commerciale.CFSalaCommercialeV8";
    static props = ["*"];

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            isLoading: true,
            kpi: {
                mail_pending: null,
                lead_aperti: null,
                progetti_attivi: null,
                sla_scadenza: null,
                fatturato_mese: null,
                currency: "€",
            },
            selectedMail: {
                company: "AL WASL GENERAL TRADING COMPANY",
                subject: "Request for catalogue",
                snippet: "Richiesta catalogo export, listino e opportunita private label per mercato UAE.",
                contacts: ["Ahmed Al Wasl", "purchasing@alwasl.ae"],
                nextAction: "Inviare catalogo oggi e follow-up 13/06",
            },
        });

        onWillStart(async () => this.loadKpi());
    }

    async loadKpi() {
        this.state.isLoading = true;
        try {
            const result = await this.orm.call("cf.home.kpi", "cf_get_kpi_commerciale", []);
            Object.assign(this.state.kpi, result);
        } catch (err) {
            console.warn("Sala Commerciale v8 KPI load failed:", err);
        } finally {
            this.state.isLoading = false;
        }
    }

    formatKpi(value, type) {
        if (value === null || value === undefined) return "—";
        if (type === "currency") return `${this.state.kpi.currency}${Math.round(value / 1000)}k`;
        return String(Math.round(value));
    }

    async crmLeadFormViews() {
        if (this.crmLeadFormViewId === undefined) {
            try {
                this.crmLeadFormViewId = await this.orm.call(
                    "crm.lead",
                    "casafolino_get_premium_form_view_id",
                    []
                );
            } catch {
                this.crmLeadFormViewId = false;
            }
        }
        return [[this.crmLeadFormViewId || false, "form"]];
    }

    async openMailTriage() {
        try {
            await this.action.doAction("casafolino_mail.action_cf_mail_posizionatore");
        } catch {
            await this.action.doAction({
                type: "ir.actions.act_window",
                name: "Inbox triage",
                res_model: "casafolino.mail.message",
                views: [[false, "list"], [false, "form"]],
                domain: [["state", "in", ["new", "review"]]],
                target: "current",
            });
        }
    }

    async openMailbox() {
        try {
            await this.action.doAction("casafolino_mail.action_casafolino_mail_my_mailbox");
        } catch {
            await this.openMailTriage();
        }
    }

    async createCompanyAndContacts() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Nuova azienda da mail",
            res_model: "res.partner",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_name: this.state.selectedMail.company,
                default_company_type: "company",
            },
        });
    }

    async createPipelineLead() {
        try {
            await this.action.doAction({
                type: "ir.actions.client",
                tag: "casafolino_crm_export.open_wizard_new_lead",
                target: "new",
            });
        } catch {
            await this.action.doAction({
                type: "ir.actions.act_window",
                name: "Nuovo lead da mail",
                res_model: "crm.lead",
                views: await this.crmLeadFormViews(),
                target: "current",
                context: {
                    default_name: `${this.state.selectedMail.company} - catalogo export`,
                    default_type: "lead",
                    default_user_id: user.userId,
                },
            });
        }
    }

    async prepareDossier() {
        try {
            await this.action.doAction("casafolino_crm_export.action_cf_dossier_upsert_wizard");
        } catch {
            await this.action.doAction({
                type: "ir.actions.act_window",
                name: "Dossier export",
                res_model: "project.project",
                views: [[false, "kanban"], [false, "list"], [false, "form"]],
                target: "current",
            });
        }
    }

    async createFollowupTask() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Task e follow-up",
            res_model: "mail.activity",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            context: {
                default_summary: this.state.selectedMail.nextAction,
                default_user_id: user.userId,
            },
        });
    }

    async openPipeline() {
        try {
            await this.action.doAction("casafolino_crm_export.action_cf_crm_all");
        } catch {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "crm.lead",
                views: [[false, "kanban"], [false, "list"], (await this.crmLeadFormViews())[0]],
                domain: [["type", "=", "lead"], ["active", "=", true]],
                target: "current",
            });
        }
    }

    async openDossiers() {
        try {
            await this.action.doAction("casafolino_crm_export.action_cf_project_dossier");
        } catch {
            await this.prepareDossier();
        }
    }
}

registry.category("actions").add("cf_sala_commerciale_v8", CFSalaCommercialeV8);
