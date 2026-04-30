/** @odoo-module **/
import { Component, useEnv } from "@odoo/owl";

export class LavagnaTodayBar extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaTodayBar";
    static props = ["*"];

    setup() {
        this.env = useEnv();
    }

    onItemClick(item) {
        if (item.task_id) {
            this.env.actions.openTaskDrawer(item.task_id);
        }
    }
}
