/** @odoo-module **/
import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

const TABS_ROW1 = [
    { key: 'contact', label: 'Contatto', icon: 'fa-user' },
    { key: 'company', label: 'Azienda', icon: 'fa-building' },
    { key: 'leads', label: 'Lead', icon: 'fa-bullseye' },
    { key: 'timeline', label: 'Timeline', icon: 'fa-clock-o' },
    { key: 'revenue', label: 'Fatturato', icon: 'fa-eur' },
];

const TABS_ROW2 = [
    { key: 'orders', label: 'Ordini', icon: 'fa-shopping-cart' },
    { key: 'notes', label: 'Note', icon: 'fa-sticky-note-o' },
    { key: 'activities', label: 'Attività', icon: 'fa-calendar-check-o' },
    { key: 'products', label: 'Prodotti', icon: 'fa-cube' },
    { key: 'ai_insight', label: 'AI Insight', icon: 'fa-magic' },
];

const LS_KEY = 'cf_mail_v3_360_last_tab';

export class MailV3Insight360TabBar extends Component {
    static template = "casafolino_mail.Insight360TabBar";
    static props = ["*"];

    setup() {
        const savedTab = localStorage.getItem(LS_KEY) || 'contact';
        this.state = useState({
            activeTab: savedTab,
            tabData: {},
            tabLoading: {},
            enriching: false,
            createContactForm: false,
            newContactName: '',
            newContactCompany: '',
            notesValue: '',
            notesSaving: false,
        });
        this._notesSaveTimeout = null;

        onWillStart(() => {
            if (this.props.partnerId) {
                this._loadTab(this.state.activeTab);
            }
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.partnerId !== this.props.partnerId) {
                this.state.tabData = {};
                if (nextProps.partnerId) {
                    this._loadTabForPartner(this.state.activeTab, nextProps.partnerId);
                }
            }
        });
    }

    get tabsRow1() { return TABS_ROW1; }
    get tabsRow2() { return TABS_ROW2; }

    selectTab(key) {
        this.state.activeTab = key;
        localStorage.setItem(LS_KEY, key);
        if (!this.state.tabData[key] && this.props.partnerId) {
            this._loadTab(key);
        } else if (!this.props.partnerId && key === 'ai_insight') {
            this._loadTab(key);
        }
    }

    async _loadTab(key) {
        const partnerId = this.props.partnerId;
        await this._loadTabForPartner(key, partnerId);
    }

    async _loadTabForPartner(key, partnerId) {
        if (this.state.tabLoading[key]) return;
        this.state.tabLoading[key] = true;
        try {
            let endpoint = '/cf/mail/v3/insight360/' + key;
            let params = {};
            if (key === 'ai_insight') {
                params.thread_id = this.props.threadId;
            } else {
                params.partner_id = partnerId;
            }
            const result = await rpc(endpoint, params);
            this.state.tabData[key] = result;
            if (key === 'notes' && result) {
                this.state.notesValue = result.comment_plain || '';
            }
        } catch (e) {
            console.error('[360 tabbar] load tab error:', key, e);
            this.state.tabData[key] = { error: true };
        }
        this.state.tabLoading[key] = false;
    }

    formatCurrency(val) {
        if (!val && val !== 0) return '-';
        return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(val);
    }

    formatDate(dateStr) {
        if (!dateStr) return '-';
        return dateStr.slice(0, 10);
    }

    // ── Enrich from domain ──
    async enrichFromDomain() {
        this.state.enriching = true;
        try {
            const email = this.props.senderEmail || '';
            const domain = email.split('@')[1] || '';
            if (!domain) return;
            // Use existing endpoint pattern
            const result = await rpc('/cf/mail/v3/insight360/create_contact', {
                email: email,
                name: '',
                company_name: domain,
                thread_id: this.props.threadId,
            });
            if (result && result.success && result.partner_id) {
                if (this.props.onPartnerCreated) {
                    this.props.onPartnerCreated(result.partner_id);
                }
            }
        } catch (e) {
            console.error('[360 tabbar] enrich error:', e);
        }
        this.state.enriching = false;
    }

    // ── Create contact ──
    toggleCreateContact() {
        this.state.createContactForm = !this.state.createContactForm;
    }

    onNewContactName(ev) {
        this.state.newContactName = ev.target.value;
    }

    onNewContactCompany(ev) {
        this.state.newContactCompany = ev.target.value;
    }

    async createContact() {
        try {
            const result = await rpc('/cf/mail/v3/insight360/create_contact', {
                email: this.props.senderEmail || '',
                name: this.state.newContactName,
                company_name: this.state.newContactCompany,
                thread_id: this.props.threadId,
            });
            if (result && result.success && result.partner_id) {
                this.state.createContactForm = false;
                if (this.props.onPartnerCreated) {
                    this.props.onPartnerCreated(result.partner_id);
                }
            }
        } catch (e) {
            console.error('[360 tabbar] create contact error:', e);
        }
    }

    // ── Notes ──
    onNotesInput(ev) {
        this.state.notesValue = ev.target.value;
        if (this._notesSaveTimeout) clearTimeout(this._notesSaveTimeout);
        this._notesSaveTimeout = setTimeout(() => this._saveNotes(), 1000);
    }

    async _saveNotes() {
        if (!this.props.partnerId) return;
        this.state.notesSaving = true;
        try {
            await rpc('/cf/mail/v3/insight360/notes', {
                partner_id: this.props.partnerId,
                new_comment: this.state.notesValue,
            });
        } catch (e) {
            console.error('[360 tabbar] save notes error:', e);
        }
        this.state.notesSaving = false;
    }

    getTimelineIcon(type) {
        const icons = {
            email_in: 'fa-envelope text-primary',
            email_out: 'fa-reply text-success',
            lead: 'fa-bullseye text-warning',
            order: 'fa-shopping-cart text-info',
            activity: 'fa-calendar-check-o text-muted',
        };
        return icons[type] || 'fa-circle text-muted';
    }
}
