/** @odoo-module **/
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

const REFRESH_INTERVAL = 30000; // 30 seconds

export class SyncBadge extends Component {
    static template = "casafolino_mail.SyncBadge";
    static props = ["*"];

    setup() {
        this.state = useState({
            globalStatus: 'ok',
            label: '',
            syncing: false,
            loaded: false,
        });

        this._timer = null;

        onMounted(() => {
            this._refresh();
            this._timer = setInterval(() => this._refresh(), REFRESH_INTERVAL);
        });

        onWillUnmount(() => {
            if (this._timer) clearInterval(this._timer);
        });
    }

    get statusClass() {
        const s = this.state.globalStatus;
        if (s === 'error') return 'mv3-sync-badge--error';
        if (s === 'delayed') return 'mv3-sync-badge--delayed';
        return 'mv3-sync-badge--ok';
    }

    get statusIcon() {
        if (this.state.syncing) return 'fa fa-spinner fa-spin';
        const s = this.state.globalStatus;
        if (s === 'error') return 'fa fa-exclamation-triangle';
        if (s === 'delayed') return 'fa fa-clock-o';
        return 'fa fa-check-circle';
    }

    async _refresh() {
        try {
            const res = await rpc('/cf/mail/v3/sync_status');
            this.state.globalStatus = res.global_status || 'ok';
            this.state.loaded = true;

            // Build label from best account (lowest minutes_ago)
            const accounts = res.accounts || [];
            if (accounts.length === 0) {
                this.state.label = 'Nessun account';
                return;
            }
            // Use worst-case minutes for label
            const maxMin = Math.max(...accounts.map(a => a.minutes_ago));
            if (maxMin > 9998) {
                this.state.label = 'Mai sincronizzato';
            } else if (maxMin === 0) {
                this.state.label = 'Sync: adesso';
            } else if (maxMin === 1) {
                this.state.label = 'Sync: 1 min fa';
            } else {
                this.state.label = 'Sync: ' + maxMin + ' min fa';
            }

            // Show error message if any
            const errAcct = accounts.find(a => a.error_message);
            if (errAcct) {
                this.state.label = 'Errore sync: ' + (errAcct.error_message || '').slice(0, 40);
            }
        } catch (e) {
            // Silent — don't break UI
        }
    }

    async forceSync() {
        if (this.state.syncing) return;
        this.state.syncing = true;
        try {
            await rpc('/cf/mail/v3/sync_status/force');
            // Wait a moment then refresh
            setTimeout(() => this._refresh(), 3000);
        } catch (e) {
            console.warn('[sync badge] force sync error:', e);
        }
        // Keep spinner for a few seconds
        setTimeout(() => { this.state.syncing = false; }, 5000);
    }
}
