/** @odoo-module **/
import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { useService } from "@web/core/utils/hooks";

export class CasafolinoCrmLeadKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    async createRecord() {
        await this.actionService.doAction({
            type: "ir.actions.client",
            tag: "casafolino_crm_export.open_wizard_new_lead",
        });
    }
}

registry.category("views").add("casafolino_crm_lead_kanban", {
    ...kanbanView,
    Controller: CasafolinoCrmLeadKanbanController,
});
