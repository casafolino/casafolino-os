/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ComposeWizardDialog } from "@casafolino_mail/js/mail_v3/compose_wizard_dialog";

export class CFPipelineControl extends Component {
    static template = "casafolino_pipeline_control.CFPipelineControl";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.state = useState({
            loading: true,
            error: null,
            activeView: this.props.action?.context?.default_view || "dossiers",
            selectedFairId: false,
            inboxFilter: "all",
            dossierSearch: "",
            dossierContinent: "all",
            activeDossierId: false,
            data: {
                kpis: [],
                lanes: [],
                followup: { kpis: [], columns: [], routes: [], timeline: [] },
                post_fair: { kpis: [], columns: [], timeline: [], fair_options: [] },
                pipeline: [],
                inbox: { kpis: [], to_reply: [], waiting_customer: [] },
                dossiers: [],
            },
        });
        onWillStart(this.loadData.bind(this));
    }

    async loadData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            this.state.data = await this.orm.call("cf.pipeline.control", "get_dashboard_data", [this.state.selectedFairId || false]);
            if (!this.state.selectedFairId && this.state.data.post_fair?.fair?.id) {
                this.state.selectedFairId = this.state.data.post_fair.fair.id;
            }
        } catch (error) {
            this.state.error = error.message || String(error);
        } finally {
            this.state.loading = false;
        }
    }

    setView(view) {
        this.state.activeView = view;
    }

    async selectFair(ev) {
        this.state.selectedFairId = parseInt(ev.target.value, 10) || false;
        await this.loadData();
    }

    setInboxFilter(filter) {
        this.state.inboxFilter = filter;
    }

    setDossierSearch(ev) {
        this.state.dossierSearch = (ev.target.value || "").toLowerCase();
    }

    setDossierContinent(ev) {
        this.state.dossierContinent = ev.target.value || "all";
    }

    openDossierWorkbench(dossier) {
        if (!dossier || !dossier.id) {
            this.notification.add(_t("Dossier non disponibile"), { type: "warning" });
            return;
        }
        this.state.activeDossierId = dossier.id;
    }

    closeDossierWorkbench() {
        this.state.activeDossierId = false;
    }

    async openRecord(item) {
        if (!item || !item.model || !item.res_id) {
            this.notification.add(_t("Record non disponibile"), { type: "warning" });
            return;
        }
        if (item.model === "crm.lead") {
            return this.openLeadRecord(item.res_id);
        }
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: item.model,
            res_id: item.res_id,
            views: [[false, "form"]],
            target: "current",
        });
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

    async openLeadRecord(leadId) {
        const id = parseInt(leadId, 10);
        if (!id) {
            this.notification.add(_t("Lead non disponibile"), { type: "warning" });
            return;
        }
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Lead"),
            res_model: "crm.lead",
            res_id: id,
            views: await this._crmLeadFormViews(),
            target: "current",
        });
    }

    async openCard(item) {
        if (!item) {
            return;
        }
        if (item.model === "crm.lead") {
            return this.openLeadRecord(item.res_id || item.id);
        }
        return this.openRecord(item);
    }

    async onCardKeydown(ev, item) {
        if (ev.key !== "Enter" && ev.key !== " ") {
            return;
        }
        ev.preventDefault();
        await this.openCard(item);
    }

    async mailQuickAction(row, quickAction) {
        if (!row || !row.id) {
            this.notification.add(_t("Email non disponibile"), { type: "warning" });
            return;
        }
        try {
            const result = await this.orm.call("cf.pipeline.control", "mail_quick_action", [row.id, quickAction]);
            if (result) {
                if (this.openComposeDialogFromAction(result)) {
                    return;
                }
                await this.action.doAction(result);
                if (result.reload) {
                    await this.loadData();
                }
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    async leadQuickAction(item, quickAction) {
        if (!item || !item.id) {
            this.notification.add(_t("Lead non disponibile"), { type: "warning" });
            return;
        }
        try {
            if (quickAction === "open") {
                return this.openLeadRecord(item.res_id || item.id);
            }
            const result = await this.orm.call("cf.pipeline.control", "lead_quick_action", [item.id, quickAction]);
            if (result) {
                if (this.openComposeDialogFromAction(result)) {
                    return;
                }
                await this.action.doAction(result);
                if (result.reload) {
                    await this.loadData();
                }
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    async recordQuickAction(item, quickAction) {
        if (!item || !item.model || !item.res_id) {
            this.notification.add(_t("Record non disponibile"), { type: "warning" });
            return;
        }
        if (item.model === "crm.lead") {
            return this.leadQuickAction(item, quickAction);
        }
        if (item.model === "casafolino.mail.message") {
            return this.mailQuickAction(item, quickAction);
        }
        try {
            const result = await this.orm.call("cf.pipeline.control", "record_quick_action", [item.model, item.res_id, quickAction]);
            if (result) {
                if (this.openComposeDialogFromAction(result)) {
                    return;
                }
                await this.action.doAction(result);
                if (result.reload) {
                    await this.loadData();
                }
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    openComposeDialogFromAction(result) {
        if (!result || result.tag !== "casafolino_mail.compose_f8") {
            return false;
        }
        const context = result.context || {};
        this.dialog.add(ComposeWizardDialog, {
            partnerEmail: context.default_partner_email || "",
            defaultSubject: context.default_subject || "",
            defaultBody: context.default_body || "",
            partnerId: context.default_partner_id || false,
            threadId: context.default_thread_id || false,
            threadModel: context.default_thread_model || false,
        });
        return true;
    }

    async openModel(model, name) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: model,
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    async newLead() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Nuova richiesta veloce"),
            res_model: "crm.lead",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_type: "opportunity",
            },
        });
    }

    async newDossier() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Nuovo dossier"),
            res_model: "project.project",
            views: [[false, "form"]],
            target: "current",
        });
    }

    async newSample(item) {
        const context = {};
        if (item && item.model === "crm.lead") {
            context.default_lead_id = item.res_id;
        }
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Nuova campionatura"),
            res_model: "cf.export.sample",
            views: [[false, "form"]],
            target: "new",
            context,
        });
    }

    async planPostFairFollowups() {
        const fairId = this.state.selectedFairId || this.state.data.post_fair?.fair?.id;
        if (!fairId) {
            this.notification.add(_t("Seleziona prima una fiera"), { type: "warning" });
            return;
        }
        try {
            const result = await this.orm.call("cf.pipeline.control", "plan_fair_followups", [fairId]);
            if (result) {
                await this.action.doAction(result);
                if (result.reload) {
                    await this.loadData();
                }
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    get navItems() {
        return [
            { id: "control", label: "Sala Controllo", count: this.totalLaneCount },
            { id: "followup", label: "Follow-up", count: this.state.data.followup?.kpis?.[0]?.value || 0 },
            { id: "fair", label: "Post-Fiera", count: this.state.data.post_fair?.fair ? this.state.data.post_fair.kpis?.[0]?.value : 0 },
            { id: "inbox", label: "Inbox", count: this.state.data.inbox?.kpis?.[0]?.value || 0 },
            { id: "pipeline", label: "Pipeline", count: this.pipelineCount },
            { id: "dossiers", label: "Dossier", count: this.state.data.dossiers?.length || 0 },
        ];
    }

    get totalLaneCount() {
        return (this.state.data.lanes || []).reduce((sum, lane) => sum + (lane.count || 0), 0);
    }

    get pipelineCount() {
        return (this.state.data.pipeline || []).reduce((sum, column) => sum + (column.count || 0), 0);
    }

    get inboxFilterOptions() {
        const rows = this.allInboxRows;
        return [
            { id: "all", label: "Tutti", count: rows.length },
            { id: "urgent", label: "Urgenti", count: rows.filter((row) => row.urgency === "high").length },
            { id: "no_lead", label: "Senza lead", count: rows.filter((row) => !row.lead_id).length },
            { id: "with_lead", label: "Con lead", count: rows.filter((row) => row.lead_id).length },
            { id: "ai_action", label: "Azione AI", count: rows.filter((row) => row.needs_action).length },
        ];
    }

    get filteredToReplyRows() {
        return this.filterInboxRows(this.state.data.inbox?.to_reply || []);
    }

    get filteredWaitingRows() {
        return this.filterInboxRows(this.state.data.inbox?.waiting_customer || []);
    }

    get allInboxRows() {
        return [
            ...(this.state.data.inbox?.to_reply || []),
            ...(this.state.data.inbox?.waiting_customer || []),
        ];
    }

    get dossierContinentOptions() {
        const rows = this.state.data.dossiers || [];
        const labels = {
            europe: "Europa",
            north_america: "Nord America",
            south_america: "Sud America",
            asia: "Asia",
            africa: "Africa",
            oceania: "Oceania",
            other: "Altro",
        };
        const counts = rows.reduce((acc, row) => {
            const key = row.continent || "other";
            acc[key] = (acc[key] || 0) + 1;
            return acc;
        }, {});
        return [
            { id: "all", label: _t("Tutti i continenti"), count: rows.length },
            ...Object.entries(counts).map(([id, count]) => ({
                id,
                label: labels[id] || id,
                count,
            })),
        ];
    }

    get filteredDossiers() {
        const rows = this.state.data.dossiers || [];
        const query = this.state.dossierSearch || "";
        const continent = this.state.dossierContinent || "all";
        return rows.filter((row) => {
            const matchesContinent = continent === "all" || (row.continent || "other") === continent;
            if (!matchesContinent) {
                return false;
            }
            if (!query) {
                return true;
            }
            return [
                row.name,
                row.partner,
                row.status,
                row.blocker,
                row.next_action,
                row.continent_label,
            ].filter(Boolean).join(" ").toLowerCase().includes(query);
        });
    }

    get activeDossier() {
        if (!this.state.activeDossierId) {
            return false;
        }
        return (this.state.data.dossiers || []).find((row) => row.id === this.state.activeDossierId) || false;
    }

    filterInboxRows(rows) {
        const filter = this.state.inboxFilter;
        if (filter === "urgent") {
            return rows.filter((row) => row.urgency === "high");
        }
        if (filter === "no_lead") {
            return rows.filter((row) => !row.lead_id);
        }
        if (filter === "with_lead") {
            return rows.filter((row) => row.lead_id);
        }
        if (filter === "ai_action") {
            return rows.filter((row) => row.needs_action);
        }
        return rows;
    }
}

registry.category("actions").add("casafolino_pipeline_control", CFPipelineControl);
