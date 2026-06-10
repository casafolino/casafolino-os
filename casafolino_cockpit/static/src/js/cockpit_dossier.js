/** @odoo-module **/
import { Component, useState, onMounted, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

export class CockpitDossier extends Component {
    static template = "casafolino_cockpit.CockpitDossier";
    static props = ["*"];

    setup() {
        this.state = useState({
            partner: null,
            initiatives: [],
            messages: [],
            attachments: [],
            loading: true,
            expandedInitId: null,
            feedbackDialog: null,
            feedbackText: "",
        });
        this.notification = useService("notification");
        this.action = useService("action");
        onMounted(() => this._load());
        onWillUpdateProps(nextProps => {
            if (nextProps.partnerId !== this.props.partnerId) this._load(nextProps.partnerId);
        });
    }

    async _load(partnerId) {
        const pid = partnerId || this.props.partnerId;
        if (!pid) return;
        this.state.loading = true;
        this.state.expandedInitId = this.props.expandedInitiativeId || null;

        try {
            const [partnerData, initData, msgData, attData] = await Promise.all([
                rpc("/web/dataset/call_kw", {
                    model: "res.partner", method: "search_read",
                    args: [[["id","=",pid]]],
                    kwargs: { fields: ["id","name","country_id","user_id"], limit: 1 },
                }),
                rpc("/web/dataset/call_kw", {
                    model: "cf.initiative", method: "search_read",
                    args: [[["partner_id","=",pid]]],
                    kwargs: {
                        fields: ["id","name","state","template_id","current_stage_id","progress","traffic_light"],
                        order: "state asc, write_date desc",
                    },
                }),
                rpc("/web/dataset/call_kw", {
                    model: "casafolino.mail.message", method: "search_read",
                    args: [[["partner_id","=",pid]]],
                    kwargs: {
                        fields: ["id","subject","body_plain","email_date","direction","sender_email","sender_name"],
                        order: "email_date desc", limit: 20,
                    },
                }),
                rpc("/web/dataset/call_kw", {
                    model: "ir.attachment", method: "search_read",
                    args: [[["res_model","=","res.partner"],["res_id","=",pid]]],
                    kwargs: {
                        fields: ["id","name","create_date","mimetype"],
                        order: "create_date desc", limit: 50,
                    },
                }),
            ]);

            this.state.partner = partnerData[0] || null;
            this.state.initiatives = initData;
            this.state.messages = this._groupMessages(msgData);
            this.state.attachments = attData;
            await this._loadStageDetails(initData);

        } catch (e) {
            console.error("CockpitDossier load error:", e);
        }
        this.state.loading = false;
    }

    async _loadStageDetails(initiatives) {
        const activeIds = initiatives.filter(i => !["done","cancelled"].includes(i.state)).map(i => i.id);
        if (!activeIds.length) return;

        const [stages, todos] = await Promise.all([
            rpc("/web/dataset/call_kw", {
                model: "cf.initiative.stage", method: "search_read",
                args: [[["initiative_id","in",activeIds]]],
                kwargs: {
                    fields: ["id","name","initiative_id","state","user_id","sequence","require_feedback"],
                    order: "initiative_id asc, sequence asc",
                },
            }),
            rpc("/web/dataset/call_kw", {
                model: "cf.todo", method: "search_read",
                args: [[["initiative_id","in",activeIds]]],
                kwargs: {
                    fields: ["id","name","initiative_id","stage_id","done","assigned_user_id"],
                    order: "sequence asc",
                },
            }),
        ]);

        const sbInit = {}, tbInit = {};
        stages.forEach(s => { const id = s.initiative_id?.[0]; if (id) (sbInit[id] = sbInit[id]||[]).push(s); });
        todos.forEach(t => { const id = t.initiative_id?.[0]; if (id) (tbInit[id] = tbInit[id]||[]).push(t); });

        this.state.initiatives = this.state.initiatives.map(i => ({
            ...i, _stages: sbInit[i.id] || [], _todos: tbInit[i.id] || [],
        }));
    }

    _groupMessages(msgs) {
        const groups = {};
        msgs.forEach(m => {
            const key = (m.subject || "").replace(/^(re:|fwd?:)\s*/gi,"").trim().toLowerCase() || "senza oggetto";
            if (!groups[key]) groups[key] = { subject: m.subject || "(nessun oggetto)", msgs: [], expanded: false };
            groups[key].msgs.push(m);
        });
        return Object.values(groups).sort((a,b) =>
            (b.msgs[0]?.email_date||"").localeCompare(a.msgs[0]?.email_date||"")
        );
    }

    toggleMessageGroup(idx) { this.state.messages[idx].expanded = !this.state.messages[idx].expanded; }
    toggleExpanded(id) { this.state.expandedInitId = this.state.expandedInitId === id ? null : id; }

    async toggleTodo(todo) {
        try {
            const val = todo.done ? false : true;
            await rpc("/web/dataset/call_kw", {
                model: "cf.todo", method: "write",
                args: [[todo.id], { done: val }], kwargs: {},
            });
            await this._loadStageDetails(this.state.initiatives);
        } catch (e) {
            this.notification.add("Errore task: " + (e?.data?.message || e?.message || e), { type: "danger" });
        }
    }

    async closeStage(stage) {
        let feedback = undefined;
        if (stage.require_feedback) {
            feedback = await this._requestFeedback();
            if (feedback === null) return;
        }
        try {
            const kwargs = feedback !== undefined ? { feedback } : {};
            await rpc("/web/dataset/call_kw", {
                model: "cf.initiative.stage", method: "action_complete_stage",
                args: [[stage.id]], kwargs,
            });
            this.notification.add("Fase completata. Testimone passato!", { type: "success" });
            await this._load();
        } catch (e) {
            this.notification.add(e?.data?.message || e?.message || String(e), { type: "danger", sticky: true });
        }
    }

    _requestFeedback() {
        return new Promise(resolve => {
            this.state.feedbackDialog = { resolve };
            this.state.feedbackText = "";
        });
    }

    submitFeedback() {
        const { resolve } = this.state.feedbackDialog;
        this.state.feedbackDialog = null;
        resolve(this.state.feedbackText);
    }

    cancelFeedback() {
        const { resolve } = this.state.feedbackDialog;
        this.state.feedbackDialog = null;
        resolve(null);
    }

    onFeedbackInput(ev) { this.state.feedbackText = ev.target.value; }

    async openNativePartner() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: this.props.partnerId,
            views: [[false,"form"]], target: "current",
        });
    }

    async openNewProjectWizard() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cf.initiative.create.wizard",
            views: [[false,"form"]], target: "new",
            context: { default_partner_id: this.props.partnerId },
        });
    }

    get activeInitiatives() { return this.state.initiatives.filter(i => !["done","cancelled"].includes(i.state)); }
    get closedInitiatives() { return this.state.initiatives.filter(i => ["done","cancelled"].includes(i.state)); }

    formatDate(d) {
        if (!d) return "";
        return new Date(d).toLocaleDateString("it-IT", { day:"2-digit", month:"short", year:"numeric" });
    }

    getInitials(name) {
        if (!name) return "?";
        return name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0,2);
    }

    refresh() { this._load(); }
}
