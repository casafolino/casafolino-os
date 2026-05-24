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
        this.identitySearchTimer = null;

        // Determine default cluster from action tag
        const tag = this.props.action?.tag || "cf_scrivania_commerciale";
        let defaultCluster = "crm";
        if (tag === "cf_scrivania_operativa") defaultCluster = "produzione";
        else if (tag === "cf_scrivania_admin") defaultCluster = "tesoreria";
        else if (tag === "cf_workspace_haccp") defaultCluster = "haccp";

        this.state = useState({
            activeCluster: defaultCluster,
            isLoading: true,
            mailRows: [],
            dossierRows: [],
            identityPanelOpen: false,
            identityLoading: false,
            identityQuery: "",
            identityContext: "search",
            identityMail: null,
            identityResults: {
                contacts: [],
                leads: [],
                dossiers: [],
                mails: [],
            },
            kpi: {
                crm: {},
                produzione: {},
                haccp: {},
                tesoreria: {},
            },
        });

        onWillStart(async () => {
            await this._loadAllKpi();
            await this._loadMailRows();
            await this._loadDossierRows();
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

    async _loadMailRows() {
        try {
            const rows = await this.orm.searchRead(
                "casafolino.mail.message",
                [
                    ["direction", "=", "inbound"],
                    ["is_deleted", "=", false],
                    ["is_archived", "=", false],
                    ["state", "not in", ["discard", "auto_discard", "internal"]],
                ],
                ["subject", "sender_name", "sender_email", "snippet", "email_date", "lead_id", "cf_project_id", "ai_action_required", "ai_urgency"],
                { limit: 6, order: "email_date desc, id desc" }
            );
            this.state.mailRows = rows.map((row) => ({
                ...row,
                subject: row.subject || "(senza oggetto)",
                sender: row.sender_name || row.sender_email || "Mittente sconosciuto",
                preview: row.snippet || row.sender_email || "Email ricevuta",
                badge: row.lead_id ? "lead" : row.cf_project_id ? "dossier" : row.ai_action_required ? "azione" : "nuova",
                badgeClass: row.lead_id ? "green" : row.cf_project_id ? "violet" : row.ai_urgency === "high" ? "amber" : "",
                actionLabel: row.lead_id ? "Apri lead" : "Crea lead",
            }));
        } catch (err) {
            console.warn("Workspace mail rows load failed:", err);
            this.state.mailRows = [];
        }
    }

    async _loadDossierRows() {
        try {
            const rows = await this.orm.searchRead(
                "project.project",
                [["cf_status_dossier", "!=", false]],
                ["id", "name", "partner_id", "cf_status_dossier", "cf_next_action", "write_date"],
                { limit: 8, order: "write_date desc, id desc" }
            );
            this.state.dossierRows = rows.map((row) => ({
                ...row,
                title: row.name || "Dossier senza nome",
                partner: row.partner_id?.[1] || "Cliente non collegato",
                status: row.cf_status_dossier || "dossier",
                nextAction: row.cf_next_action || "Apri la Vista 360 e aggiorna la prossima azione.",
            }));
        } catch (err) {
            console.warn("Workspace dossier rows load failed:", err);
            this.state.dossierRows = [];
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
        await this._loadMailRows();
        await this._loadDossierRows();
    }

    get identitySections() {
        return [
            { key: "contacts", title: "Contatti", label: "contatto", icon: "fa-address-card", rows: this.state.identityResults.contacts },
            { key: "leads", title: "Lead / pipeline", label: "lead", icon: "fa-bullseye", rows: this.state.identityResults.leads },
            { key: "dossiers", title: "Dossier 360", label: "dossier", icon: "fa-folder-open", rows: this.state.identityResults.dossiers },
            { key: "mails", title: "Mail", label: "mail", icon: "fa-envelope", rows: this.state.identityResults.mails },
        ];
    }

    get hasIdentityResults() {
        return this.identitySections.some((section) => section.rows.length);
    }

    get identityContextTitle() {
        const titles = {
            lead: "Controllo prima di creare un lead",
            mail: "Controllo prima di lavorare la mail",
            dossier: "Controllo prima di aprire un dossier",
            search: "Ricerca globale",
        };
        return titles[this.state.identityContext] || titles.search;
    }

    // ======== CRM actions ========

    async onNewProject() {
        await this.action.doAction(
            "casafolino_crm_export.action_cf_commercial_project_wizard"
        );
    }

    async onCreateNewLead() {
        try {
            await this.action.doAction({
                type: "ir.actions.client",
                tag: "casafolino_crm_export.open_wizard_new_lead",
                target: "new",
            });
        } catch {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "crm.lead",
                views: await this._crmLeadFormViews(),
                target: "current",
                context: { default_type: "lead", default_user_id: user.userId },
            });
        }
    }

    async onNewLead() {
        await this.openIdentityPanel("lead");
    }

    async onSearchInput(ev) {
        this.state.identityQuery = ev.target.value || "";
        if (!this.state.identityPanelOpen) {
            this.state.identityContext = "search";
            this.state.identityPanelOpen = true;
        }
        clearTimeout(this.identitySearchTimer);
        this.identitySearchTimer = setTimeout(() => {
            this.runIdentitySearch(this.state.identityContext || "search");
        }, 250);
    }

    async onSubmitGlobalSearch(ev) {
        ev.preventDefault();
        await this.runIdentitySearch("search");
    }

    async onFocusGlobalSearch() {
        await this.openIdentityPanel("search");
    }

    async openIdentityPanel(context = "search", query = "", mail = null) {
        this.state.identityContext = context;
        this.state.identityMail = mail;
        if (query) {
            this.state.identityQuery = query;
        }
        this.state.identityPanelOpen = true;
        if ((this.state.identityQuery || "").trim().length >= 2) {
            await this.runIdentitySearch(context);
        }
    }

    closeIdentityPanel() {
        this.state.identityPanelOpen = false;
        this.state.identityMail = null;
    }

    async runIdentitySearch(context = this.state.identityContext) {
        const query = (this.state.identityQuery || "").trim();
        this.state.identityContext = context;
        this.state.identityPanelOpen = true;
        if (query.length < 2) {
            this.state.identityResults = { contacts: [], leads: [], dossiers: [], mails: [] };
            return;
        }
        this.state.identityLoading = true;
        try {
            const [contacts, leads, dossiers, mails] = await Promise.all([
                this._safeSearchRead("res.partner", [
                    "|", "|", "|", "|",
                    ["name", "ilike", query],
                    ["email", "ilike", query],
                    ["phone", "ilike", query],
                    ["mobile", "ilike", query],
                    ["vat", "ilike", query],
                ], ["name", "email", "phone", "mobile"], 5),
                this._safeSearchRead("crm.lead", [
                    "|", "|", "|", "|",
                    ["name", "ilike", query],
                    ["contact_name", "ilike", query],
                    ["email_from", "ilike", query],
                    ["phone", "ilike", query],
                    ["mobile", "ilike", query],
                ], ["name", "contact_name", "email_from", "phone", "stage_id"], 5),
                this._safeSearchRead("project.project", [
                    "|", ["name", "ilike", query], ["partner_id.name", "ilike", query],
                ], ["name", "partner_id", "cf_status_dossier", "cf_next_action"], 5),
                this._safeSearchRead("casafolino.mail.message", [
                    "|", "|", "|",
                    ["subject", "ilike", query],
                    ["sender_email", "ilike", query],
                    ["sender_name", "ilike", query],
                    ["snippet", "ilike", query],
                ], ["subject", "sender_name", "sender_email", "lead_id", "cf_project_id"], 5),
            ]);
            this.state.identityResults = {
                contacts: contacts.map((row) => this._identityRow("res.partner", row, row.name, row.email || row.phone || row.mobile)),
                leads: leads.map((row) => this._identityRow("crm.lead", row, row.name || row.contact_name, row.email_from || row.phone || row.stage_id?.[1])),
                dossiers: dossiers.map((row) => this._identityRow("project.project", row, row.name, row.partner_id?.[1] || row.cf_next_action || row.cf_status_dossier)),
                mails: mails.map((row) => this._identityRow("casafolino.mail.message", row, row.subject || "(senza oggetto)", row.sender_name || row.sender_email)),
            };
        } finally {
            this.state.identityLoading = false;
        }
    }

    async _safeSearchRead(model, domain, fields, limit) {
        try {
            return await this.orm.searchRead(model, domain, fields, { limit, order: "write_date desc, id desc" });
        } catch (err) {
            console.warn(`Identity search failed for ${model}:`, err);
            return [];
        }
    }

    _identityRow(model, row, title, subtitle) {
        return {
            id: row.id,
            model,
            title: title || "Senza nome",
            subtitle: subtitle || "Apri scheda",
            raw: row,
        };
    }

    _normalizeWindowAction(action, fallbackView = "form") {
        if (action?.type === "ir.actions.act_window" && !Array.isArray(action.views)) {
            const viewMode = action.view_mode || fallbackView;
            action.views = viewMode.split(",").map((mode) => [false, mode.trim() || fallbackView]);
        }
        return action;
    }

    async _crmLeadFormViews() {
        if (this.crmLeadFormViewId === undefined) {
            try {
                this.crmLeadFormViewId = await this.orm.call(
                    "crm.lead",
                    "casafolino_get_premium_form_view_id",
                    []
                );
            } catch (err) {
                console.warn("Premium lead form view lookup failed:", err);
                this.crmLeadFormViewId = false;
            }
        }
        return [[this.crmLeadFormViewId || false, "form"]];
    }

    async _crmLeadViewsWithPipeline() {
        const formViews = await this._crmLeadFormViews();
        return [[false, "kanban"], [false, "list"], formViews[0]];
    }

    async onOpenIdentityResult(row) {
        if (row.model === "project.project") {
            await this.onOpenDossier360({
                id: row.id,
                title: row.title,
            });
            return;
        }
        const views = row.model === "crm.lead"
            ? await this._crmLeadFormViews()
            : [[false, "form"]];
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: row.model,
            res_id: row.id,
            views,
            target: "current",
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
        await this.openIdentityPanel("mail");
    }

    async onOpenMailHub() {
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

    async onOpenMailRow(mail) {
        if (!mail?.id) {
            await this.onOpenMiaCasella();
            return;
        }
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "casafolino.mail.message",
            res_id: mail.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async onCreateLeadFromMail(mail) {
        if (!mail?.id) {
            await this.onNewLead();
            return;
        }
        await this.openIdentityPanel("mail", mail.sender_email || mail.sender || mail.subject || "", mail);
    }

    async onConfirmCreateLeadFromMail() {
        const mail = this.state.identityMail;
        if (!mail?.id) {
            await this.onCreateNewLead();
            return;
        }
        if (mail.lead_id) {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "crm.lead",
                res_id: mail.lead_id[0],
                views: await this._crmLeadFormViews(),
                target: "current",
            });
            return;
        }
        const action = await this.orm.call(
            "casafolino.mail.message",
            "action_create_lead",
            [[mail.id]]
        );
        const normalizedAction = this._normalizeWindowAction(action);
        if (normalizedAction?.res_model === "crm.lead") {
            normalizedAction.views = await this._crmLeadFormViews();
        }
        await this.action.doAction(normalizedAction);
    }

    async onOpenPipeline() {
        try {
            await this.action.doAction("casafolino_crm_export.action_cf_crm_all");
        } catch {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "crm.lead",
                views: await this._crmLeadViewsWithPipeline(),
                domain: [["type", "in", ["lead", "opportunity"]], ["active", "=", true]],
                target: "current",
            });
        }
    }

    async onOpenProjects() {
        if (!this.state.identityPanelOpen) {
            await this.openIdentityPanel("dossier");
            return;
        }
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

    async onOpenDossier360(dossier) {
        if (!dossier?.id) {
            await this.onOpenProjects();
            return;
        }
        await this.action.doAction({
            type: "ir.actions.client",
            tag: "casafolino_crm_export.project_dashboard",
            name: `Vista 360° — ${dossier.title || dossier.name || "Dossier"}`,
            target: "current",
            context: {
                active_id: dossier.id,
                default_project_id: dossier.id,
                active_model: "project.project",
            },
        });
    }

    async onOpenFirstDossier360() {
        try {
            const dossiers = await this.orm.searchRead(
                "project.project",
                [["cf_status_dossier", "!=", false]],
                ["id", "name"],
                { limit: 1, order: "write_date desc" }
            );
            const dossier = dossiers[0];
            if (!dossier) {
                await this.onOpenProjects();
                return;
            }
            await this.action.doAction({
                type: "ir.actions.client",
                tag: "casafolino_crm_export.project_dashboard",
                name: `Vista 360° — ${dossier.name}`,
                target: "current",
                context: {
                    active_id: dossier.id,
                    default_project_id: dossier.id,
                    active_model: "project.project",
                },
            });
        } catch {
            await this.onOpenProjects();
        }
    }

    async onOpenLavagna() {
        try {
            await this.action.doAction("casafolino_initiative.action_cf_initiative");
        } catch {
            await this.action.doAction({
                type: "ir.actions.act_window",
                name: "Lavagne operative",
                res_model: "cf.initiative",
                views: [[false, "kanban"], [false, "list"], [false, "form"]],
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

// Register with force so the unified workspace wins over legacy desks.
registry.category("actions").add("cf_scrivania_commerciale", CFWorkspace, { force: true });
registry.category("actions").add("cf_workspace_main", CFWorkspace, { force: true });
registry.category("actions").add("cf_scrivania_operativa", CFWorkspace, { force: true });
registry.category("actions").add("cf_scrivania_admin", CFWorkspace, { force: true });
registry.category("actions").add("cf_workspace_haccp", CFWorkspace, { force: true });
