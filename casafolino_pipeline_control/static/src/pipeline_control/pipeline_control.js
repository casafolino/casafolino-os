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
            selectedMessageLoadSeq: 0,
            selectedMessageIds: {},
            messageContext: null,
            partnerSearchQuery: "",
            leadSearchQuery: "",
            dossierSearchQuery: "",
            partnerSearchResults: [],
            leadSearchResults: [],
            dossierSearchResults: [],
            entitySearchQuery: "",
            entitySearchResults: [],
            entitySearchLoading: false,
            entityDetail: null,
            entityDetailLoading: false,
            selectedEntityKey: "",
            aiDraftBody: "",
            aiDraftLoading: false,
            aiInstruction: "",
            aiComposerMode: "reply",
            aiComposerTone: "professional",
            data: {
                kpis: [],
                lanes: [],
                b2b_registrations: { kpis: [], rows: [] },
                followup: { kpis: [], columns: [], routes: [], timeline: [] },
                post_fair: { kpis: [], columns: [], timeline: [], fair_options: [] },
                pipeline: [],
                inbox: { kpis: [], ai_status: {}, to_reply: [], waiting_customer: [] },
                dossiers: [],
                operations: { tasks: [], shipments: [], samples: [], entities: [], ai_queue: [] },
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
            
            // Auto-select first message in Inbox if not set or not in current list
            const allInbox = this.allInboxRows;
            if (allInbox.length && (!this.state.selectedMessageId || !allInbox.find(m => m.id === this.state.selectedMessageId))) {
                await this.selectMessage(allInbox[0].id);
            }

            const dossiers = this.state.data.dossiers || [];
            if (this.state.activeView === "dossiers" && dossiers.length) {
                const activeExists = dossiers.some((row) => row.id === this.state.activeDossierId);
                if (!this.state.activeDossierId || !activeExists) {
                    this.state.activeDossierId = dossiers[0].id;
                    await this.loadDossierTimeline(dossiers[0].id);
                }
            }
        } catch (error) {
            this.state.error = error.message || String(error);
        } finally {
            this.state.loading = false;
        }
    }

    async selectMessage(messageId) {
        const loadSeq = (this.state.selectedMessageLoadSeq || 0) + 1;
        this.state.selectedMessageLoadSeq = loadSeq;
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
            const bodyInfo = await this.orm.call("cf.pipeline.control", "get_message_body", [messageId]);
            if (this.state.selectedMessageId !== messageId || this.state.selectedMessageLoadSeq !== loadSeq) {
                return;
            }
            if (bodyInfo?.found) {
                this.state.selectedMessageBody = bodyInfo.body_html || `<pre>${bodyInfo.body_plain || ''}</pre>` || _t("Nessun contenuto.");
                if (!bodyInfo.downloaded && bodyInfo.fetch_error_msg) {
                    this.notification.add(bodyInfo.fetch_error_msg, { type: "warning" });
                }
            } else {
                this.state.selectedMessageBody = bodyInfo?.message || _t("Impossibile caricare il corpo del messaggio.");
            }

            // Fetch sidebar context database info
            const context = await this.orm.call("cf.pipeline.control", "get_message_context_info", [messageId]);
            if (this.state.selectedMessageId !== messageId || this.state.selectedMessageLoadSeq !== loadSeq) {
                return;
            }
            this.state.messageContext = context;
        } catch (error) {
            if (this.state.selectedMessageId !== messageId || this.state.selectedMessageLoadSeq !== loadSeq) {
                return;
            }
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
            if (actionType === 'keep') {
                const result = await this.orm.call("cf.pipeline.control", "mass_keep_senders", [ids]);
                this.notification.add(_t("Mittenti tenuti: ") + (result?.count || ids.length), { type: "success" });
            } else if (actionType === 'dismiss') {
                const result = await this.orm.call("cf.pipeline.control", "mass_dismiss_senders", [ids]);
                this.notification.add(_t("Mittenti scartati: ") + (result?.count || ids.length), { type: "success" });
            } else if (actionType === 'snooze_tomorrow') {
                const result = await this.orm.call("cf.pipeline.control", "mass_snooze_tomorrow", [ids]);
                this.notification.add(_t("Reminder domani creati: ") + (result?.count || 0), { type: "success" });
            } else if (actionType === 'archive') {
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
            await this.loadData();
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
                await this.loadData();
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
            const res = await this.orm.call("cf.pipeline.control", "generate_ai_draft", [
                this.state.selectedMessageId,
                this.state.aiInstruction,
                this.state.aiComposerMode,
                this.state.aiComposerTone,
            ]);
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

    setAIComposerPreset(mode, instruction = "", tone = "professional") {
        this.state.aiComposerMode = mode;
        this.state.aiComposerTone = tone;
        this.state.aiInstruction = instruction;
        this.state.aiDraftBody = "";
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
                await this.loadData();
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
                await this.loadData();
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
                await this.loadData();
                await this.selectMessage(this.state.selectedMessageId);
            } else {
                this.notification.add(_t("Associazione fallita"), { type: "danger" });
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    async linkDossierToMessage(projectId, assistantSuggestion = null) {
        if (!this.state.selectedMessageId) return;
        try {
            const args = [this.state.selectedMessageId, projectId];
            if (assistantSuggestion) {
                args.push({
                    project_id: assistantSuggestion.project_id || false,
                    confidence: assistantSuggestion.confidence || 0,
                    confidence_band: assistantSuggestion.confidence_band || "",
                    provider: assistantSuggestion.provider || "",
                    department: assistantSuggestion.department || "",
                    department_label: assistantSuggestion.department_label || "",
                    reason: assistantSuggestion.reason || "",
                    next_action: assistantSuggestion.next_action || "",
                    route_summary: assistantSuggestion.route_summary || "",
                    operating_stage: assistantSuggestion.operating_stage || "",
                    task_quick_action: assistantSuggestion.task_quick_action || "",
                });
            }
            const success = await this.orm.call("cf.pipeline.control", "link_dossier_to_message", args);
            if (success) {
                this.notification.add(_t("Email associata al dossier con successo"), { type: "success" });
                await this.loadData();
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

    async onEntitySearch(ev) {
        const query = ev.target.value;
        this.state.entitySearchQuery = query;
        if (query.length < 2) {
            this.state.entitySearchResults = [];
            this.state.entityDetail = null;
            this.state.selectedEntityKey = "";
            return;
        }
        this.state.entitySearchLoading = true;
        try {
            this.state.entitySearchResults = await this.orm.call("cf.pipeline.control", "search_entity_360", [query, 12]);
            if (this.state.entitySearchResults.length) {
                await this.selectEntity360(this.state.entitySearchResults[0]);
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        } finally {
            this.state.entitySearchLoading = false;
        }
    }

    async selectEntity360(entity) {
        if (!entity || !entity.model || !entity.res_id) {
            return;
        }
        this.state.selectedEntityKey = `${entity.model}-${entity.res_id}`;
        this.state.entityDetailLoading = true;
        try {
            const detail = await this.orm.call("cf.pipeline.control", "get_entity_360_detail", [entity.model, entity.res_id]);
            if (detail?.found) {
                this.state.entityDetail = detail;
            } else {
                this.state.entityDetail = null;
                this.notification.add(detail?.error || _t("Entità non trovata"), { type: "warning" });
            }
        } catch (error) {
            this.state.entityDetail = null;
            this.notification.add(error.message || String(error), { type: "danger" });
        } finally {
            this.state.entityDetailLoading = false;
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
            await this.loadData();
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

    async newTask() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Task veloce"),
            res_model: "cf.pipeline.quick.task.wizard",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_quick_kind: "todo",
            },
        });
    }

    async newCallTask() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Task veloce da chiamata"),
            res_model: "cf.pipeline.quick.task.wizard",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_quick_kind: "call",
            },
        });
    }

    async newCatalogTask() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Task catalogo"),
            res_model: "cf.pipeline.quick.task.wizard",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_quick_kind: "catalog",
            },
        });
    }

    async newSampleTask() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Task veloce campionatura"),
            res_model: "cf.pipeline.quick.task.wizard",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_quick_kind: "sample",
            },
        });
    }

    async openTasks() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Task / To-do operativi"),
            res_model: "project.task",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            context: {
                search_default_my_tasks: 1,
            },
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
            await this.loadData();
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
    }

    get selectedMessage() {
        if (!this.state.selectedMessageId) return null;
        return this.allInboxRows.find(m => m.id === this.state.selectedMessageId) || null;
    }

    get activeMessageContext() {
        const context = this.state.messageContext;
        if (!context || !this.state.selectedMessageId) {
            return null;
        }
        if (context.message_id && context.message_id !== this.state.selectedMessageId) {
            return null;
        }
        return context;
    }

    get navItems() {
        return [
            { id: "control", label: "Console", count: this.totalLaneCount },
            { id: "followup", label: "Follow-up", count: this.state.data.followup?.kpis?.[0]?.value || 0 },
            { id: "fair", label: "Post-Fiera", count: this.state.data.post_fair?.fair ? this.state.data.post_fair.kpis?.[0]?.value : 0 },
            { id: "inbox", label: "Inbox", count: this.state.data.inbox?.kpis?.[0]?.value || 0 },
            { id: "pipeline", label: "Pipeline", count: this.pipelineCount },
            { id: "tasks", label: "Task", count: this.taskCount },
            { id: "dossiers", label: "Dossier", count: this.state.data.dossiers?.length || 0 },
        ];
    }

    get totalLaneCount() {
        return (this.state.data.lanes || []).reduce((sum, lane) => sum + (lane.count || 0), 0);
    }

    get primaryControlLanes() {
        return (this.state.data.lanes || []).slice(0, 2);
    }

    get secondaryControlLanes() {
        return (this.state.data.lanes || []).slice(2);
    }

    get consoleMailRows() {
        return [
            ...(this.state.data.inbox?.to_reply || []),
            ...(this.state.data.inbox?.waiting_customer || []),
        ].slice(0, 7);
    }

    get consoleFocusMail() {
        return this.consoleMailRows[0] || null;
    }

    get consoleHotItems() {
        const lanes = this.state.data.lanes || [];
        return lanes.flatMap((lane) => lane.items || []).slice(0, 6);
    }

    get consolePipelineColumns() {
        return (this.state.data.pipeline || []).slice(0, 5);
    }

    get operations() {
        return this.state.data.operations || {};
    }

    get consoleTasks() {
        return this.operations.tasks || [];
    }

    get consoleShipments() {
        return this.operations.shipments || [];
    }

    get consoleSamples() {
        return this.operations.samples || [];
    }

    get consoleEntities() {
        return this.operations.entities || [];
    }

    get consoleAIQueue() {
        return this.operations.ai_queue || [];
    }

    get entity360Sections() {
        const detail = this.state.entityDetail;
        if (!detail?.sections) {
            return [];
        }
        const config = [
            ["leads", "Lead e pipeline"],
            ["mails", "Mail recenti"],
            ["dossiers", "Dossier"],
            ["tasks", "Task aperte"],
            ["samples", "Campionature"],
            ["shipments", "Tracking spedizioni"],
            ["quotes", "Preventivi / ordini"],
            ["contacts", "Contatti azienda"],
        ];
        return config
            .map(([key, label]) => ({
                key,
                label,
                rows: detail.sections[key] || [],
            }))
            .filter((section) => section.rows.length);
    }

    get hasConsoleTracking() {
        return Boolean(this.consoleShipments.length || this.consoleSamples.length);
    }

    get taskCount() {
        return this.consoleTasks.length + this.consoleShipments.length + this.consoleSamples.length;
    }

    get pipelineCount() {
        return (this.state.data.pipeline || []).reduce((sum, column) => sum + (column.count || 0), 0);
    }

    get inboxFilterOptions() {
        const rows = this.allInboxRows;
        return [
            { id: "all", label: "Tutti", count: rows.length },
            { id: "pending", label: "Da decidere", count: rows.filter((row) => row.sender_decision === "pending").length },
            { id: "ai_safe", label: "AI sicura", count: rows.filter((row) => row.ai_safe_to_apply).length },
            { id: "urgent", label: "Urgenti", count: rows.filter((row) => row.urgency === "high").length },
            { id: "commercial", label: "Commerciale", count: rows.filter((row) => row.workstream === "commercial").length },
            { id: "logistics", label: "Logistica", count: rows.filter((row) => row.workstream === "logistics").length },
            { id: "admin", label: "Admin", count: rows.filter((row) => row.workstream === "admin").length },
            { id: "materials", label: "Materiali", count: rows.filter((row) => row.workstream === "materials").length },
            { id: "samples", label: "Campioni", count: rows.filter((row) => row.workstream === "samples").length },
            { id: "no_lead", label: "Da collegare", count: rows.filter((row) => !row.lead_id || !row.partner_id).length },
        ];
    }

    get inboxAIStatus() {
        return this.state.data.inbox?.ai_status || {};
    }

    get filteredToReplyRows() {
        return this.filterInboxRows(this.state.data.inbox?.to_reply || []);
    }

    get filteredWaitingRows() {
        return this.filterInboxRows(this.state.data.inbox?.waiting_customer || []);
    }

    get groupedToReplyRows() {
        return this.groupInboxRows(this.filteredToReplyRows);
    }

    get groupedWaitingRows() {
        return this.groupInboxRows(this.filteredWaitingRows);
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
        if (filter === "pending") {
            return rows.filter((row) => row.sender_decision === "pending");
        }
        if (filter === "ai_safe") {
            return rows.filter((row) => row.ai_safe_to_apply);
        }
        if (filter === "kept") {
            return rows.filter((row) => row.sender_decision === "kept");
        }
        if (["commercial", "logistics", "admin", "materials", "samples"].includes(filter)) {
            return rows.filter((row) => row.workstream === filter);
        }
        if (filter === "no_lead") {
            return rows.filter((row) => !row.lead_id || !row.partner_id);
        }
        if (filter === "with_lead") {
            return rows.filter((row) => row.lead_id);
        }
        if (filter === "ai_action") {
            return rows.filter((row) => row.needs_action);
        }
        if (filter === "attachments") {
            return rows.filter((row) => row.has_attachments);
        }
        return rows;
    }

    groupInboxRows(rows) {
        const buckets = [
            { key: "today", label: _t("Oggi"), rows: [] },
            { key: "this_week", label: _t("Questa settimana"), rows: [] },
            { key: "last_week", label: _t("Scorsa settimana"), rows: [] },
            { key: "older", label: _t("Il resto"), rows: [] },
        ];
        const byKey = Object.fromEntries(buckets.map((bucket) => [bucket.key, bucket]));
        for (const row of rows || []) {
            const key = row.date_bucket || "older";
            (byKey[key] || byKey.older).rows.push(row);
        }

        const items = [];
        for (const bucket of buckets) {
            if (!bucket.rows.length) {
                continue;
            }
            items.push({
                type: "date_group",
                key: "date-group-" + bucket.key,
                label: bucket.label,
                count: bucket.rows.length,
            });
            for (const row of bucket.rows) {
                items.push({
                    type: "row",
                    key: "row-" + row.id,
                    row,
                });
            }
        }
        return items;
    }
}

registry.category("actions").add("casafolino_pipeline_control", CFPipelineControl);
