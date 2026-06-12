/** @odoo-module **/
import { onMounted } from "@odoo/owl";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CFInboxSelector, cfInboxSelectorState } from "@casafolino_mail/inbox_selector/inbox_selector";

export class CFPosizionatoreListController extends ListController {
    static components = {
        ...ListController.components,
        CFInboxSelector,
    };
    static template = "casafolino_mail.PosizionatoreListView";

    setup() {
        super.setup();
        this.action = useService("action");
        this._unsubscribe = cfInboxSelectorState.subscribe((newUserId) => {
            this._reloadForUser(newUserId);
        });
        onMounted(() => {
            if (!this.props.context?.cf_keep_posizionatore_list) {
                this.action.doAction("casafolino_mail.action_mail_v3_client", {
                    clearBreadcrumbs: true,
                });
            }
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
