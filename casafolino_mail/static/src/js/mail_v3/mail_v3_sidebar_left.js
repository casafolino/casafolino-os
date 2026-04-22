/** @odoo-module **/
import { Component, useState } from "@odoo/owl";

export class SidebarLeft extends Component {
    static template = "casafolino_mail.SidebarLeft";
    static props = ["*"];

    setup() {
        this.state = useState({
            selectedAccountId: null,
            activeFolder: 'inbox',
        });
    }

    // Account colors — fixed palette
    _accountColors = ['#5A6E3A', '#F39C12', '#9B59B6', '#2980B9', '#E74C3C'];

    getAccountColor(index) {
        return this._accountColors[index % this._accountColors.length];
    }

    selectAll() {
        this.state.selectedAccountId = null;
        this.state.activeFolder = 'inbox';
        this.props.onAccountChange(null);
    }

    selectAccount(accountId) {
        this.state.selectedAccountId = accountId;
        this.state.activeFolder = 'inbox';
        this.props.onAccountChange([accountId]);
    }

    selectFolder(folder) {
        this.state.activeFolder = folder;
        if (this.props.onFolderChange) {
            this.props.onFolderChange(folder);
        }
    }

    onOpenSettings() {
        if (this.props.onOpenSettings) {
            this.props.onOpenSettings();
        }
    }

    onComposeNew() {
        if (this.props.onComposeNew) {
            this.props.onComposeNew();
        }
    }

    get totalUnread() {
        const accounts = this.props.accounts || [];
        return accounts.reduce((sum, a) => sum + (a.unread_count || 0), 0);
    }
}
