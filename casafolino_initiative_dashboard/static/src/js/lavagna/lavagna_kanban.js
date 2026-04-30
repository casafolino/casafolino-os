/** @odoo-module **/
import { Component, useState, useEnv } from "@odoo/owl";
import { LavagnaTaskCard } from "./lavagna_task_card";

export class LavagnaKanban extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaKanban";
    static components = { LavagnaTaskCard };
    static props = ["*"];

    setup() {
        this.env = useEnv();
        this.state = useState({
            quickAddStageId: null,
            quickAddTagId: null,
            quickAddName: '',
            showFolded: false,
        });
    }

    get hasSwimlanes() {
        return this.props.data && this.props.data.swimlanes && this.props.data.swimlanes.length > 0;
    }

    get visibleStages() {
        if (!this.props.data) return [];
        return (this.props.data.visible_stages || this.props.data.stages || []);
    }

    get foldedStages() {
        if (!this.props.data) return [];
        return (this.props.data.folded_stages || []);
    }

    get allDisplayStages() {
        if (this.state.showFolded) {
            return [...this.visibleStages, ...this.foldedStages];
        }
        return this.visibleStages;
    }

    getTasksForCell(swimlaneId, stageId) {
        const data = this.props.data;
        if (!data || !data.tasks) return [];
        return data.tasks.filter(t => {
            const matchStage = t.stage_id === stageId;
            if (!matchStage) return false;
            if (swimlaneId === null) return true;
            return (t.cf_tag_ids || []).includes(swimlaneId);
        });
    }

    getTaskCountForStage(stageId) {
        if (!this.props.data || !this.props.data.tasks) return 0;
        return this.props.data.tasks.filter(t => t.stage_id === stageId).length;
    }

    getTaskCountForSwimlane(swimlaneId) {
        if (!this.props.data || !this.props.data.tasks) return 0;
        return this.props.data.tasks.filter(t =>
            (t.cf_tag_ids || []).includes(swimlaneId)).length;
    }

    getSwimlaneColor(colorIdx) {
        const colors = [
            '#6B4A1E', '#C8A43A', '#3498db', '#27ae60', '#e74c3c',
            '#9b59b6', '#f39c12', '#16a085', '#2c3e50', '#e67e22',
        ];
        return colors[(colorIdx || 0) % colors.length];
    }

    toggleShowFolded() {
        this.state.showFolded = !this.state.showFolded;
    }

    // Quick add
    openQuickAdd(ev, stageId, tagId) {
        ev.stopPropagation();
        this.state.quickAddStageId = stageId;
        this.state.quickAddTagId = tagId || null;
        this.state.quickAddName = '';
    }

    cancelQuickAdd() {
        this.state.quickAddStageId = null;
        this.state.quickAddName = '';
    }

    onQuickAddKeydown(ev) {
        if (ev.key === 'Enter' && this.state.quickAddName.trim()) {
            this.env.actions.quickAddTask(
                this.state.quickAddName.trim(),
                this.state.quickAddStageId,
                this.state.quickAddTagId
            );
            this.cancelQuickAdd();
        } else if (ev.key === 'Escape') {
            this.cancelQuickAdd();
        }
    }

    onQuickAddInput(ev) {
        this.state.quickAddName = ev.target.value;
    }

    // Drag & drop
    onDragOver(ev) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = 'move';
    }

    onDragEnter(ev) {
        ev.preventDefault();
        const cell = ev.currentTarget;
        cell.classList.add('o_drag_over');
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
