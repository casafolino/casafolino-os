/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import { ComposeWizardDialog } from "@casafolino_mail/js/mail_v3/compose_wizard_dialog";

const STATUS_LABELS = {
    exploration: "Esplorativo",
    active: "Attivo",
    on_hold: "In pausa",
    won: "Vinto",
    closed: "Chiuso",
};

const STATUS_COLORS = {
    exploration: "blue",
    active: "green",
    on_hold: "orange",
    won: "emerald",
    closed: "gray",
};

const COUNTRY_FLAGS = {
    IT: "\u{1F1EE}\u{1F1F9}", CA: "\u{1F1E8}\u{1F1E6}", US: "\u{1F1FA}\u{1F1F8}",
    DE: "\u{1F1E9}\u{1F1EA}", FR: "\u{1F1EB}\u{1F1F7}", ES: "\u{1F1EA}\u{1F1F8}",
    GB: "\u{1F1EC}\u{1F1E7}", NL: "\u{1F1F3}\u{1F1F1}", BE: "\u{1F1E7}\u{1F1EA}",
    CH: "\u{1F1E8}\u{1F1ED}", AT: "\u{1F1E6}\u{1F1F9}", JP: "\u{1F1EF}\u{1F1F5}",
    CN: "\u{1F1E8}\u{1F1F3}", KR: "\u{1F1F0}\u{1F1F7}", AE: "\u{1F1E6}\u{1F1EA}",
    SA: "\u{1F1F8}\u{1F1E6}", BR: "\u{1F1E7}\u{1F1F7}", MX: "\u{1F1F2}\u{1F1FD}",
    AU: "\u{1F1E6}\u{1F1FA}", PL: "\u{1F1F5}\u{1F1F1}", SE: "\u{1F1F8}\u{1F1EA}",
    DK: "\u{1F1E9}\u{1F1F0}", NO: "\u{1F1F3}\u{1F1F4}", PT: "\u{1F1F5}\u{1F1F9}",
    GR: "\u{1F1EC}\u{1F1F7}", RO: "\u{1F1F7}\u{1F1F4}", CZ: "\u{1F1E8}\u{1F1FF}",
    HU: "\u{1F1ED}\u{1F1FA}", IE: "\u{1F1EE}\u{1F1EA}", FI: "\u{1F1EB}\u{1F1EE}",
};

function getFlag(code) {
    if (!code) return "";
    return COUNTRY_FLAGS[code.toUpperCase()] || "";
}

function formatCurrency(val) {
    if (!val) return "0";
    if (val >= 1000) {
        return Math.round(val / 1000) + "k";
    }
    return String(Math.round(val));
}

export class CFProjectDashboard extends Component {
    static template = "casafolino_crm_export.CFProjectDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");

        this.state = useState({
            isLoading: true,
            data: null,
            activeTab: "cockpit",
            timelineFilter: "all",
            error: null,
        });

        onWillStart(this._loadData.bind(this));
    }

    async _loadData() {
        try {
            const ctx = this.props.action?.context || {};
            const projectId = ctx.active_id || ctx.default_project_id;
            if (!projectId) {
                throw new Error("No project ID in action context");
            }
            const data = await this.orm.call(
                "project.project",
                "cf_get_dashboard_data",
                [[projectId]]
            );
            this.state.data = data;
            this.state.isLoading = false;
        } catch (err) {
            this.state.error = err.message || String(err);
            this.state.isLoading = false;
        }
    }

    // --- Getters for template ---

    get statusLabel() {
        const s = this.state.data?.project?.status_dossier;
        return STATUS_LABELS[s] || s || "";
    }

    get statusColor() {
        const s = this.state.data?.project?.status_dossier;
        return STATUS_COLORS[s] || "gray";
    }

    get partnerFlag() {
        return getFlag(this.state.data?.partner?.country_code);
    }

    get partnerLocation() {
        const p = this.state.data?.partner;
        if (!p) return "";
        const parts = [p.city, p.country_name].filter(Boolean);
        return parts.join(", ");
    }

    get stageSegments() {
        const pos = this.state.data?.lead?.stage_position || 0;
        return [1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => ({
            index: i,
            active: i <= pos,
            current: i === pos,
        }));
    }

    get kpiRevenue() {
        return formatCurrency(this.state.data?.kpi?.revenue);
    }

    get kpiForecast() {
        return formatCurrency(this.state.data?.kpi?.forecast);
    }

    get filteredTimeline() {
        const tl = this.state.data?.timeline;
        if (!tl) return [];
        if (this.state.timelineFilter === "all") return tl;
        return tl.filter((ev) => ev.type === this.state.timelineFilter);
    }

    get brokerContact() {
        return (this.state.data?.contacts || []).find(
            (contact) => contact.role === "broker" || contact.is_external
        ) || null;
    }

    get displayedMail() {
        return (this.state.data?.mail || []).slice(0, 6);
    }

    get displayedTimeline() {
        return (this.state.data?.timeline || []).slice(0, 6);
    }

    get inboundMailCount() {
        return (this.state.data?.mail || []).filter((mail) => !mail.is_outbound).length;
    }

    get outboundMailCount() {
        return (this.state.data?.mail || []).filter((mail) => mail.is_outbound).length;
    }

    contactInitials(contact) {
        return (contact?.name || "?")
            .split(" ")
            .filter(Boolean)
            .map((part) => part[0])
            .join("")
            .slice(0, 2)
            .toUpperCase();
    }

    get tabs() {
        return [
            { id: "cockpit", label: "Vista 360", enabled: true },
            { id: "timeline", label: "Evoluzione", enabled: true },
            { id: "documenti", label: "Documenti", enabled: true },
            { id: "mail", label: "Comunicazioni", enabled: true },
            { id: "storico", label: "Storico", enabled: true },
        ];
    }

    get timelineFilters() {
        return [
            { id: "all", label: "Tutti" },
            { id: "mail", label: "Email" },
            { id: "activity", label: "Attività" },
            { id: "message", label: "Note" },
        ];
    }

    // --- Handlers ---

    onTabChange(tabId) {
        if (!this.tabs.some((tab) => tab.id === tabId && tab.enabled)) {
            return;
        }
        this.state.activeTab = tabId;
    }

    onTimelineFilter(filter) {
        this.state.timelineFilter = filter;
    }

    async onQuickActionMail() {
        const partnerEmail = this.state.data?.partner?.email || "";
        this.dialog.add(ComposeWizardDialog, {
            partnerEmail,
            onSent: () => this.onRefresh(),
        });
    }

    async onQuickActionSample() {
        const leadId = this.state.data?.lead?.id;
        if (!leadId) {
            this.notification.add(_t("Nessun lead collegato"), { type: "warning" });
            return;
        }
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cf.export.sample",
            views: [[false, "form"]],
            target: "new",
            context: { default_lead_id: leadId },
        });
    }

    async onQuickActionOffer() {
        const partnerId = this.state.data?.partner?.id;
        if (!partnerId) {
            this.notification.add(_t("Nessun partner collegato"), { type: "warning" });
            return;
        }
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "sale.order",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_partner_id: partnerId,
                default_cf_project_id: this.state.data?.project?.id || false,
            },
        });
    }

    async onOpenSaleOrders() {
        const partnerId = this.state.data?.partner?.id;
        if (!partnerId) {
            this.notification.add(_t("Nessun partner collegato"), { type: "warning" });
            return;
        }
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Preventivi e ordini"),
            res_model: "sale.order",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [["partner_id", "=", partnerId]],
            context: {
                default_partner_id: partnerId,
                default_cf_project_id: this.state.data?.project?.id || false,
            },
        });
    }

    async onOpenDocuments() {
        const projectId = this.state.data?.project?.id;
        const partnerId = this.state.data?.partner?.id;
        const domain = [
            "|",
            "&", ["res_model", "=", "project.project"], ["res_id", "=", projectId || 0],
            "&", ["res_model", "=", "res.partner"], ["res_id", "=", partnerId || 0],
        ];
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Documenti dossier"),
            res_model: "ir.attachment",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain,
            context: {
                default_res_model: "project.project",
                default_res_id: projectId || false,
            },
        });
    }

    async onUploadDocument() {
        const projectId = this.state.data?.project?.id;
        if (!projectId) return;
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Carica documento"),
            res_model: "ir.attachment",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_res_model: "project.project",
                default_res_id: projectId,
            },
        });
        await this.onRefresh();
    }

    async onQuickActionActivity() {
        const projectId = this.state.data?.project?.id;
        if (!projectId) return;
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "mail.activity",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_res_model: "project.project",
                default_res_id: projectId,
            },
        });
    }

    // Brief #FINAL — Commerciale + Campionature handlers

    async onOpenSaleOrder(orderId) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "sale.order",
            res_id: orderId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async onOpenSample(sampleId) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cf.export.sample",
            res_id: sampleId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async onCreateNewSample() {
        const leadId = this.state.data?.lead?.id;
        if (!leadId) {
            this.notification.add(_t("Nessun lead collegato"), { type: "warning" });
            return;
        }
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cf.export.sample",
            views: [[false, "form"]],
            target: "new",
            context: { default_lead_id: leadId },
        });
    }

    async onOpenLead() {
        const leadId = this.state.data?.lead?.id;
        if (!leadId) return;
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            res_id: leadId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async onOpenPartner() {
        const partnerId = this.state.data?.partner?.id;
        if (!partnerId) return;
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async onOpenProjectForm() {
        const projectId = this.state.data?.project?.id;
        if (!projectId) return;
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "project.project",
            res_id: projectId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    onGoBack() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            target: "current",
            domain: [["type", "=", "opportunity"]],
        });
    }

    async onRefresh() {
        this.state.isLoading = true;
        this.state.error = null;
        await this._loadData();
    }

    async onSyncDossierMail() {
        const projectId = this.state.data?.project?.id;
        if (!projectId) return;
        await this.orm.call(
            "project.project",
            "action_sync_dossier_mail_history",
            [[projectId]]
        );
        this.notification.add(_t("Storico mail aggiornato"), { type: "success" });
        await this.onRefresh();
    }

    onContactClick(contactId) {
        if (!contactId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: contactId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async onAddContact() {
        const projectId = this.state.data?.project?.id;
        if (!projectId) return;
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cf.project.contact",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_project_id: projectId,
                default_mail_sync_enabled: true,
            },
        });
        await this.onRefresh();
    }

    // Brief #B6 — Mail tab handlers
    onOpenMailThread(mailEntry) {
        if (!mailEntry.partner_id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: mailEntry.partner_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async onQuickReply(mailEntry) {
        if (!mailEntry.partner_id) return;
        this.dialog.add(ComposeWizardDialog, {
            partnerEmail: mailEntry.sender_email || '',
            defaultSubject: mailEntry.subject ? 'Re: ' + mailEntry.subject : '',
            partnerId: mailEntry.partner_id || null,
            threadId: mailEntry.partner_id || null,
            threadModel: 'res.partner',
            onSent: () => this.onRefresh(),
        });
    }
}

// Register as client action
registry.category("actions").add(
    "casafolino_crm_export.project_dashboard",
    CFProjectDashboard
);
