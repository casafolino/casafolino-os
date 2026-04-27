/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class DismissedSenders extends Component {
    static template = "casafolino_mail.DismissedSenders";
    static props = ["*"];

    setup() {
        this.state = useState({
            dismissed: [],
            search: '',
            loading: false,
            restoreDialog: null,  // email being restored
            restoreDays: 0,
        });

        onWillStart(async () => {
            await this.loadDismissed();
        });
    }

    async loadDismissed() {
        this.state.loading = true;
        try {
            const res = await rpc('/cf/mail/v3/sender_decision/list_dismissed', {
                search: this.state.search,
            });
            this.state.dismissed = res.dismissed || [];
        } catch (e) {
            console.error('[dismissed senders] load error:', e);
        }
        this.state.loading = false;
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value;
        clearTimeout(this._searchTimeout);
        this._searchTimeout = setTimeout(() => this.loadDismissed(), 300);
    }

    openRestoreDialog(email) {
        this.state.restoreDialog = email;
        this.state.restoreDays = 0;
    }

    closeRestoreDialog() {
        this.state.restoreDialog = null;
    }

    onRestoreDaysChange(ev) {
        this.state.restoreDays = parseInt(ev.target.value) || 0;
    }

    async confirmRestore() {
        const email = this.state.restoreDialog;
        if (!email) return;
        try {
            await rpc('/cf/mail/v3/sender_decision/restore', {
                email: email,
                recover_days: this.state.restoreDays,
            });
            this.state.restoreDialog = null;
            await this.loadDismissed();
            if (this.props.onRestored) this.props.onRestored();
        } catch (e) {
            console.error('[dismissed senders] restore error:', e);
        }
    }

    formatDate(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        return d.toLocaleDateString('it-IT', {
            day: '2-digit', month: 'short', year: 'numeric',
        });
    }
}
