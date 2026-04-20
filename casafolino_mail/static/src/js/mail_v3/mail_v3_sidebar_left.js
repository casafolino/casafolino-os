/** @odoo-module **/
import { Component, useState } from "@odoo/owl";

export class SidebarLeft extends Component {
    static template = "casafolino_mail.SidebarLeft";
    static props = ["*"];

    setup() {
        this.state = useState({
            selectedAccountId: null,
        });
    }

    selectAll() {
        this.state.selectedAccountId = null;
        this.props.onAccountChange(null);
    }

    selectAccount(accountId) {
        this.state.selectedAccountId = accountId;
        this.props.onAccountChange([accountId]);
    }

    onComposeNew() {
        if (this.props.onComposeNew) {
            this.props.onComposeNew();
        }
    }
}
