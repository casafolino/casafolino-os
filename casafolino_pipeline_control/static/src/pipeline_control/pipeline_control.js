/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class CFPipelineControl extends Component {
    static template = "casafolino_pipeline_control.CFPipelineControl";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            error: null,
            activeView: this.props.action?.context?.default_view || "control",
            selectedFairId: false,
            data: {
                kpis: [],
                lanes: [],
                followup: { kpis: [], columns: [], timeline: [] },
                post_fair: { kpis: [], columns: [], timeline: [], fair_options: [] },
                pipeline: [],
                inbox: { to_reply: [], waiting_customer: [] },
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
                await this.action.doAction(result);
                if (result.reload) {
                    await this.loadData();
                }
            }
        } catch (error) {
            this.notification.add(error.message || String(error), { type: "danger" });
        }
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

    get navItems() {
        return [
            { id: "control", label: "Sala Controllo", count: this.totalLaneCount },
            { id: "followup", label: "Follow-up", count: this.state.data.followup?.kpis?.[0]?.value || 0 },
            { id: "fair", label: "Post-Fiera", count: this.state.data.post_fair?.fair ? this.state.data.post_fair.kpis?.[0]?.value : 0 },
            { id: "inbox", label: "Inbox", count: this.state.data.inbox?.to_reply?.length || 0 },
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
}

registry.category("actions").add("casafolino_pipeline_control", CFPipelineControl);
