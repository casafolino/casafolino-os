/** @odoo-module **/
import { Component, useState, useEnv } from "@odoo/owl";
import { LavagnaTaskCard } from "./lavagna_task_card";

export class LavagnaKanban extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaKanban";
    static components = { LavagnaTaskCard };
    static props = ["*"];

    setup() {
        this.env = useEnv();
        this.localState = useState({
            quickAddStageId: null,
            quickAddTagId: null,
            quickAddName: '',
            dragTaskId: null,
        });
    }

    getTasksForCell(stageId, swimlaneTagId) {
        const data = this.props.data;
        if (!data || !data.tasks) return [];
        let tasks = data.tasks.filter(t => t.stage_id === stageId);
        if (swimlaneTagId) {
            tasks = tasks.filter(t =>
                t.cf_tag_ids && t.cf_tag_ids.includes(swimlaneTagId));
        }
        // KPI filter
        const kpiFilter = this.env.lavagnaState.kpiFilter;
        if (kpiFilter && kpiFilter.target_model === 'project.task') {
            // Filter by stage name matching KPI domain hint
            // For now: no additional filter (KPI highlights, doesn't hide)
        }
        return tasks;
    }

    getUnsortedTasks(stageId) {
        // Tasks without any swimlane tag (when swimlanes are active)
        const data = this.props.data;
        if (!data || !data.tasks || !data.swimlanes.length) return [];
        const allTagIds = data.swimlanes.map(s => s.id);
        return data.tasks.filter(t =>
            t.stage_id === stageId &&
            (!t.cf_tag_ids || !t.cf_tag_ids.some(id => allTagIds.includes(id)))
        );
    }

    hasSwimlines() {
        return this.props.data && this.props.data.swimlanes && this.props.data.swimlanes.length > 0;
    }

    // Quick add
    startQuickAdd(stageId, tagId) {
        this.localState.quickAddStageId = stageId;
        this.localState.quickAddTagId = tagId || null;
        this.localState.quickAddName = '';
    }

    cancelQuickAdd() {
        this.localState.quickAddStageId = null;
        this.localState.quickAddName = '';
    }

    onQuickAddKeydown(ev) {
        if (ev.key === 'Enter' && this.localState.quickAddName.trim()) {
            this.env.actions.quickAddTask(
                this.localState.quickAddName.trim(),
                this.localState.quickAddStageId,
                this.localState.quickAddTagId
            );
            this.cancelQuickAdd();
        } else if (ev.key === 'Escape') {
            this.cancelQuickAdd();
        }
    }

    onQuickAddInput(ev) {
        this.localState.quickAddName = ev.target.value;
    }

    // Drag & drop (HTML5 native)
    onDragStart(ev, taskId) {
        this.localState.dragTaskId = taskId;
        ev.dataTransfer.effectAllowed = 'move';
        ev.dataTransfer.setData('text/plain', String(taskId));
        ev.target.classList.add('o_dragging');
    }

    onDragEnd(ev) {
        ev.target.classList.remove('o_dragging');
        this.localState.dragTaskId = null;
    }

    onDragOver(ev) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = 'move';
    }

    onDragEnter(ev) {
        ev.preventDefault();
        ev.currentTarget.classList.add('o_drag_over');
    }

    onDragLeave(ev) {
        ev.currentTarget.classList.remove('o_drag_over');
    }

    onDrop(ev, stageId) {
        ev.preventDefault();
        ev.currentTarget.classList.remove('o_drag_over');
        const taskId = parseInt(ev.dataTransfer.getData('text/plain'));
        if (taskId && stageId) {
            this.env.actions.moveTask(taskId, stageId);
        }
    }
}
