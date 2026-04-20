/** @odoo-module **/
import { Component, useState } from "@odoo/owl";

export class Sidebar360 extends Component {
    static template = "casafolino_mail.Sidebar360";
    static props = ["*"];

    setup() {
        this.state = useState({
            notesValue: (this.props.data && this.props.data.notes) || '',
        });
        this._notesSaveTimeout = null;
    }

    getHotnessClass(tier) {
        return 'mv3-hotness-badge--' + (tier || 'dormant');
    }

    formatCurrency(val) {
        if (!val && val !== 0) return '-';
        return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(val);
    }

    onQuickAction(key) {
        if (this.props.onQuickAction) {
            this.props.onQuickAction(key);
        }
    }

    dismissNba() {
        const partnerId = this.props.data && this.props.data.nba && this.props.data.nba.partner_id;
        if (partnerId && this.props.onDismissNba) {
            this.props.onDismissNba(partnerId);
        }
    }

    pinHot() {
        const partnerId = this.props.data && this.props.data.partner_id;
        if (partnerId && this.props.onFeedback) {
            this.props.onFeedback(partnerId, 'pinned_hot');
        }
    }

    pinIgnore() {
        const partnerId = this.props.data && this.props.data.partner_id;
        if (partnerId && this.props.onFeedback) {
            this.props.onFeedback(partnerId, 'pinned_ignore');
        }
    }

    onNotesInput(ev) {
        this.state.notesValue = ev.target.value;
        if (this._notesSaveTimeout) clearTimeout(this._notesSaveTimeout);
        this._notesSaveTimeout = setTimeout(() => {
            this._saveNotes();
        }, 1000);
    }

    _saveNotes() {
        const partnerId = this.props.data && this.props.data.partner_id;
        if (partnerId && this.props.onSaveNotes) {
            this.props.onSaveNotes(partnerId, this.state.notesValue);
        }
    }

    getDirectionIcon(direction) {
        return direction === 'outbound' ? '↗️' : '↙️';
    }

    formatTimelineDate(dateStr) {
        if (!dateStr) return '';
        return dateStr;
    }
}
