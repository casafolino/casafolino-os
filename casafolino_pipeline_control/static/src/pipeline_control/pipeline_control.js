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
            activeView: this.props.action?.context?.default_view || "control",
            selectedFairId: false,
            inboxFilter: "all",
            dossierSearch: "",
            dossierContinent: "all",
            activeDossierId: false,
            dossierTimeline: [],
            dossierTimelineLoading: false,
            dossierNoteBody: "",
            dossierNoteLoading: false,
            selectedMessageId: null,
            selectedMessageBody: "",
            selectedMessageIds: {},
            messageContext: null,
            partnerSearchQuery: "",
            leadSearchQuery: "",
            dossierSearchQuery: "",
            partnerSearchResults: [],
            leadSearchResults: [],
            dossierSearchResults: [],
            aiDraftBody: "",
            aiDraftLoading: false,
            aiInstruction: "",
            loadedSections: {},
            data: {
                kpis: [],
                discipline: { kpis: [], rows: [] },
                lanes: [],
                b2b_registrations: { kpis: [], rows: [] },
                followup: { kpis: [], columns: [], routes: [], timeline: [] },
                post_fair: { kpis: [], columns: [], timeline: [], fair_options: [] },
                pipeline: [],
                inbox: { kpis: [], to_reply: [], waiting_customer: [] },
                dossiers: [],
            },
        });
        onWillStart(this.loadData.bind(this));
    }

    async loadData(section = this.state.activeView, force = false) {
        const targetSection = section || "control";
        if (!force && this.state.loadedSections[targetSection]) {
            return;
        }
        this.state.loading = true;
        this.state.error = null;
        try {
            const data = await this.orm.call("cf.pipeline.control", "get_dashboard_data", [this.state.selectedFairId || false, targetSection]);
            this.state.data = this.normalizeDashboardData({
                ...this.state.data,
                ...data,
            });
            this.state.loadedSections[targetSection] = true;
            if (!this.state.selectedFairId && this.state.data.post_fair?.fair?.id) {
                this.state.selectedFairId = this.state.data.post_fair.fair.id;
            }
            
            // Auto-select first message in Inbox if not set or not in current list
            const allInbox = this.allInboxRows;
            if (allInbox.length && (!this.state.selectedMessageId || !allInbox.find(m => m.id === this.state.selectedMessageId))) {
                await this.selectMessage(allInbox[0].id);
            }
        } catch (error) {
            this.state.error = error.message || String(error);
        } finally {
            this.state.loading = false;
        }
    }

    async refreshData() {
        await this.loadData(this.state.activeView, true);
    }

    normalizeDashboardData(data = {}) {
        const asArray = (value) => Array.isArray(value) ? value : [];
        const normalized = data || {};
        return {
            ...normalized,
            kpis: asArray(normalized.kpis),
            discipline: {
                ...(normalized.discipline || {}),
                kpis: asArray(normalized.discipline?.kpis),
                rows: asArray(normalized.discipline?.rows),
            },
            lanes: asArray(normalized.lanes).map((lane) => ({
                ...lane,
                items: asArray(lane.items),
            })),
            b2b_registrations: {
                ...(normalized.b2b_registrations || {}),
                kpis: asArray(normalized.b2b_registrations?.kpis),
                rows: asArray(normalized.b2b_registrations?.rows),
            },
            followup: {
                ...(normalized.followup || {}),
                kpis: asArray(normalized.followup?.kpis),
                columns: asArray(normalized.followup?.columns).map((column) => ({
                    ...column,
                    items: asArray(column.items),
                })),
                routes: asArray(normalized.followup?.routes).map((route) => ({
                    ...route,
                    items: asArray(route.items),
                })),
                timeline: asArray(normalized.followup?.timeline),
            },
            post_fair: {
                ...(normalized.post_fair || {}),
                kpis: asArray(normalized.post_fair?.kpis),
                columns: asArray(normalized.post_fair?.columns).map((column) => ({
                    ...column,
                    items: asArray(column.items),
                })),
                timeline: asArray(normalized.post_fair?.timeline),
                fair_options: asArray(normalized.post_fair?.fair_options),
            },
            pipeline: asArray(normalized.pipeline).map((column) => ({
                ...column,
                items: asArray(column.items),
            })),
            inbox: {
                ...(normalized.inbox || {}),
                kpis: asArray(normalized.inbox?.kpis),
                distribution_stats: asArray(normalized.inbox?.distribution_stats),
                to_reply: asArray(normalized.inbox?.to_reply),
                waiting_customer: asArray(normalized.inbox?.waiting_customer),
            },
            dossiers: asArray(normalized.dossiers).map((dossier) => ({
                ...dossier,
                departments: asArray(dossier.departments).map((department) => ({
                    ...department,
                    tasks: asArray(department.tasks),
                })),
            })),
        };
    }

    async selectMessage(messageId) {
        this.state.selectedMessageId = messageId;
        this.state.aiDraftBody = "";
        this.state.aiInstruction = "";
        this.state.selectedMessageBody = _t("Caricamento email...");
        this.state.messageContext = null;
        this.state.partnerSearchQuery = "";
        this.state.leadSearchQuery = "";
        this.state.dossierSearchQuery = "";
        this.state.partnerSearchResults = [];
        this.state.leadSearchResults = [];
        this.state.dossierSearchResults = [];
        
        try {
            const records = await this.orm.read("casafolino.mail.message", [messageId], ["body_html", "body_plain"]);
            if (records && records.length) {
                this.state.selectedMessageBody = records[0].body_html || `<pre>${records[0].body_plain || ''}</pre>` || _t("Nessun contenuto.");
            } else {
                this.state.selectedMessageBody = _t("Impossibile caricare il corpo del messaggio.");
            }
            
            // Fetch sidebar context database info
            this.state.messageContext = await this.orm.call("cf.pipeline.control", "get_message_context_info", [messageId]);
        } catch (error) {
            this.state.selectedMessageBody = _t("Errore caricamento corpo email: ") + (error.message || String(error));
        }
    }

    toggleMessageCheck(messageId) {
        this.state.selectedMessageIds[messageId] = !this.state.selectedMessageIds[messageId];
    }

    async triggerBulkAction(actionType) {
        const ids = Object.keys(this.state.selectedMessageIds).filter(id => this.state.selectedMessageIds[id]).map(Number);
        if (!ids.length) {
            this.notification.add(_t("Nessun messaggio selezionato"), { type: "warning" });
            return;
        }
        try {
            if (actionType === 'archive') {
                await this.orm.call("cf.pipeline.control", "mass_archive", [ids]);
                this.notification.add(_t("Messaggi archiviati con successo"), { type: "success" });
            } else if (actionType === 'link_lead') {
                if (this.selectedMessage && this.selectedMessage.lead_id) {
                    await this.orm.call("cf.pipeline.control", "mass_link_lead", [ids, this.selectedMessage.lead_id]);
                    this.notification.add(_t("Messaggi collegati al lead con successo"), { type: "success" });
                } else {
                    this.notification.add(_t("Seleziona prima una mail collegata ad un lead di destinazione"), { type: "warning" });
                    return;
                }
            }
            this.state.selectedMessageIds = {};
            await this.loadData(this.state.activeView, true);
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    async quickCreatePartner(row) {
        if (!row || !row.id) return;
        try {
            const success = await this.orm.call("cf.pipeline.control", "quick_create_partner", [row.id]);
            if (success) {
                this.notification.add(_t("Contatto registrato e collegato con successo!"), { type: "success" });
                await this.loadData(this.state.activeView, true);
                if (this.state.selectedMessageId === row.id) {
                    await this.selectMessage(row.id);
                }
            } else {
                this.notification.add(_t("Registrazione contatto fallita."), { type: "danger" });
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    async generateAIDraft() {
        if (!this.state.selectedMessageId) return;
        this.state.aiDraftLoading = true;
        try {
            const res = await this.orm.call("cf.pipeline.control", "generate_ai_draft", [this.state.selectedMessageId, this.state.aiInstruction]);
            if (res.success) {
                this.state.aiDraftBody = res.draft;
                this.notification.add(_t("Bozza AI generata con successo"), { type: "success" });
            } else {
                this.notification.add(res.error || _t("Errore nella generazione bozza"), { type: "danger" });
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        } finally {
            this.state.aiDraftLoading = false;
        }
    }

    async sendAIDraft() {
        if (!this.state.selectedMessageId || !this.state.aiDraftBody) return;
        this.state.aiDraftLoading = true;
        try {
            const res = await this.orm.call("cf.pipeline.control", "send_ai_reply", [this.state.selectedMessageId, this.state.aiDraftBody]);
            if (res.success) {
                this.state.aiDraftBody = "";
                this.state.aiInstruction = "";
                this.notification.add(_t("Email di risposta inviata con successo!"), { type: "success" });
                await this.loadData(this.state.activeView, true);
            } else {
                this.notification.add(res.error || _t("Errore nell'invio email"), { type: "danger" });
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        } finally {
            this.state.aiDraftLoading = false;
        }
    }

    async linkPartnerToMessage(partnerId) {
        if (!this.state.selectedMessageId) return;
        try {
            const success = await this.orm.call("cf.pipeline.control", "link_partner_to_message", [this.state.selectedMessageId, partnerId]);
            if (success) {
                this.notification.add(_t("Mittente associato al partner con successo"), { type: "success" });
                await this.loadData(this.state.activeView, true);
                await this.selectMessage(this.state.selectedMessageId);
            } else {
                this.notification.add(_t("Associazione fallita"), { type: "danger" });
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    async linkLeadToMessage(leadId) {
        if (!this.state.selectedMessageId) return;
        try {
            const success = await this.orm.call("cf.pipeline.control", "link_lead_to_message", [this.state.selectedMessageId, leadId]);
            if (success) {
                this.notification.add(_t("Email associata al lead con successo"), { type: "success" });
                await this.loadData(this.state.activeView, true);
                await this.selectMessage(this.state.selectedMessageId);
            } else {
                this.notification.add(_t("Associazione fallita"), { type: "danger" });
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    async linkDossierToMessage(projectId) {
        if (!this.state.selectedMessageId) return;
        try {
            const success = await this.orm.call("cf.pipeline.control", "link_dossier_to_message", [this.state.selectedMessageId, projectId]);
            if (success) {
                this.notification.add(_t("Email associata al dossier con successo"), { type: "success" });
                await this.loadData(this.state.activeView, true);
                await this.selectMessage(this.state.selectedMessageId);
            } else {
                this.notification.add(_t("Associazione fallita"), { type: "danger" });
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    async onPartnerSearch(ev) {
        const query = ev.target.value;
        this.state.partnerSearchQuery = query;
        if (query.length < 2) {
            this.state.partnerSearchResults = [];
            return;
        }
        try {
            this.state.partnerSearchResults = await this.orm.call("cf.pipeline.control", "search_context_records", ["partner", query]);
        } catch (error) {
            console.error(error);
        }
    }

    async onLeadSearch(ev) {
        const query = ev.target.value;
        this.state.leadSearchQuery = query;
        if (query.length < 2) {
            this.state.leadSearchResults = [];
            return;
        }
        try {
            this.state.leadSearchResults = await this.orm.call("cf.pipeline.control", "search_context_records", ["lead", query]);
        } catch (error) {
            console.error(error);
        }
    }

    async onDossierSearch(ev) {
        const query = ev.target.value;
        this.state.dossierSearchQuery = query;
        if (query.length < 2) {
            this.state.dossierSearchResults = [];
            return;
        }
        try {
            this.state.dossierSearchResults = await this.orm.call("cf.pipeline.control", "search_context_records", ["dossier", query]);
        } catch (error) {
            console.error(error);
        }
    }

    setView(view) {
        this.state.activeView = view;
        this.loadData(view);
    }

    async selectFair(ev) {
        this.state.selectedFairId = parseInt(ev.target.value, 10) || false;
        this.state.loadedSections.fair = false;
        await this.loadData("fair", true);
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

    async openDossierWorkbench(dossier) {
        if (!dossier || !dossier.id) {
            this.notification.add(_t("Dossier non disponibile"), { type: "warning" });
            return;
        }
        this.state.activeDossierId = dossier.id;
        await this.loadDossierTimeline(dossier.id);
    }

    async loadDossierTimeline(dossierId) {
        this.state.dossierTimelineLoading = true;
        try {
            this.state.dossierTimeline = await this.orm.call(
                "cf.pipeline.control",
                "get_dossier_timeline",
                [dossierId]
            );
        } catch (error) {
            console.error("Error loading timeline", error);
        } finally {
            this.state.dossierTimelineLoading = false;
        }
    }

    async postDossierNote() {
        const body = (this.state.dossierNoteBody || "").trim();
        if (!body || !this.state.activeDossierId) return;
        this.state.dossierNoteLoading = true;
        try {
            const success = await this.orm.call(
                "cf.pipeline.control",
                "post_dossier_note",
                [this.state.activeDossierId, body]
            );
            if (success) {
                this.state.dossierNoteBody = "";
                this.notification.add(_t("Nota interna aggiunta!"), { type: "success" });
                await this.loadDossierTimeline(this.state.activeDossierId);
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        } finally {
            this.state.dossierNoteLoading = false;
        }
    }

    async cycleSubprojectTrafficLight(sub) {
        if (!sub || !sub.id) return;
        const states = ["green", "yellow", "red"];
        const nextIdx = (states.indexOf(sub.status) + 1) % states.length;
        const nextState = states[nextIdx];
        try {
            await this.orm.write("project.project", [sub.id], {
                cf_traffic_light: nextState
            });
            this.notification.add(_t("Stato aggiornato!"), { type: "success" });
            
            // Reload overall data and active dossier's specific content
            await this.loadData(this.state.activeView, true);
            if (this.state.activeDossierId) {
                await this.loadDossierTimeline(this.state.activeDossierId);
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    closeDossierWorkbench() {
        this.state.activeDossierId = false;
        this.state.dossierTimeline = [];
    }

    async openRecord(item) {
        if (!item || !item.model || !item.res_id) {
            this.notification.add(_t("Record non disponibile"), { type: "warning" });
            return;
        }
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: item.model,
            res_id: item.res_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async mailQuickAction(row, quickAction) {
        if (!row || !row.id) {
            this.notification.add(_t("Email non disponibile"), { type: "warning" });
            return;
        }
        try {
            const result = await this.orm.call("cf.pipeline.control", "mail_quick_action", [row.id, quickAction]);
            if (result) {
                if (await this.openComposeDialogFromAction(result)) {
                    return;
                }
                await this.action.doAction(result);
                if (result.reload) {
                    await this.loadData(this.state.activeView, true);
                }
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    async mailPolicyAction(row, policyAction) {
        if (!row || !row.id) {
            this.notification.add(_t("Email non disponibile"), { type: "warning" });
            return;
        }
        try {
            const result = await this.orm.call("cf.pipeline.control", "mail_policy_action", [row.id, policyAction]);
            if (result) {
                await this.action.doAction(result);
                if (result.reload) {
                    await this.loadData(this.state.activeView, true);
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
            const result = await this.orm.call("cf.pipeline.control", "lead_quick_action", [item.id, quickAction]);
            if (result) {
                if (await this.openComposeDialogFromAction(result)) {
                    return;
                }
                await this.action.doAction(result);
                if (result.reload) {
                    await this.loadData(this.state.activeView, true);
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
                if (await this.openComposeDialogFromAction(result)) {
                    return;
                }
                await this.action.doAction(result);
                if (result.reload) {
                    await this.loadData(this.state.activeView, true);
                }
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    async openComposeDialogFromAction(result) {
        if (!result || result.tag !== "casafolino_mail.compose_f8") {
            return false;
        }
        const ctx = result.context || {};
        const replyToId = ctx.default_thread_model === "casafolino.mail.message"
            ? ctx.default_thread_id
            : (ctx.default_in_reply_to_message_id || false);
        this.dialog.add(ComposeWizardDialog, {
            accountId: ctx.default_account_id || false,
            partnerEmail: ctx.default_partner_email || ctx.default_to_emails || "",
            defaultSubject: ctx.default_subject || "",
            defaultBody: ctx.default_body_html || "",
            partnerId: ctx.default_partner_id || false,
            threadId: ctx.default_thread_id || false,
            threadModel: ctx.default_thread_model || "",
            replyToId,
            mode: ctx.default_mode || (replyToId ? "reply" : "new"),
            onSent: async () => {
                await this.loadData(this.state.activeView, true);
            },
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
        try {
            await this.action.doAction({
                type: "ir.actions.client",
                tag: "casafolino_crm_export.open_wizard_new_lead",
            });
        } catch (error) {
            console.warn("CasaFolino new lead wizard unavailable, falling back to standard CRM form", error);
            await this.openLegacyLeadForm();
        }
    }

    async openLegacyLeadForm() {
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
                    await this.loadData(this.state.activeView, true);
                }
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    async openB2BRegistrations() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Iscrizioni B2B"),
            res_model: "res.partner",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [["cf_b2b_status", "!=", "none"]],
            context: { search_default_pending: 1 },
        });
    }

    async openB2BRegistration(row) {
        if (!row?.id) {
            return;
        }
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Iscrizione B2B"),
            res_model: "res.partner",
            res_id: row.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async approveB2BRegistration(row) {
        if (!row?.id) {
            return;
        }
        try {
            await this.orm.call("res.partner", "action_cf_b2b_approve", [[row.id]]);
            this.notification.add(_t("Cliente B2B approvato"), { type: "success" });
            await this.loadData(this.state.activeView, true);
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    async openPipelineDiscipline() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Lead senza prossima azione"),
            res_model: "crm.lead",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [
                ["type", "=", "opportunity"],
                ["active", "=", true],
                ["stage_id.fold", "=", false],
                ["cf_date_next_followup", "=", false],
            ],
            context: {
                default_type: "opportunity",
            },
        });
    }

    get selectedMessage() {
        if (!this.state.selectedMessageId) return null;
        return this.allInboxRows.find(m => m.id === this.state.selectedMessageId) || null;
    }

    get navItems() {
        return [
            { id: "control", label: "Console CRM", count: this.totalLaneCount },
            { id: "inbox", label: "Inbox", count: this.allInboxRows.length },
            { id: "followup", label: "Follow-up", count: this.followupCount },
            { id: "fair", label: "Post-Fiera", count: this.postFairCount },
            { id: "pipeline", label: "Pipeline", count: this.pipelineCount },
            { id: "dossiers", label: "Dossier", count: this.dossierCount },
        ];
    }

    get totalLaneCount() {
        return (this.state.data.lanes || []).reduce((sum, lane) => sum + (lane.count || 0), 0);
    }

    get followupCount() {
        return (this.state.data.followup?.columns || []).reduce((sum, column) => sum + (column.count || 0), 0);
    }

    get postFairCount() {
        return (this.state.data.post_fair?.columns || []).reduce((sum, column) => sum + (column.count || 0), 0);
    }

    get pipelineCount() {
        return (this.state.data.pipeline || []).reduce((sum, column) => sum + (column.count || 0), 0);
    }

    get dossierCount() {
        return (this.state.data.dossiers || []).length;
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

    get priorityInboxRows() {
        const score = (row) => {
            let value = 60;
            if (row.urgency === "high") value += 24;
            if (row.needs_action) value += 12;
            if (!row.lead_id) value += 6;
            if (row.partner_id) value += 5;
            return Math.min(value, 98);
        };
        return this.filterInboxRows(this.allInboxRows)
            .map((row) => ({ ...row, priority_score: score(row) }))
            .sort((a, b) => b.priority_score - a.priority_score);
    }

    get homeInboxRows() {
        return this.priorityInboxRows.slice(0, 10);
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
