/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { registry } from "@web/core/registry";

const CLUSTERS = ["crm", "produzione", "haccp", "tesoreria"];

export class CFWorkspace extends Component {
    static template = "casafolino_home.CFWorkspace";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        // Determine default cluster from action tag
        const tag = this.props.action?.tag || "cf_scrivania_commerciale";
        let defaultCluster = "crm";
        if (tag === "cf_scrivania_operativa") defaultCluster = "produzione";
        else if (tag === "cf_scrivania_admin") defaultCluster = "tesoreria";
        else if (tag === "cf_workspace_haccp") defaultCluster = "haccp";

        this.state = useState({
            activeCluster: defaultCluster,
            isLoading: true,
            kpi: {
                crm: {},
                produzione: {},
                haccp: {},
                tesoreria: {},
            },
        });

        onWillStart(async () => {
            await this._loadAllKpi();
        });
    }

    async _loadAllKpi() {
        this.state.isLoading = true;
        try {
            const result = await this.orm.call("cf.home.kpi", "cf_get_kpi_all", []);
            this.state.kpi.crm = result.commerciale || {};
            this.state.kpi.produzione = result.operativa || {};
            this.state.kpi.haccp = result.haccp || {};
            this.state.kpi.tesoreria = result.admin || {};
        } catch (err) {
            console.warn("Workspace KPI load failed:", err);
        } finally {
            this.state.isLoading = false;
        }
    }

    get activeCluster() {
        return this.state.activeCluster;
    }

    switchCluster(cluster) {
        if (CLUSTERS.includes(cluster)) {
            this.state.activeCluster = cluster;
        }
    }

    onSwitchCRM() { this.switchCluster("crm"); }
    onSwitchProduzione() { this.switchCluster("produzione"); }
    onSwitchHACCP() { this.switchCluster("haccp"); }
    onSwitchTesoreria() { this.switchCluster("tesoreria"); }

    formatKpi(value, type) {
        if (value === null || value === undefined) return "\u2014";
        if (type === "currency") {
            const k = Math.round(value / 1000);
            return "\u20AC" + k + "k";
        }
        if (type === "text") return String(value);
        return String(Math.round(value));
    }

    async onRefresh() {
        await this._loadAllKpi();
    }

    // ======== CRM actions ========

    async onNewProject() {
        await this.action.doAction(
            "casafolino_crm_export.action_cf_commercial_project_wizard"
        );
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
            await this.action.doAction("casafolino_mail.action_cf_mail_posizionatore");
        } catch {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "casafolino.mail.message",
                views: [[false, "list"], [false, "form"]],
                domain: [["cf_project_id", "=", false], ["partner_id", "!=", false]],
                target: "current",
            });
        }
    }

    async onOpenMiaCasella() {
        try {
            await this.action.doAction("casafolino_mail.action_casafolino_mail_my_mailbox");
        } catch {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "casafolino.mail.message",
                views: [[false, "list"], [false, "form"]],
                target: "current",
            });
        }
    }

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
            await this.action.doAction("casafolino_crm_export.action_project_dashboard_360");
        } catch {
            console.warn("Analytics action not available");
        }
    }

    async onOpenDossierExport() {
        await this.action.doAction("casafolino_crm_export.action_cf_project_dossier");
    }

    // ======== Produzione actions ========

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

    // ======== HACCP actions ========

    async onOpenHACCPDashboard() {
        try {
            await this.action.doAction("casafolino_haccp.action_cf_haccp_dashboard");
        } catch {
            console.warn("HACCP dashboard not available");
        }
    }

    async onOpenNC() {
        try {
            await this.action.doAction("casafolino_haccp.action_cf_haccp_nc");
        } catch {
            console.warn("HACCP NC not available");
        }
    }

    async onOpenCalibrations() {
        try {
            await this.action.doAction("casafolino_haccp.action_cf_haccp_calibration");
        } catch {
            console.warn("Calibrations not available");
        }
    }

    async onOpenRegistri() {
        try {
            await this.action.doAction("casafolino_haccp.action_cf_haccp_registri");
        } catch {
            console.warn("Registri not available");
        }
    }

    async onOpenQuarantine() {
        try {
            await this.action.doAction("casafolino_haccp.action_cf_haccp_quarantine");
        } catch {
            console.warn("Quarantine not available");
        }
    }

    async onOpenHACCPDocuments() {
        try {
            await this.action.doAction("casafolino_haccp.action_cf_haccp_documents");
        } catch {
            console.warn("HACCP documents not available");
        }
    }

    // ======== Tesoreria actions ========

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
}

// Register for all action tags (backward compat + new)
registry.category("actions").add("cf_scrivania_commerciale", CFWorkspace);
registry.category("actions").add("cf_scrivania_operativa", CFWorkspace);
registry.category("actions").add("cf_scrivania_admin", CFWorkspace);
registry.category("actions").add("cf_workspace_haccp", CFWorkspace);
