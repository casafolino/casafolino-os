/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

// Sub-components
import { SidebarLeft } from "./mail_v3_sidebar_left";
import { ThreadList } from "./mail_v3_thread_list";
import { ReadingPane } from "./mail_v3_reading_pane";
import { Sidebar360 } from "./mail_v3_sidebar_360";
import { ComposeWizard } from "./mail_v3_compose";

export class MailV3Client extends Component {
    static template = "casafolino_mail.MailV3Client";
    static components = { SidebarLeft, ThreadList, ReadingPane, Sidebar360, ComposeWizard };
    static props = ["*"];

    setup() {
        this.state = useState({
            accounts: [],
            selectedAccountIds: null,
            threads: [],
            selectedThreadId: null,
            messages: [],
            selectedPartner: null,
            sidebar360Data: null,
            loading: { threads: false, messages: false, sidebar: false },
            totalThreads: 0,
            composeVisible: false,
            composeMode: 'new',
            composeReplyToId: null,
            composeDraftId: null,
            composePrefilled: {},
        });

        onWillStart(async () => {
            await this.loadAccounts();
            await this.loadThreads();
        });
    }

    async loadAccounts() {
        try {
            const res = await rpc('/cf/mail/v3/accounts/summary');
            this.state.accounts = res.accounts || [];
        } catch (e) {
            console.error('[mail v3] loadAccounts error:', e);
        }
    }

    async loadThreads() {
        this.state.loading.threads = true;
        try {
            const res = await rpc('/cf/mail/v3/threads/list', {
                account_ids: this.state.selectedAccountIds,
                state: 'keep',
                limit: 50,
                offset: 0,
                filters: {},
            });
            this.state.threads = res.threads || [];
            this.state.totalThreads = res.total || 0;
        } catch (e) {
            console.error('[mail v3] loadThreads error:', e);
        }
        this.state.loading.threads = false;
    }

    async selectThread(threadId) {
        this.state.selectedThreadId = threadId;
        this.state.loading.messages = true;
        try {
            const res = await rpc('/cf/mail/v3/thread/' + threadId + '/messages');
            this.state.messages = res.messages || [];

            // Mark thread as read
            await rpc('/cf/mail/v3/thread/' + threadId + '/mark_all_read');

            // Update thread unread count locally
            const thread = this.state.threads.find(t => t.id === threadId);
            if (thread) {
                thread.unread_count = 0;
                thread.is_read = true;
            }

            // Load sidebar 360 for main partner
            const inbound = this.state.messages.find(m => m.direction_computed === 'inbound' || m.direction === 'inbound');
            const partnerId = inbound ? inbound.partner_id : null;
            if (partnerId) {
                this.state.loading.sidebar = true;
                const sidebar = await rpc('/cf/mail/v3/partner/' + partnerId + '/sidebar_360');
                this.state.sidebar360Data = sidebar;
                this.state.selectedPartner = partnerId;
                this.state.loading.sidebar = false;
            } else {
                this.state.sidebar360Data = null;
                this.state.selectedPartner = null;
            }
        } catch (e) {
            console.error('[mail v3] selectThread error:', e);
        }
        this.state.loading.messages = false;
    }

    onAccountChange(accountIds) {
        this.state.selectedAccountIds = accountIds;
        this.loadThreads();
    }

    async onMessageAction(action, msgId) {
        try {
            await rpc('/cf/mail/v3/message/' + msgId + '/' + action);
            // Reload messages
            if (this.state.selectedThreadId) {
                const res = await rpc('/cf/mail/v3/thread/' + this.state.selectedThreadId + '/messages');
                this.state.messages = res.messages || [];
            }
        } catch (e) {
            console.error('[mail v3] message action error:', e);
        }
    }

    async openCompose(mode, replyToId) {
        const accountId = this.state.selectedAccountIds
            ? this.state.selectedAccountIds[0]
            : (this.state.accounts.length > 0 ? this.state.accounts[0].id : null);

        try {
            const res = await rpc('/cf/mail/v3/draft/create', {
                account_id: accountId,
                in_reply_to_message_id: replyToId || false,
                mode: mode || 'new',
            });
            this.state.composeDraftId = res.draft_id;
            this.state.composePrefilled = res.prefilled || {};
            this.state.composeMode = mode || 'new';
            this.state.composeReplyToId = replyToId || null;
            this.state.composeVisible = true;
        } catch (e) {
            console.error('[mail v3] openCompose error:', e);
        }
    }

    closeCompose() {
        this.state.composeVisible = false;
        this.state.composeDraftId = null;
    }

    async onComposeSent() {
        this.state.composeVisible = false;
        this.state.composeDraftId = null;
        // Reload threads
        await this.loadThreads();
        if (this.state.selectedThreadId) {
            await this.selectThread(this.state.selectedThreadId);
        }
    }
}

registry.category("actions").add("cf_mail_v3_client", MailV3Client);
