/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, useSubEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

import { LavagnaHeader } from "./lavagna_header";
import { LavagnaTodayBar } from "./lavagna_today_bar";
import { LavagnaKpiRail } from "./lavagna_kpi_rail";
import { LavagnaKanban } from "./lavagna_kanban";
import { LavagnaPanelMail } from "./lavagna_panel_mail";
import { LavagnaPanelTodo } from "./lavagna_panel_todo";
import { LavagnaPanelActivity } from "./lavagna_panel_activity";
import { LavagnaPanelCalendar } from "./lavagna_panel_calendar";
import { LavagnaPanelMailThread } from "./lavagna_panel_mail_thread";
import { LavagnaDrawerTask } from "./lavagna_drawer_task";
import { LavagnaTimeline } from "./lavagna_timeline";

export class LavagnaMain extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaMain";
    static components = {
        LavagnaHeader, LavagnaTodayBar, LavagnaKpiRail, LavagnaKanban,
        LavagnaPanelMail, LavagnaPanelTodo, LavagnaPanelActivity,
        LavagnaPanelCalendar, LavagnaPanelMailThread, LavagnaDrawerTask, LavagnaTimeline,
    };
    static props = ["*"];

    setup() {
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            data: null,
            error: null,
            todayBarCollapsed: false,
            kpiFilter: null,
            drawerOpen: false,
            drawerTaskId: null,
        });

        this.initiativeId = this.props.action.params.initiative_id;

        useSubEnv({
            lavagnaState: this.state,
            initiativeId: this.initiativeId,
            actions: {
                openTaskDrawer: (taskId) => this.openDrawer(taskId),
                closeTaskDrawer: () => this.closeDrawer(),
                refreshData: () => this.loadData(),
                filterByKpi: (kpi) => this.filterByKpi(kpi),
                clearFilters: () => { this.state.kpiFilter = null; },
                openOdooRecord: (model, resId) => this.openOdooRecord(model, resId),
                moveTask: (taskId, newStageId) => this.moveTask(taskId, newStageId),
                quickAddTask: (name, stageId, tagId) => this.quickAddTask(name, stageId, tagId),
            },
        });

        onWillStart(() => this.loadData());
    }

    async loadData() {
        try {
            this.state.loading = true;
            const data = await rpc(`/casafolino/lavagna/${this.initiativeId}/data`, {});
            if (data.error) {
                this.state.error = data.error;
            } else {
                this.state.data = data;
                this.state.error = null;
            }
        } catch (err) {
            this.state.error = err.message || "Errore caricamento Lavagna";
        } finally {
            this.state.loading = false;
        }
    }

    openDrawer(taskId) {
        this.state.drawerTaskId = taskId;
        this.state.drawerOpen = true;
    }

    closeDrawer() {
        this.state.drawerOpen = false;
        this.state.drawerTaskId = null;
    }

    filterByKpi(kpi) {
        if (this.state.kpiFilter && this.state.kpiFilter.id === kpi.id) {
            this.state.kpiFilter = null;
        } else {
            this.state.kpiFilter = kpi;
        }
    }

    openOdooRecord(model, resId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            res_id: resId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async moveTask(taskId, newStageId) {
        const task = this.state.data.kanban.tasks.find(t => t.id === taskId);
        if (!task) return;
        const oldStageId = task.stage_id;
        task.stage_id = newStageId;
        try {
            await rpc(`/casafolino/lavagna/${this.initiativeId}/move_task`, {
                task_id: taskId, new_stage_id: newStageId,
            });
        } catch (err) {
            task.stage_id = oldStageId;
            this.notification.add(`Errore: ${err.message}`, { type: "danger" });
        }
    }

    async quickAddTask(name, stageId, swimlaneTagId) {
        try {
            const result = await rpc(`/casafolino/lavagna/${this.initiativeId}/quick_add_task`, {
                name, stage_id: stageId, swimlane_tag_id: swimlaneTagId,
            });
            if (result.ok) {
                this.notification.add(`Task "${name}" creato`, { type: "success" });
                await this.loadData();
            }
        } catch (err) {
            this.notification.add(`Errore: ${err.message}`, { type: "danger" });
        }
    }

    backToInitiative() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "cf.initiative",
            res_id: this.initiativeId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    isPanelActive(panelName) {
        if (!this.state.data) return false;
        return (this.state.data.initiative.lavagna_panels || []).includes(panelName);
    }

    toggleTodayBar() {
        this.state.todayBarCollapsed = !this.state.todayBarCollapsed;
    }
}

registry.category("actions").add("casafolino_lavagna", LavagnaMain);
