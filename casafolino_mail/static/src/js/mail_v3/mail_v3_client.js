/** @odoo-module **/
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

import { SidebarLeft } from "./mail_v3_sidebar_left";
import { ThreadList } from "./mail_v3_thread_list";
import { ReadingPane } from "./mail_v3_reading_pane";
import { Sidebar360 } from "./mail_v3_sidebar_360";
import { ReplyAssistant } from "./mail_v3_reply_assistant";

export class MailV3Client extends Component {
    static template = "casafolino_mail.MailV3Client";
    static components = { SidebarLeft, ThreadList, ReadingPane, Sidebar360, ReplyAssistant };
    static props = ["*"];

    setup() {
        this.actionService = useService("action");

        this.state = useState({
            accounts: [],
            selectedAccountIds: null,
            activeFolder: 'inbox',
            threads: [],
            selectedThreadId: null,
            selectedThreadIndex: -1,
            messages: [],
            selectedPartner: null,
            sidebar360Data: null,
            loading: { threads: false, messages: false, sidebar: false },
            totalThreads: 0,
            // Search
            searchQuery: '',
            searchResults: null,
            // Reply assistant
            replyAssistantVisible: false,
            replyAssistantMessageId: null,
            // Settings drawer
            settingsVisible: false,
            // Shortcuts help
            shortcutsHelpVisible: false,
        });

        this._keyHandler = this._onKeyDown.bind(this);

        onWillStart(async () => {
            await this.loadAccounts();
            await this.loadThreads();
        });

        onMounted(() => {
            document.addEventListener('keydown', this._keyHandler);
        });

        onWillUnmount(() => {
            document.removeEventListener('keydown', this._keyHandler);
        });
    }

    // ── Data loading ────────────────────────────────────────────

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
                folder: this.state.activeFolder === 'inbox' ? null : this.state.activeFolder,
            });
            this.state.threads = res.threads || [];
            this.state.totalThreads = res.total || 0;
            this.state.searchResults = null;
        } catch (e) {
            console.error('[mail v3] loadThreads error:', e);
        }
        this.state.loading.threads = false;
    }

    async selectThread(threadId) {
        this.state.selectedThreadId = threadId;
        const idx = this.state.threads.findIndex(t => t.id === threadId);
        this.state.selectedThreadIndex = idx;
        this.state.loading.messages = true;
        try {
            const res = await rpc('/cf/mail/v3/thread/' + threadId + '/messages');
            this.state.messages = res.messages || [];

            await rpc('/cf/mail/v3/thread/' + threadId + '/mark_all_read');

            const thread = this.state.threads.find(t => t.id === threadId);
            if (thread) {
                thread.unread_count = 0;
                thread.is_read = true;
            }

            // Load sidebar 360 for main partner
            const inbound = this.state.messages.find(
                m => m.direction_computed === 'inbound' || m.direction === 'inbound'
            );
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

    // ── Callbacks from children ─────────────────────────────────

    onAccountChange(accountIds) {
        this.state.selectedAccountIds = accountIds;
        this.state.activeFolder = 'inbox';
        this.loadThreads();
    }

    onFolderChange(folder) {
        this.state.activeFolder = folder;
        this.loadThreads();
    }

    async onMessageAction(action, msgId) {
        try {
            await rpc('/cf/mail/v3/message/' + msgId + '/' + action);
            if (this.state.selectedThreadId) {
                const res = await rpc('/cf/mail/v3/thread/' + this.state.selectedThreadId + '/messages');
                this.state.messages = res.messages || [];
            }
        } catch (e) {
            console.error('[mail v3] message action error:', e);
        }
    }

    // ── Compose (wizard action) ─────────────────────────────────

    openComposeNew() {
        this._openComposeWizard('new', null);
    }

    openReply(msgId) {
        this._openComposeWizard('reply', msgId);
    }

    openReplyAll(msgId) {
        this._openComposeWizard('reply_all', msgId);
    }

    openForward(msgId) {
        this._openComposeWizard('forward', msgId);
    }

    async _openComposeWizard(mode, replyToId, prefilled_body) {
        const accountId = this.state.selectedAccountIds
            ? this.state.selectedAccountIds[0]
            : (this.state.accounts.length > 0 ? this.state.accounts[0].id : null);

        try {
            const action = await rpc('/cf/mail/v3/compose/open', {
                account_id: accountId,
                mode: mode,
                reply_to_id: replyToId || false,
                prefilled_body: prefilled_body || '',
            });
            await this.actionService.doAction(action, {
                onClose: async () => {
                    await this.loadThreads();
                    if (this.state.selectedThreadId) {
                        await this.selectThread(this.state.selectedThreadId);
                    }
                },
            });
        } catch (e) {
            console.error('[mail v3] compose open error:', e);
        }
    }

    // ── Reply Assistant ─────────────────────────────────────────

    openReplyAssistant(msgId) {
        this.state.replyAssistantMessageId = msgId;
        this.state.replyAssistantVisible = true;
    }

    closeReplyAssistant() {
        this.state.replyAssistantVisible = false;
        this.state.replyAssistantMessageId = null;
    }

    onSelectDraft(body) {
        // Close assistant, open compose with selected AI draft
        const msgId = this.state.replyAssistantMessageId;
        this.state.replyAssistantVisible = false;
        this.state.replyAssistantMessageId = null;
        this._openComposeWizard('reply', msgId, body);
    }

    // ── NBA dismiss ─────────────────────────────────────────────

    async dismissNba(partnerId) {
        try {
            await rpc('/cf/mail/v3/partner/' + partnerId + '/nba/dismiss');
            if (this.state.sidebar360Data && this.state.sidebar360Data.nba) {
                this.state.sidebar360Data.nba = {};
            }
        } catch (e) {
            console.error('[mail v3] NBA dismiss error:', e);
        }
    }

    // ── Notes save ──────────────────────────────────────────────

    async saveNotes(partnerId, notes) {
        try {
            await rpc('/cf/mail/v3/partner/' + partnerId + '/notes', { notes: notes });
        } catch (e) {
            console.error('[mail v3] Notes save error:', e);
        }
    }

    // ── Settings ────────────────────────────────────────────────

    openSettings() {
        this.state.settingsVisible = true;
    }

    closeSettings() {
        this.state.settingsVisible = false;
    }

    // ── Search ──────────────────────────────────────────────────

    _searchTimeout = null;

    onSearchInput(ev) {
        const query = ev.target.value;
        this.state.searchQuery = query;
        if (this._searchTimeout) clearTimeout(this._searchTimeout);
        if (!query || query.length < 2) {
            this.state.searchResults = null;
            return;
        }
        this._searchTimeout = setTimeout(() => this._doSearch(query), 300);
    }

    async _doSearch(query) {
        try {
            const res = await rpc('/cf/mail/v3/search', { query: query, limit: 50 });
            this.state.searchResults = res.results || [];
        } catch (e) {
            console.error('[mail v3] search error:', e);
        }
    }

    onSearchResultClick(threadId) {
        if (threadId) {
            this.state.searchQuery = '';
            this.state.searchResults = null;
            this.selectThread(threadId);
        }
    }

    clearSearch() {
        this.state.searchQuery = '';
        this.state.searchResults = null;
    }

    // ── Keyboard Shortcuts ──────────────────────────────────────

    _onKeyDown(ev) {
        // Skip when focus is on input/textarea/contenteditable
        const tag = ev.target.tagName;
        const editable = ev.target.getAttribute('contenteditable');
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || editable === 'true') {
            // Allow Cmd+Enter in inputs
            if ((ev.metaKey || ev.ctrlKey) && ev.key === 'Enter') {
                // Handled by compose wizard natively
            }
            return;
        }

        const threads = this.state.threads || [];

        switch (ev.key) {
            case 'j': // Next thread
                ev.preventDefault();
                if (this.state.selectedThreadIndex < threads.length - 1) {
                    const nextIdx = this.state.selectedThreadIndex + 1;
                    this.selectThread(threads[nextIdx].id);
                }
                break;
            case 'k': // Prev thread
                ev.preventDefault();
                if (this.state.selectedThreadIndex > 0) {
                    const prevIdx = this.state.selectedThreadIndex - 1;
                    this.selectThread(threads[prevIdx].id);
                }
                break;
            case 'r': // Reply
                ev.preventDefault();
                if (!ev.shiftKey) {
                    this._shortcutReply('reply');
                }
                break;
            case 'R': // Reply all (Shift+R)
                ev.preventDefault();
                this._shortcutReply('reply_all');
                break;
            case 'f': // Forward
                ev.preventDefault();
                this._shortcutReply('forward');
                break;
            case 'a': // AI reply assistant
                ev.preventDefault();
                this._shortcutAiReply();
                break;
            case 'e': // Archive
                ev.preventDefault();
                this._shortcutAction('archive');
                break;
            case '#': // Delete
                ev.preventDefault();
                this._shortcutAction('delete_soft');
                break;
            case 's': // Star
                ev.preventDefault();
                this._shortcutAction('toggle_star');
                break;
            case 'u': // Mark unread
                ev.preventDefault();
                this._shortcutAction('mark_unread');
                break;
            case 'c': // Compose new
                ev.preventDefault();
                this.openComposeNew();
                break;
            case '/': // Focus search
                ev.preventDefault();
                const searchInput = document.querySelector('.mv3-search__input');
                if (searchInput) searchInput.focus();
                break;
            case '?': // Shortcuts help
                ev.preventDefault();
                this.state.shortcutsHelpVisible = !this.state.shortcutsHelpVisible;
                break;
        }
    }

    _shortcutReply(mode) {
        const msgs = this.state.messages || [];
        if (msgs.length > 0) {
            const lastMsg = msgs[msgs.length - 1];
            this._openComposeWizard(mode, lastMsg.id);
        }
    }

    _shortcutAiReply() {
        const msgs = this.state.messages || [];
        if (msgs.length > 0) {
            this.openReplyAssistant(msgs[msgs.length - 1].id);
        }
    }

    _shortcutAction(action) {
        const msgs = this.state.messages || [];
        if (msgs.length > 0) {
            this.onMessageAction(action, msgs[msgs.length - 1].id);
        }
    }

    closeShortcutsHelp() {
        this.state.shortcutsHelpVisible = false;
    }
}

registry.category("actions").add("cf_mail_v3_client", MailV3Client);
