/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

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
        this.user = useService("user");
        this.notification = useService("notification");

        this.state = useState({
            isLoading: true,
            data: null,
            activeTab: "timeline",
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

    get tabs() {
        return [
            { id: "timeline", label: "Timeline", enabled: true },
            { id: "cliente", label: "Cliente", enabled: true },
            { id: "commerciale", label: "Commerciale", enabled: false, brief: "5.1" },
            { id: "campionature", label: "Campionature", enabled: false, brief: "5.1" },
            { id: "documenti", label: "Documenti", enabled: false, brief: "5.2" },
            { id: "mail", label: "Mail", enabled: false, brief: "B6" },
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
        const tab = this.tabs.find((t) => t.id === tabId);
        if (tab && !tab.enabled) {
            this.notification.add(
                _t("Sezione disponibile in Brief #%s", tab.brief),
                { type: "info" }
            );
            return;
        }
        this.state.activeTab = tabId;
    }

    onTimelineFilter(filter) {
        this.state.timelineFilter = filter;
    }

    async onQuickActionMail() {
        this.notification.add(
            _t("Composer mail disponibile in Brief #8"),
            { type: "info" }
        );
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
            context: { default_partner_id: partnerId },
        });
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
}

// Register as client action
registry.category("actions").add(
    "casafolino_crm_export.project_dashboard",
    CFProjectDashboard
);
