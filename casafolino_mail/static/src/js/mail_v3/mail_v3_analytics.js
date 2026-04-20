/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class MailV3Analytics extends Component {
    static template = "casafolino_mail.MailV3Analytics";
    static props = ["*"];

    setup() {
        this.state = useState({
            data: null,
            loading: true,
            days: 30,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const res = await rpc('/cf/mail/v3/analytics', { days: this.state.days });
            this.state.data = res;
        } catch (e) {
            console.error('[mail v3] analytics error:', e);
        }
        this.state.loading = false;
    }

    async onDaysChange(ev) {
        this.state.days = parseInt(ev.target.value);
        await this.loadData();
    }
}

registry.category("actions").add("cf_mail_v3_analytics", MailV3Analytics);
