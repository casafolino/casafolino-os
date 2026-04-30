/** @odoo-module **/
/**
 * F2.4: Initiative = Lavagna (always).
 * Patches ListController and KanbanController so that for cf.initiative:
 * - openRecord → opens Lavagna OWL cockpit (not form)
 * - createRecord → opens wizard premium 5-step (not blank form)
 */
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { KanbanController } from "@web/views/kanban/kanban_controller";

function isInitiativeView(controller) {
    try {
        return controller.props.resModel === 'cf.initiative';
    } catch {
        return false;
    }
}

// Patch List
patch(ListController.prototype, {
    async openRecord(record) {
        if (isInitiativeView(this) || record.resModel === 'cf.initiative') {
            return this.actionService.doAction({
                type: 'ir.actions.client',
                tag: 'casafolino_lavagna',
                name: 'Lavagna',
                params: { initiative_id: record.resId },
            });
        }
        return super.openRecord(...arguments);
    },

    async createRecord() {
        if (isInitiativeView(this)) {
            return this.actionService.doAction(
                'casafolino_initiative_dashboard.action_cf_initiative_dashboard_wizard'
            );
        }
        return super.createRecord(...arguments);
    },
});

// Patch Kanban
patch(KanbanController.prototype, {
    async openRecord(record) {
        if (isInitiativeView(this) || record.resModel === 'cf.initiative') {
            return this.actionService.doAction({
                type: 'ir.actions.client',
                tag: 'casafolino_lavagna',
                name: 'Lavagna',
                params: { initiative_id: record.resId },
            });
        }
        return super.openRecord(...arguments);
    },

    async createRecord() {
        if (isInitiativeView(this)) {
            return this.actionService.doAction(
                'casafolino_initiative_dashboard.action_cf_initiative_dashboard_wizard'
            );
        }
        return super.createRecord(...arguments);
    },
});
