/** @odoo-module **/
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { CFInboxSelector, cfInboxSelectorState } from "@casafolino_mail/inbox_selector/inbox_selector";

export class CFPosizionatoreListController extends ListController {
    static components = {
        ...ListController.components,
        CFInboxSelector,
    };
    static template = "casafolino_mail.PosizionatoreListView";

    setup() {
        super.setup();
        this._unsubscribe = cfInboxSelectorState.subscribe((newUserId) => {
            this._reloadForUser(newUserId);
        });
    }

    async _reloadForUser(userId) {
        if (this.model?.root) {
            this.model.root.context.cf_viewing_as_user_id = userId;
            await this.model.root.load();
        }
    }

    onWillUnmount() {
        this._unsubscribe?.();
    }
}

registry.category("views").add("cf_posizionatore_list", {
    ...listView,
    Controller: CFPosizionatoreListController,
});
