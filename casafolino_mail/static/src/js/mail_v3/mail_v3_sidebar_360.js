/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class Sidebar360 extends Component {
    static template = "casafolino_mail.Sidebar360";
    static props = ["*"];

    setup() {
        this.state = useState({
            notesValue: (this.props.data && this.props.data.notes) || '',
            commercialExpanded: false,
            commercialData: null,
            commercialLoading: false,
            enriching: false,
        });
        this._notesSaveTimeout = null;
        this._commercialCache = {};
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

    async enrichFromDomain() {
        const personId = this.props.data && this.props.data.person && this.props.data.person.id;
        if (!personId) return;
        this.state.enriching = true;
        try {
            const result = await rpc('/cf/mail/v3/partner/' + personId + '/enrich_domain');
            if (result && result.success && result.company_name) {
                // Update company block in-place
                if (!this.props.data.company) this.props.data.company = {};
                this.props.data.company.name = result.company_name;
                this.props.data.company.id = result.company_id;
            }
        } catch (e) {
            console.error('[360] enrich domain error:', e);
        }
        this.state.enriching = false;
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

    // ── F6: Commercial Context ──────────────────────────────────────

    async toggleCommercialContext() {
        this.state.commercialExpanded = !this.state.commercialExpanded;
        if (this.state.commercialExpanded && !this.state.commercialData) {
            await this._loadCommercialContext();
        }
    }

    async _loadCommercialContext() {
        const partnerId = this.props.data && this.props.data.partner_id;
        if (!partnerId) return;

        if (this._commercialCache[partnerId]) {
            this.state.commercialData = this._commercialCache[partnerId];
            return;
        }

        this.state.commercialLoading = true;
        try {
            const res = await rpc('/cf/mail/v3/partner/' + partnerId + '/commercial_context', {});
            if (res && res.success) {
                this.state.commercialData = res.data;
                this._commercialCache[partnerId] = res.data;
            }
        } catch (e) {
            console.error('[sidebar360] commercial context error:', e);
        }
        this.state.commercialLoading = false;
    }

    openPartnerForm() {
        const partnerId = this.props.data && this.props.data.partner_id;
        if (partnerId && this.props.onQuickAction) {
            this.props.onQuickAction('open_partner');
        }
    }

    // ── F6: Quote Wizard ────────────────────────────────────────────

    async openQuoteWizard() {
        const threadId = this.props.data && this.props.data.thread_id;
        if (!threadId) return;
        try {
            const res = await rpc('/cf/mail/v3/thread/' + threadId + '/quote/open_wizard', {});
            if (res && res.success && res.action) {
                if (this.props.onDoAction) {
                    this.props.onDoAction(res.action);
                }
            }
        } catch (e) {
            console.error('[sidebar360] quote wizard error:', e);
        }
    }
}
