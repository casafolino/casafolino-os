/** @odoo-module **/
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

import { SidebarLeft } from "./mail_v3_sidebar_left";
import { ThreadList } from "./mail_v3_thread_list";
import { ReadingPane } from "./mail_v3_reading_pane";
import { Sidebar360 } from "./mail_v3_sidebar_360";
import { MailV3Insight360TabBar } from "./mail_v3_insight_360_tabbar";
import { ReplyAssistant } from "./mail_v3_reply_assistant";
import { ComposeWizard } from "./mail_v3_compose";
import { SenderDecisionPopup } from "./mail_v3_sender_decision_popup";
import { DismissedSenders } from "./mail_v3_dismissed_senders";
import { FolderSidebar } from "./mail_v3_folder_sidebar";

export class MailV3Client extends Component {
    static template = "casafolino_mail.MailV3Client";
    static components = { SidebarLeft, ThreadList, ReadingPane, Sidebar360, MailV3Insight360TabBar, ReplyAssistant, ComposeWizard, SenderDecisionPopup, DismissedSenders, FolderSidebar };
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
            loading: { threads: false, messages: false, sidebar: false, threadsMore: false },
            totalThreads: 0,
            threadsOffset: 0,
            hasMoreThreads: false,
            // Search
            searchQuery: '',
            searchResults: null,
            // Reply assistant
            replyAssistantVisible: false,
            replyAssistantMessageId: null,
            // Settings drawer
            settingsVisible: false,
            settingsTab: 'signatures',
            signatures: [],
            preferences: {},
            groqTestResult: null,
            // Shortcuts help
            shortcutsHelpVisible: false,
            // Dark mode
            darkMode: false,
            // Snooze popup
            snoozePopupVisible: false,
            snoozeThreadId: null,
            snoozeCustomDate: '',
            snoozeType: 'until_date',
            // Undo send
            undoToast: false,
            undoOutboxId: null,
            undoCountdown: 10,
            // Bulk selection
            bulkMode: false,
            selectedThreadIds: [],
            // Mobile
            mobileView: null, // null = desktop, 'list' | 'reading' | 'sidebar'
            // Compose overlay (F10: OWL ComposeWizard)
            composeVisible: false,
            composeDraftId: null,
            composePrefilled: null,
            composeMode: 'new',
            composeAccountId: null,
            // 360 panel collapse (F10 WP5)
            panel360Collapsed: false,
            // V12.4: sender email for 360 tabbar
            senderEmail: '',
            // V12.6: Sender decision
            senderDecisionVisible: false,
            senderDecisionEmail: '',
            senderDecisionName: '',
            // V12.6: Dismiss undo toast
            dismissUndoToast: false,
            dismissUndoEmail: '',
            dismissUndoToken: '',
            dismissUndoCount: 0,
            dismissUndoCountdown: 10,
            // V12.6: Dismissed senders folder
            dismissedSendersVisible: false,
            // V14: Folder sidebar
            selectedFolderId: null,
            folderSidebarVisible: true,
            // V15: Mass actions
            searchAllSelected: false,
            allSelected: false,
            moveDropdownVisible: false,
            moveFolders: [],
            massUndoToast: false,
            massUndoToken: '',
            massUndoMessage: '',
            massUndoCountdown: 10,
            isTrashView: false,
            permanentDeleteConfirm: false,
        });

        this._keyHandler = this._onKeyDown.bind(this);
        this._undoTimer = null;
        this._undoCountdownTimer = null;
        this._dismissUndoTimer = null;
        this._dismissUndoCountdownTimer = null;
        this._massUndoTimer = null;
        this._massUndoCountdownTimer = null;

        onWillStart(async () => {
            await this.loadAccounts();
            await this.loadThreads();
            await this._loadPreferences();
            this._detectMobile();
        });

        onMounted(() => {
            document.addEventListener('keydown', this._keyHandler);
            window.addEventListener('resize', () => this._detectMobile());
        });

        onWillUnmount(() => {
            document.removeEventListener('keydown', this._keyHandler);
            if (this._undoTimer) clearTimeout(this._undoTimer);
            if (this._undoCountdownTimer) clearInterval(this._undoCountdownTimer);
        });
    }

    // ── Mobile detection ────────────────────────────────────────

    _detectMobile() {
        if (window.innerWidth <= 768) {
            if (!this.state.mobileView) {
                this.state.mobileView = 'list';
            }
        } else {
            this.state.mobileView = null;
        }
    }

    mobileBack() {
        this.state.mobileView = 'list';
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
        this.state.threadsOffset = 0;
        this.state.hasMoreThreads = false;
        try {
            const folder = this.state.activeFolder === 'inbox' ? null : this.state.activeFolder;
            const params = {
                account_ids: this.state.selectedAccountIds,
                state: 'keep',
                limit: 50,
                offset: 0,
                filters: {},
                folder: folder,
            };
            if (this.state.selectedFolderId) {
                params.folder_id = this.state.selectedFolderId;
            }
            const res = await rpc('/cf/mail/v3/threads/list', params);
            this.state.threads = res.threads || [];
            this.state.totalThreads = res.total || 0;
            this.state.hasMoreThreads = res.has_more || false;
            this.state.threadsOffset = this.state.threads.length;
            this.state.searchResults = null;
        } catch (e) {
            console.error('[mail v3] loadThreads error:', e);
        }
        this.state.loading.threads = false;
    }

    async loadMoreThreads() {
        if (this.state.loading.threadsMore || !this.state.hasMoreThreads) return;
        this.state.loading.threadsMore = true;
        try {
            const folder = this.state.activeFolder === 'inbox' ? null : this.state.activeFolder;
            const moreParams = {
                account_ids: this.state.selectedAccountIds,
                state: 'keep',
                limit: 50,
                offset: this.state.threadsOffset,
                filters: {},
                folder: folder,
            };
            if (this.state.selectedFolderId) {
                moreParams.folder_id = this.state.selectedFolderId;
            }
            const res = await rpc('/cf/mail/v3/threads/list', moreParams);
            const newThreads = res.threads || [];
            this.state.threads = [...this.state.threads, ...newThreads];
            this.state.totalThreads = res.total || this.state.totalThreads;
            this.state.hasMoreThreads = res.has_more || false;
            this.state.threadsOffset += newThreads.length;
        } catch (e) {
            console.error('[mail v3] loadMoreThreads error:', e);
        }
        this.state.loading.threadsMore = false;
    }

    async selectThread(threadId) {
        this.state.selectedThreadId = threadId;
        const idx = this.state.threads.findIndex(t => t.id === threadId);
        this.state.selectedThreadIndex = idx;
        this.state.loading.messages = true;

        // Mobile: switch to reading pane
        if (this.state.mobileView) {
            this.state.mobileView = 'reading';
        }

        try {
            const res = await rpc('/cf/mail/v3/thread/' + threadId + '/messages');
            this.state.messages = res.messages || [];

            rpc('/cf/mail/v3/thread/' + threadId + '/mark_all_read').catch(() => {});

            const thread = this.state.threads.find(t => t.id === threadId);
            if (thread) {
                thread.unread_count = 0;
                thread.is_read = true;
            }
        } catch (e) {
            console.error('[mail v3] selectThread messages error:', e);
        }
        this.state.loading.messages = false;

        // Load sidebar 360 separately — never blocks message rendering
        const inbound = this.state.messages.find(
            m => m.direction_computed === 'inbound' || m.direction === 'inbound'
        );
        const partnerId = inbound ? inbound.partner_id : null;
        this.state.senderEmail = inbound ? (inbound.sender_email || '') : '';
        if (partnerId) {
            this._loadSidebar360(partnerId);
        } else {
            this.state.sidebar360Data = null;
            this.state.selectedPartner = null;
        }

        // V12.6: Check sender decision status for popup
        this.state.senderDecisionVisible = false;
        if (inbound && inbound.sender_email) {
            this._checkSenderDecision(inbound.sender_email, inbound.sender_name || '');
        }
    }

    async _loadSidebar360(partnerId) {
        this.state.loading.sidebar = true;
        try {
            const sidebar = await rpc('/cf/mail/v3/partner/' + partnerId + '/sidebar_360');
            this.state.sidebar360Data = sidebar;
            this.state.selectedPartner = partnerId;
        } catch (e) {
            console.error('[mail v3] sidebar 360 load error:', e);
            this.state.sidebar360Data = null;
            this.state.selectedPartner = null;
        }
        this.state.loading.sidebar = false;
    }

    // ── Callbacks from children ─────────────────────────────────

    onAccountChange(accountIds) {
        this.state.selectedAccountIds = accountIds;
        this.state.activeFolder = 'inbox';
        this.loadThreads();
    }

    onFolderChange(folder) {
        this.state.activeFolder = folder;
        this.state.selectedFolderId = null;
        this.state.dismissedSendersVisible = false;
        this.state.isTrashView = (folder === 'trash');
        this.clearBulkSelection();
        if (folder === 'scheduled') {
            this._loadScheduled();
        } else if (folder === 'dismissed') {
            this.state.dismissedSendersVisible = true;
        } else {
            this.loadThreads();
        }
    }

    // V14: Folder sidebar callbacks
    onFolderSelect(folderId, accountId) {
        this.state.selectedFolderId = folderId;
        this.clearBulkSelection();
        if (folderId) {
            // When selecting a folder, switch to that account too
            if (accountId) {
                this.state.selectedAccountIds = [accountId];
            }
            this.state.activeFolder = 'inbox';
            this.state.dismissedSendersVisible = false;
            // Detect if selected folder is trash (for permanent delete button)
            this._detectTrashFolder(folderId);
        } else {
            this.state.isTrashView = false;
        }
        this.loadThreads();
    }

    async _detectTrashFolder(folderId) {
        try {
            const folders = await rpc('/cf/mail/v3/folders/list');
            const folder = (folders.folders || []).find(f => f.id === folderId);
            this.state.isTrashView = folder && folder.system_code === 'trash';
        } catch (e) {
            this.state.isTrashView = false;
        }
    }

    onOpenRules() {
        this.actionService.doAction('casafolino_mail.action_casafolino_mail_folder_rule');
    }

    async _loadScheduled() {
        this.state.loading.threads = true;
        try {
            const res = await rpc('/cf/mail/v3/scheduled');
            // Map drafts to thread-like objects for display
            this.state.threads = (res.drafts || []).map(d => ({
                id: d.id,
                subject: d.subject || '(Senza oggetto)',
                main_participant: d.to_emails || '',
                is_read: true,
                unread_count: 0,
                preview: 'Programmata: ' + (d.scheduled_send_at || '').slice(0, 16),
                silent_days: 0,
                hotness_score: 0,
                hotness_tier: '',
                hotness_emoji: '',
                attachment_count: 0,
                lead_open: false,
                is_draft: true,
            }));
            this.state.totalThreads = this.state.threads.length;
        } catch (e) {
            console.error('[mail v3] load scheduled error:', e);
        }
        this.state.loading.threads = false;
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

    async onDeleteEmail(msgId) {
        try {
            const result = await rpc('/cf/mail/v3/message/delete_single', { message_id: msgId });
            if (result.success) {
                if (result.thread_deleted) {
                    this.state.selectedThreadId = null;
                    this.state.messages = [];
                    await this.loadThreads();
                } else {
                    const res = await rpc('/cf/mail/v3/thread/' + this.state.selectedThreadId + '/messages');
                    this.state.messages = res.messages || [];
                }
            }
        } catch (e) {
            console.error('[mail v3] delete email error:', e);
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
            // Create draft via RPC to get prefilled data + draftId
            const result = await rpc('/cf/mail/v3/compose/prepare', {
                account_id: accountId,
                mode: mode,
                reply_to_id: replyToId || false,
                prefilled_body: prefilled_body || '',
            });
            if (!result || !result.draft_id) {
                console.error("[mail v3] compose prepare failed", result);
                return;
            }
            // Show OWL ComposeWizard overlay
            this.state.composeDraftId = result.draft_id;
            this.state.composePrefilled = result.prefilled || {};
            this.state.composeMode = mode;
            this.state.composeAccountId = accountId;
            this.state.composeVisible = true;
        } catch (e) {
            console.error('[mail v3] compose open error:', e);
        }
    }

    async onComposeSent() {
        this.state.composeVisible = false;
        this.state.composeDraftId = null;
        await this.loadThreads();
        if (this.state.selectedThreadId) {
            await this.selectThread(this.state.selectedThreadId);
        }
    }

    onComposeClose() {
        this.state.composeVisible = false;
        this.state.composeDraftId = null;
    }

    togglePanel360() {
        this.state.panel360Collapsed = !this.state.panel360Collapsed;
    }

    onPartnerCreated(partnerId) {
        this.state.selectedPartner = partnerId;
        this._loadSidebar360(partnerId);
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
        const msgId = this.state.replyAssistantMessageId;
        this.state.replyAssistantVisible = false;
        this.state.replyAssistantMessageId = null;
        this._openComposeWizard('reply', msgId, body);
    }

    // ── NBA dismiss + Calibration Feedback ──────────────────────

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

    async logFeedback(partnerId, actionType) {
        try {
            await rpc('/cf/mail/v3/partner/' + partnerId + '/feedback', {
                action_type: actionType,
            });
        } catch (e) {
            console.error('[mail v3] feedback error:', e);
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

    onSidebarQuickAction(key) {
        const msgs = this.state.messages || [];
        const lastMsg = msgs.length > 0 ? msgs[msgs.length - 1] : null;
        switch (key) {
            case 'reply':
                if (lastMsg) this.openReply(lastMsg.id);
                break;
            case 'open_partner':
                if (this.state.selectedPartner) {
                    this.actionService.doAction({
                        type: 'ir.actions.act_window',
                        res_model: 'res.partner',
                        res_id: this.state.selectedPartner,
                        views: [[false, 'form']],
                        target: 'current',
                    });
                }
                break;
            case 'new_lead':
                this.actionService.doAction({
                    type: 'ir.actions.act_window',
                    res_model: 'crm.lead',
                    views: [[false, 'form']],
                    target: 'current',
                    context: { default_partner_id: this.state.selectedPartner },
                });
                break;
            default:
                break;
        }
    }

    async doAction(action) {
        try {
            await this.actionService.doAction(action, {
                onClose: async () => {
                    if (this.state.selectedThreadId) {
                        await this.selectThread(this.state.selectedThreadId);
                    }
                },
            });
        } catch (e) {
            console.error('[mail v3] doAction error:', e);
        }
    }

    // ── Dark Mode ───────────────────────────────────────────────

    async toggleDarkMode() {
        const newMode = !this.state.darkMode;
        this.state.darkMode = newMode;
        try {
            await rpc('/cf/mail/v3/user/dark_mode', { enabled: newMode });
        } catch (e) {
            console.error('[mail v3] dark mode toggle error:', e);
        }
    }

    // ── Snooze ──────────────────────────────────────────────────

    openSnoozePopup(threadId) {
        this.state.snoozeThreadId = threadId || this.state.selectedThreadId;
        this.state.snoozePopupVisible = true;
        this.state.snoozeCustomDate = '';
        this.state.snoozeType = 'until_date';
    }

    closeSnoozePopup() {
        this.state.snoozePopupVisible = false;
    }

    onSnoozeCustomDateChange(ev) {
        this.state.snoozeCustomDate = ev.target.value;
    }

    onSnoozeTypeChange(ev) {
        this.state.snoozeType = ev.target.value;
    }

    async snoozePreset(preset) {
        const now = new Date();
        let wake;
        switch (preset) {
            case 'tonight':
                wake = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 18, 0);
                if (wake <= now) wake.setDate(wake.getDate() + 1);
                break;
            case 'tomorrow':
                wake = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 9, 0);
                break;
            case 'monday': {
                const daysUntilMonday = (8 - now.getDay()) % 7 || 7;
                wake = new Date(now.getFullYear(), now.getMonth(), now.getDate() + daysUntilMonday, 9, 0);
                break;
            }
            case 'week':
                wake = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
                wake.setHours(9, 0, 0, 0);
                break;
        }
        await this._doSnooze(wake.toISOString().slice(0, 19).replace('T', ' '));
    }

    async confirmSnooze() {
        if (this.state.snoozeCustomDate) {
            const wake = this.state.snoozeCustomDate.replace('T', ' ') + ':00';
            await this._doSnooze(wake);
        }
    }

    async _doSnooze(wakeAt) {
        const threadId = this.state.snoozeThreadId || this.state.selectedThreadId;
        if (!threadId) return;
        try {
            await rpc('/cf/mail/v3/thread/' + threadId + '/snooze', {
                snooze_type: this.state.snoozeType,
                wake_at: wakeAt,
            });
            this.state.snoozePopupVisible = false;
            await this.loadThreads();
        } catch (e) {
            console.error('[mail v3] snooze error:', e);
        }
    }

    // ── Undo Send ───────────────────────────────────────────────

    showUndoToast(outboxId) {
        this.state.undoToast = true;
        this.state.undoOutboxId = outboxId;
        this.state.undoCountdown = 10;

        this._undoCountdownTimer = setInterval(() => {
            this.state.undoCountdown--;
            if (this.state.undoCountdown <= 0) {
                this._clearUndoToast();
            }
        }, 1000);

        this._undoTimer = setTimeout(() => {
            this._clearUndoToast();
        }, 10500);
    }

    _clearUndoToast() {
        this.state.undoToast = false;
        this.state.undoOutboxId = null;
        if (this._undoTimer) { clearTimeout(this._undoTimer); this._undoTimer = null; }
        if (this._undoCountdownTimer) { clearInterval(this._undoCountdownTimer); this._undoCountdownTimer = null; }
    }

    async undoSend() {
        if (!this.state.undoOutboxId) return;
        try {
            await rpc('/cf/mail/v3/outbox/' + this.state.undoOutboxId + '/undo');
            this._clearUndoToast();
        } catch (e) {
            console.error('[mail v3] undo send error:', e);
        }
    }

    // ── Bulk Selection ─────────────────────────────────────────

    toggleThreadSelect(threadId) {
        const ids = this.state.selectedThreadIds || [];
        const idx = ids.indexOf(threadId);
        if (idx >= 0) {
            ids.splice(idx, 1);
        } else {
            ids.push(threadId);
        }
        this.state.selectedThreadIds = [...ids];
        this.state.bulkMode = ids.length > 0;
        this.state.allSelected = ids.length > 0 && ids.length === (this.state.threads || []).length;
    }

    toggleSelectAll() {
        const threads = this.state.threads || [];
        if (this.state.allSelected) {
            this.state.selectedThreadIds = [];
            this.state.allSelected = false;
            this.state.bulkMode = false;
        } else {
            this.state.selectedThreadIds = threads.map(t => t.id);
            this.state.allSelected = true;
            this.state.bulkMode = true;
        }
    }

    clearBulkSelection() {
        this.state.selectedThreadIds = [];
        this.state.bulkMode = false;
        this.state.allSelected = false;
        this.state.moveDropdownVisible = false;
    }

    // ── V15: Mass Actions ───────────────────────────────────────

    async massMarkRead() {
        if (!this.state.selectedThreadIds.length) return;
        try {
            const res = await rpc('/cf/mail/v3/mass_action/mark_read', {
                thread_ids: this.state.selectedThreadIds,
            });
            if (res.success) {
                this._showMassUndoToast(res.undo_token, res.processed + ' conversazioni segnate come lette');
                this.clearBulkSelection();
                await this.loadThreads();
            }
        } catch (e) {
            console.error('[mail v3] mass mark_read error:', e);
        }
    }

    async massArchive() {
        if (!this.state.selectedThreadIds.length) return;
        try {
            const res = await rpc('/cf/mail/v3/mass_action/archive', {
                thread_ids: this.state.selectedThreadIds,
            });
            if (res.success) {
                this._showMassUndoToast(res.undo_token, res.processed + ' conversazioni archiviate');
                this.clearBulkSelection();
                await this.loadThreads();
            }
        } catch (e) {
            console.error('[mail v3] mass archive error:', e);
        }
    }

    async massTrash() {
        if (!this.state.selectedThreadIds.length) return;
        try {
            const res = await rpc('/cf/mail/v3/mass_action/trash', {
                thread_ids: this.state.selectedThreadIds,
            });
            if (res.success) {
                this._showMassUndoToast(res.undo_token, res.processed + ' conversazioni cestinate');
                this.clearBulkSelection();
                await this.loadThreads();
            }
        } catch (e) {
            console.error('[mail v3] mass trash error:', e);
        }
    }

    async toggleMoveDropdown() {
        if (this.state.moveDropdownVisible) {
            this.state.moveDropdownVisible = false;
            return;
        }
        try {
            const res = await rpc('/cf/mail/v3/mass_action/folders_for_move', {
                account_ids: this.state.selectedAccountIds || [],
                exclude_folder_id: this.state.selectedFolderId || false,
            });
            this.state.moveFolders = res.folders || [];
            this.state.moveDropdownVisible = true;
        } catch (e) {
            console.error('[mail v3] load move folders error:', e);
        }
    }

    async massMove(folderId, folderName) {
        if (!this.state.selectedThreadIds.length) return;
        this.state.moveDropdownVisible = false;
        try {
            const res = await rpc('/cf/mail/v3/mass_action/move', {
                thread_ids: this.state.selectedThreadIds,
                folder_id: folderId,
            });
            if (res.success) {
                this._showMassUndoToast(res.undo_token, res.processed + ' conversazioni spostate in ' + folderName);
                this.clearBulkSelection();
                await this.loadThreads();
            }
        } catch (e) {
            console.error('[mail v3] mass move error:', e);
        }
    }

    async massDismissSenders() {
        if (!this.state.selectedThreadIds.length) return;
        try {
            const res = await rpc('/cf/mail/v3/mass_action/dismiss_senders', {
                thread_ids: this.state.selectedThreadIds,
            });
            if (res.success) {
                this._showMassUndoToast(res.undo_token, res.dismissed_count + ' mittenti dismessi');
                this.clearBulkSelection();
                await this.loadThreads();
            }
        } catch (e) {
            console.error('[mail v3] mass dismiss error:', e);
        }
    }

    massPermanentDelete() {
        if (!this.state.selectedThreadIds.length) return;
        this.state.permanentDeleteConfirm = true;
    }

    cancelPermanentDelete() {
        this.state.permanentDeleteConfirm = false;
    }

    async confirmPermanentDelete() {
        this.state.permanentDeleteConfirm = false;
        try {
            const res = await rpc('/cf/mail/v3/mass_action/permanent_delete', {
                thread_ids: this.state.selectedThreadIds,
            });
            if (res.success) {
                this.clearBulkSelection();
                this.state.selectedThreadId = null;
                this.state.messages = [];
                await this.loadThreads();
            }
        } catch (e) {
            console.error('[mail v3] mass permanent delete error:', e);
        }
    }

    // ── V15: Mass Undo Toast ────────────────────────────────────

    _showMassUndoToast(token, message) {
        this.state.massUndoToast = true;
        this.state.massUndoToken = token;
        this.state.massUndoMessage = message;
        this.state.massUndoCountdown = 10;

        if (this._massUndoCountdownTimer) clearInterval(this._massUndoCountdownTimer);
        if (this._massUndoTimer) clearTimeout(this._massUndoTimer);

        this._massUndoCountdownTimer = setInterval(() => {
            this.state.massUndoCountdown--;
            if (this.state.massUndoCountdown <= 0) {
                this._clearMassUndoToast();
            }
        }, 1000);

        this._massUndoTimer = setTimeout(() => {
            this._clearMassUndoToast();
        }, 10500);
    }

    _clearMassUndoToast() {
        this.state.massUndoToast = false;
        this.state.massUndoToken = '';
        if (this._massUndoTimer) { clearTimeout(this._massUndoTimer); this._massUndoTimer = null; }
        if (this._massUndoCountdownTimer) { clearInterval(this._massUndoCountdownTimer); this._massUndoCountdownTimer = null; }
    }

    async massUndoAction() {
        if (!this.state.massUndoToken) return;
        try {
            await rpc('/cf/mail/v3/mass_action/undo', {
                token: this.state.massUndoToken,
            });
            this._clearMassUndoToast();
            await this.loadThreads();
        } catch (e) {
            console.error('[mail v3] mass undo error:', e);
        }
    }

    openBulkSnooze() {
        this.state.snoozeThreadId = null; // bulk mode uses selectedThreadIds
        this.state.snoozePopupVisible = true;
    }

    // ── Settings ────────────────────────────────────────────────

    async openSettings() {
        this.state.settingsVisible = true;
        this.state.settingsTab = 'signatures';
        await this._loadSignatures();
    }

    closeSettings() {
        this.state.settingsVisible = false;
    }

    async _loadPreferences() {
        try {
            const prefs = await rpc('/cf/mail/v3/user/preferences');
            this.state.preferences = prefs;
            this.state.darkMode = prefs.dark_mode || false;
        } catch (e) {
            console.error('[mail v3] load preferences error:', e);
        }
    }

    async _loadSignatures() {
        try {
            const res = await rpc('/cf/mail/v3/signatures');
            this.state.signatures = res.signatures || [];
        } catch (e) {
            console.error('[mail v3] load signatures error:', e);
        }
    }

    async onSettingChange(ev) {
        const field = ev.target.dataset.field;
        const value = ev.target.value;
        this.state.preferences[field] = value;
        await this._savePreference(field, value);
    }

    async onSettingToggle(ev) {
        const field = ev.target.dataset.field;
        const value = ev.target.checked;
        this.state.preferences[field] = value;
        await this._savePreference(field, value);
    }

    async onAiTempChange(ev) {
        const value = parseFloat(ev.target.value);
        this.state.preferences.ai_temperature = value;
        await this._savePreference('ai_temperature', value);
    }

    async _savePreference(field, value) {
        try {
            const payload = {};
            payload[field] = value;
            await rpc('/cf/mail/v3/user/preferences/save', payload);
        } catch (e) {
            console.error('[mail v3] save preference error:', e);
        }
    }

    async testGroqConnection() {
        this.state.groqTestResult = null;
        try {
            const res = await rpc('/cf/mail/v3/settings/test_groq');
            this.state.groqTestResult = res;
        } catch (e) {
            this.state.groqTestResult = { success: false, error: 'Network error' };
        }
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
        this.state.searchAllSelected = false;
    }

    // ── V16: Search result selection (mass action) ─────────────

    toggleSearchThreadSelect(threadId) {
        const ids = this.state.selectedThreadIds || [];
        const idx = ids.indexOf(threadId);
        if (idx >= 0) {
            ids.splice(idx, 1);
        } else {
            ids.push(threadId);
        }
        this.state.selectedThreadIds = [...ids];
        this.state.bulkMode = ids.length > 0;
        const searchResults = this.state.searchResults || [];
        const searchThreadIds = searchResults.map(sr => sr.thread_id).filter(Boolean);
        this.state.searchAllSelected = searchThreadIds.length > 0
            && searchThreadIds.every(tid => ids.indexOf(tid) >= 0);
    }

    toggleSearchSelectAll() {
        const searchResults = this.state.searchResults || [];
        const searchThreadIds = [...new Set(searchResults.map(sr => sr.thread_id).filter(Boolean))];
        if (this.state.searchAllSelected) {
            // Deselect all search results
            this.state.selectedThreadIds = (this.state.selectedThreadIds || [])
                .filter(id => searchThreadIds.indexOf(id) < 0);
            this.state.searchAllSelected = false;
        } else {
            // Select all search results
            const current = new Set(this.state.selectedThreadIds || []);
            searchThreadIds.forEach(id => current.add(id));
            this.state.selectedThreadIds = [...current];
            this.state.searchAllSelected = true;
        }
        this.state.bulkMode = this.state.selectedThreadIds.length > 0;
    }

    // ── Keyboard Shortcuts ──────────────────────────────────────

    _onKeyDown(ev) {
        const tag = ev.target.tagName;
        const editable = ev.target.getAttribute('contenteditable');
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || editable === 'true') {
            return;
        }

        const threads = this.state.threads || [];

        switch (ev.key) {
            case 'j':
                ev.preventDefault();
                if (this.state.selectedThreadIndex < threads.length - 1) {
                    this.selectThread(threads[this.state.selectedThreadIndex + 1].id);
                }
                break;
            case 'k':
                ev.preventDefault();
                if (this.state.selectedThreadIndex > 0) {
                    this.selectThread(threads[this.state.selectedThreadIndex - 1].id);
                }
                break;
            case 'r':
                ev.preventDefault();
                if (!ev.shiftKey) this._shortcutReply('reply');
                break;
            case 'R':
                ev.preventDefault();
                this._shortcutReply('reply_all');
                break;
            case 'f':
                ev.preventDefault();
                this._shortcutReply('forward');
                break;
            case 'a':
                ev.preventDefault();
                this._shortcutAiReply();
                break;
            case 'e':
                ev.preventDefault();
                this._shortcutAction('archive');
                break;
            case '#':
                ev.preventDefault();
                this._shortcutAction('delete_soft');
                break;
            case 's':
                ev.preventDefault();
                this._shortcutAction('toggle_star');
                break;
            case 'u':
                ev.preventDefault();
                this._shortcutAction('mark_unread');
                break;
            case 'c':
                ev.preventDefault();
                this.openComposeNew();
                break;
            case 'x':
                ev.preventDefault();
                if (this.state.selectedThreadId) {
                    this.toggleThreadSelect(this.state.selectedThreadId);
                }
                break;
            case 'z':
                ev.preventDefault();
                this.openSnoozePopup();
                break;
            case '/':
                ev.preventDefault();
                const searchInput = document.querySelector('.mv3-search__input');
                if (searchInput) searchInput.focus();
                break;
            case '?':
                ev.preventDefault();
                this.state.shortcutsHelpVisible = !this.state.shortcutsHelpVisible;
                break;
        }
    }

    _shortcutReply(mode) {
        const msgs = this.state.messages || [];
        if (msgs.length > 0) {
            this._openComposeWizard(mode, msgs[msgs.length - 1].id);
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

    // ═══════════════════════════════════════════════════════════════
    // V12.6: Sender Decision
    // ═══════════════════════════════════════════════════════════════

    async _checkSenderDecision(email, name) {
        try {
            const res = await rpc('/cf/mail/v3/sender_decision/get', { email: email });
            if (res.status === 'pending') {
                this.state.senderDecisionEmail = email;
                this.state.senderDecisionName = name;
                this.state.senderDecisionVisible = true;
            }
        } catch (e) {
            console.error('[mail v3] sender decision check error:', e);
        }
    }

    onSenderDecision(decision) {
        this.state.senderDecisionVisible = false;
        // Refresh thread list to update pending badge
        this.loadThreads();
    }

    onSenderDismiss(email, undoToken, count) {
        this.state.senderDecisionVisible = false;
        this._showDismissUndoToast(email, undoToken, count);
        // Refresh thread list to remove dismissed threads
        this.loadThreads();
    }

    onSenderCreateLead() {
        this.state.senderDecisionVisible = false;
        const partnerId = this.state.selectedPartner;
        const threadId = this.state.selectedThreadId;
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'casafolino.mail.create.lead.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_partner_id: partnerId || false,
                default_thread_id: threadId || false,
            },
        });
    }

    onSenderCreateProject() {
        this.state.senderDecisionVisible = false;
        const email = this.state.senderDecisionEmail;
        const threadId = this.state.selectedThreadId;
        const partnerId = this.state.selectedPartner;
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'cf.initiative',
            views: [[false, 'form']],
            target: 'current',
            context: {
                default_source_email: email,
                default_source_thread_id: threadId,
                default_partner_id: partnerId || false,
            },
        });
    }

    // ── Quick Action: Dismiss current sender from reading pane ──

    async onQuickDismissSender() {
        const email = this.state.senderEmail;
        if (!email) return;
        try {
            const res = await rpc('/cf/mail/v3/sender_decision/dismiss', { email: email });
            this._showDismissUndoToast(email, res.undo_token, res.pending_deletion_count);
            await this.loadThreads();
        } catch (e) {
            console.error('[mail v3] quick dismiss error:', e);
        }
    }

    // ── Dismiss Undo Toast ─────────────────────────────────────

    _showDismissUndoToast(email, token, count) {
        this.state.dismissUndoToast = true;
        this.state.dismissUndoEmail = email;
        this.state.dismissUndoToken = token;
        this.state.dismissUndoCount = count;
        this.state.dismissUndoCountdown = 10;

        if (this._dismissUndoCountdownTimer) clearInterval(this._dismissUndoCountdownTimer);
        if (this._dismissUndoTimer) clearTimeout(this._dismissUndoTimer);

        this._dismissUndoCountdownTimer = setInterval(() => {
            this.state.dismissUndoCountdown--;
            if (this.state.dismissUndoCountdown <= 0) {
                this._clearDismissUndoToast();
            }
        }, 1000);

        this._dismissUndoTimer = setTimeout(() => {
            this._clearDismissUndoToast();
        }, 10500);
    }

    _clearDismissUndoToast() {
        this.state.dismissUndoToast = false;
        if (this._dismissUndoTimer) { clearTimeout(this._dismissUndoTimer); this._dismissUndoTimer = null; }
        if (this._dismissUndoCountdownTimer) { clearInterval(this._dismissUndoCountdownTimer); this._dismissUndoCountdownTimer = null; }
    }

    async cancelDismiss() {
        if (!this.state.dismissUndoToken) return;
        try {
            await rpc('/cf/mail/v3/sender_decision/cancel_dismiss', {
                undo_token: this.state.dismissUndoToken,
            });
            this._clearDismissUndoToast();
            await this.loadThreads();
        } catch (e) {
            console.error('[mail v3] cancel dismiss error:', e);
        }
    }

    // ── Dismissed Senders Folder ───────────────────────────────

    openDismissedSenders() {
        this.state.dismissedSendersVisible = true;
        this.state.activeFolder = 'dismissed';
    }

    closeDismissedSenders() {
        this.state.dismissedSendersVisible = false;
    }

    onDismissedRestored() {
        this.loadThreads();
    }
}

registry.category("actions").add("cf_mail_v3_client", MailV3Client);
