/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

patch(ListController.prototype, {
    async openRecord(record) {
        const ctx = this.props.context || {};
        if (ctx.open_lavagna_on_click && record.resModel === 'cf.initiative') {
            return this.actionService.doAction({
                type: 'ir.actions.client',
                tag: 'casafolino_lavagna',
                name: 'Lavagna',
                params: { initiative_id: record.resId },
            });
        }
        return super.openRecord(...arguments);
    },
});
