/** @odoo-module **/
import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

// ── Constants (before class so static refs work) ────────

const EMOJI_DATA = [
    { e: '\u{1F600}', keywords: ['smile', 'happy', 'grin'] },
    { e: '\u{1F603}', keywords: ['smile', 'happy'] },
    { e: '\u{1F604}', keywords: ['smile', 'laugh'] },
    { e: '\u{1F601}', keywords: ['grin', 'happy'] },
    { e: '\u{1F60A}', keywords: ['blush', 'smile'] },
    { e: '\u{1F642}', keywords: ['smile', 'slight'] },
    { e: '\u{1F609}', keywords: ['wink'] },
    { e: '\u{1F60D}', keywords: ['love', 'heart', 'eyes'] },
    { e: '\u{1F970}', keywords: ['love', 'hearts'] },
    { e: '\u{1F618}', keywords: ['kiss'] },
    { e: '\u{1F602}', keywords: ['laugh', 'cry', 'tears'] },
    { e: '\u{1F923}', keywords: ['laugh', 'rofl'] },
    { e: '\u{1F60E}', keywords: ['cool', 'sunglasses'] },
    { e: '\u{1F914}', keywords: ['think', 'hmm'] },
    { e: '\u{1F610}', keywords: ['neutral', 'meh'] },
    { e: '\u{1F622}', keywords: ['cry', 'sad'] },
    { e: '\u{1F62D}', keywords: ['sob', 'cry'] },
    { e: '\u{1F621}', keywords: ['angry', 'mad'] },
    { e: '\u{1F91D}', keywords: ['handshake', 'deal', 'agreement'] },
    { e: '\u{1F44D}', keywords: ['thumbsup', 'ok', 'good'] },
    { e: '\u{1F44E}', keywords: ['thumbsdown', 'bad'] },
    { e: '\u{1F44B}', keywords: ['wave', 'hello', 'bye'] },
    { e: '\u{1F64F}', keywords: ['pray', 'please', 'thanks'] },
    { e: '\u{1F4AA}', keywords: ['strong', 'muscle'] },
    { e: '\u{1F389}', keywords: ['party', 'celebration'] },
    { e: '\u{1F525}', keywords: ['fire', 'hot'] },
    { e: '\u2B50', keywords: ['star'] },
    { e: '\u{1F4A1}', keywords: ['idea', 'lightbulb'] },
    { e: '\u{1F4E7}', keywords: ['email', 'mail'] },
    { e: '\u{1F4CE}', keywords: ['paperclip', 'attachment'] },
    { e: '\u{1F4C5}', keywords: ['calendar', 'date'] },
    { e: '\u{1F4CA}', keywords: ['chart', 'stats'] },
    { e: '\u{1F4E6}', keywords: ['package', 'box', 'shipping'] },
    { e: '\u{1F3ED}', keywords: ['factory', 'production'] },
    { e: '\u{1F355}', keywords: ['pizza', 'food'] },
    { e: '\u{1F9C0}', keywords: ['cheese', 'food'] },
    { e: '\u{1FAD2}', keywords: ['olive', 'food'] },
    { e: '\u{1F336}\uFE0F', keywords: ['pepper', 'spicy', 'food'] },
    { e: '\u{1F35D}', keywords: ['pasta', 'food', 'spaghetti'] },
    { e: '\u{1F1EE}\u{1F1F9}', keywords: ['italy', 'flag'] },
    { e: '\u{1F1E9}\u{1F1EA}', keywords: ['germany', 'flag'] },
    { e: '\u{1F1EC}\u{1F1E7}', keywords: ['uk', 'england', 'flag'] },
    { e: '\u{1F1EA}\u{1F1F8}', keywords: ['spain', 'flag'] },
    { e: '\u{1F1EB}\u{1F1F7}', keywords: ['france', 'flag'] },
    { e: '\u2705', keywords: ['check', 'done', 'complete'] },
    { e: '\u274C', keywords: ['cross', 'no', 'wrong'] },
    { e: '\u26A0\uFE0F', keywords: ['warning', 'caution'] },
    { e: '\u{1F4B0}', keywords: ['money', 'dollar'] },
    { e: '\u{1F4C8}', keywords: ['growth', 'increase', 'chart'] },
    { e: '\u{1F4C9}', keywords: ['decrease', 'down', 'chart'] },
];

const FONT_SIZES = [
    { label: '8pt', value: '1' },
    { label: '10pt', value: '2' },
    { label: '12pt', value: '3' },
    { label: '14pt', value: '4' },
    { label: '18pt', value: '5' },
    { label: '24pt', value: '6' },
    { label: '36pt', value: '7' },
];

const COLOR_PALETTE = [
    '#000000', '#434343', '#666666', '#999999', '#cccccc', '#ffffff',
    '#E74C3C', '#E67E22', '#F1C40F', '#2ECC71', '#3498DB', '#9B59B6',
    '#C0392B', '#D35400', '#F39C12', '#27AE60', '#2980B9', '#8E44AD',
    '#5A6E3A', '#3d4d28', '#1ABC9C', '#16A085', '#2C3E50', '#34495E',
];

/**
 * Outlook-style composer with rich toolbar, emoji picker, inline images,
 * template panel, autosave indicator and preview modal.
 */
export class ComposeWizard extends Component {
    static template = "casafolino_mail.ComposeWizard";
    static props = ["*"];
    static FONT_SIZES = FONT_SIZES;
    static COLOR_PALETTE = COLOR_PALETTE;

    setup() {
        this.editorRef = useRef("editor");
        this.state = useState({
            to: this.props.prefilled?.to || '',
            cc: this.props.prefilled?.cc || '',
            bcc: this.props.prefilled?.bcc || '',
            subject: this.props.prefilled?.subject || '',
            body: this.props.prefilled?.body_html || '',
            sending: false,
            showBcc: false,
            error: '',
            attachments: [],
            dragOver: false,
            // Autosave
            lastSaveTime: null,
            saveStatus: '', // '' | 'saving' | 'saved' | 'error'
            // Emoji picker
            showEmojiPicker: false,
            emojiSearch: '',
            // Template panel
            showTemplatePanel: this.props.mode === 'new',
            templates: [],
            templateSearch: '',
            templateLangFilter: '',
            detectedLang: '',
            hoveredTemplate: null,
            hoveredPreviewHtml: '',
            // Preview modal
            showPreviewModal: false,
            previewData: null,
            // Font controls
            showFontSizeDropdown: false,
            showFontColorPicker: false,
            showBgColorPicker: false,
            // Signature
            signatureHtml: this.props.prefilled?.signature_html || '',
            // Snippet autocomplete
            snippetVisible: false,
            snippetResults: [],
            snippetSelectedIndex: 0,
            snippetQuery: '',
        });

        this._autosaveTimer = null;
        this._autosaveDebounce = null;
        this._snippetDebounce = null;

        onMounted(() => {
            // Snippet slash-command listener
            if (this.editorRef.el) {
                this.editorRef.el.addEventListener('keyup', this._onEditorKeyup.bind(this));
                this.editorRef.el.addEventListener('keydown', this._onEditorKeydown.bind(this));
            }
            if (this.editorRef.el && this.state.body) {
                this.editorRef.el.innerHTML = this.state.body;
            }
            if (this.editorRef.el && this.state.signatureHtml) {
                this._appendSignature(this.state.signatureHtml);
            }
            this._autosaveTimer = setInterval(() => this.autosave(), 15000);
            this._loadTemplates();
            this._detectPartnerLanguage();
        });

        onWillUnmount(() => {
            if (this._autosaveTimer) clearInterval(this._autosaveTimer);
            if (this._autosaveDebounce) clearTimeout(this._autosaveDebounce);
        });
    }

    // ── Editor helpers ──────────────────────────────────────

    _getEditorContent() {
        if (!this.editorRef.el) return this.state.body;
        return this.editorRef.el.innerHTML;
    }

    _execCommand(cmd, value = null) {
        this.editorRef.el?.focus();
        document.execCommand(cmd, false, value);
        this._syncBody();
    }

    _syncBody() {
        this.state.body = this._getEditorContent();
        this._triggerAutosaveDebounce();
    }

    onEditorInput() {
        this._syncBody();
    }

    onEditorPaste(ev) {
        const items = ev.clipboardData?.items;
        if (items) {
            for (const item of items) {
                if (item.type.startsWith('image/')) {
                    ev.preventDefault();
                    const file = item.getAsFile();
                    if (file) this._uploadInlineImage(file);
                    return;
                }
            }
        }
    }

    _appendSignature(sigHtml) {
        if (!this.editorRef.el || !sigHtml) return;
        const separator = '<br><div class="mv3-signature-separator" contenteditable="true" style="border-top: 1px solid #ccc; margin-top: 16px; padding-top: 12px;">';
        this.editorRef.el.innerHTML += separator + sigHtml + '</div>';
    }

    // ── Toolbar commands ────────────────────────────────────

    cmdBold() { this._execCommand('bold'); }
    cmdItalic() { this._execCommand('italic'); }
    cmdUnderline() { this._execCommand('underline'); }
    cmdStrikethrough() { this._execCommand('strikeThrough'); }
    cmdOrderedList() { this._execCommand('insertOrderedList'); }
    cmdUnorderedList() { this._execCommand('insertUnorderedList'); }
    cmdIndent() { this._execCommand('indent'); }
    cmdOutdent() { this._execCommand('outdent'); }
    cmdAlignLeft() { this._execCommand('justifyLeft'); }
    cmdAlignCenter() { this._execCommand('justifyCenter'); }
    cmdAlignRight() { this._execCommand('justifyRight'); }
    cmdAlignJustify() { this._execCommand('justifyFull'); }
    cmdHR() { this._execCommand('insertHorizontalRule'); }
    cmdRemoveFormat() { this._execCommand('removeFormat'); }
    cmdUndo() { this._execCommand('undo'); }
    cmdRedo() { this._execCommand('redo'); }

    cmdFontSize(size) {
        if (size) this._execCommand('fontSize', size);
        this.state.showFontSizeDropdown = false;
    }

    cmdFontColor(color) {
        this._execCommand('foreColor', color);
        this.state.showFontColorPicker = false;
    }

    cmdBgColor(color) {
        this._execCommand('hiliteColor', color);
        this.state.showBgColorPicker = false;
    }

    toggleFontSizeDropdown() { this.state.showFontSizeDropdown = !this.state.showFontSizeDropdown; }
    toggleFontColorPicker() { this.state.showFontColorPicker = !this.state.showFontColorPicker; }
    toggleBgColorPicker() { this.state.showBgColorPicker = !this.state.showBgColorPicker; }

    cmdLink() {
        const url = prompt('URL:');
        if (url) this._execCommand('createLink', url);
    }

    // ── Input handlers ──────────────────────────────────────

    onToChange(ev) { this.state.to = ev.target.value; }
    onCcChange(ev) { this.state.cc = ev.target.value; }
    onBccChange(ev) { this.state.bcc = ev.target.value; }
    onSubjectChange(ev) {
        this.state.subject = ev.target.value;
        this._triggerAutosaveDebounce();
    }
    toggleBcc() { this.state.showBcc = !this.state.showBcc; }

    // ── Drag & Drop ─────────────────────────────────────────

    onDragOver(ev) {
        ev.preventDefault();
        this.state.dragOver = true;
    }

    onDragLeave(ev) {
        ev.preventDefault();
        this.state.dragOver = false;
    }

    async onDrop(ev) {
        ev.preventDefault();
        this.state.dragOver = false;
        const files = ev.dataTransfer?.files;
        if (!files || files.length === 0) return;
        for (const file of files) {
            if (file.type.startsWith('image/')) {
                await this._uploadInlineImage(file);
            } else {
                await this._uploadFile(file);
            }
        }
    }

    async onFileSelect(ev) {
        const files = ev.target.files;
        if (!files || files.length === 0) return;
        for (const file of files) {
            await this._uploadFile(file);
        }
        ev.target.value = '';
    }

    async _uploadFile(file) {
        try {
            const formData = new FormData();
            formData.append('ufile', file);
            formData.append('csrf_token', odoo.csrf_token);
            const res = await fetch('/web/binary/upload_attachment', {
                method: 'POST',
                body: formData,
            });
            const data = await res.json();
            if (data && data[0] && data[0].id) {
                this.state.attachments.push({
                    id: data[0].id,
                    name: file.name,
                    size: file.size,
                });
            }
        } catch (e) {
            console.error('[mail v3] upload error:', e);
        }
    }

    async _uploadInlineImage(file) {
        try {
            const formData = new FormData();
            formData.append('ufile', file);
            formData.append('csrf_token', odoo.csrf_token);
            const res = await fetch('/web/binary/upload_attachment', {
                method: 'POST',
                body: formData,
            });
            const data = await res.json();
            if (data && data[0] && data[0].id) {
                const attId = data[0].id;
                const imgUrl = '/web/image/' + attId;
                this._execCommand('insertHTML',
                    '<img src="' + imgUrl + '" style="max-width: 100%; height: auto;" class="mv3-inline-image"/>');
            }
        } catch (e) {
            console.error('[mail v3] inline image upload error:', e);
        }
    }

    removeAttachment(index) {
        this.state.attachments.splice(index, 1);
    }

    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    // ── Emoji Picker ────────────────────────────────────────

    toggleEmojiPicker() {
        this.state.showEmojiPicker = !this.state.showEmojiPicker;
        this.state.emojiSearch = '';
    }

    onEmojiSearchInput(ev) {
        this.state.emojiSearch = ev.target.value.toLowerCase();
    }

    insertEmoji(emoji) {
        this.editorRef.el?.focus();
        document.execCommand('insertText', false, emoji);
        this._syncBody();
        this.state.showEmojiPicker = false;
    }

    get filteredEmojis() {
        const search = this.state.emojiSearch;
        if (!search) return EMOJI_DATA;
        return EMOJI_DATA.filter(e => e.keywords.some(k => k.includes(search)));
    }

    // ── Autosave ────────────────────────────────────────────

    _triggerAutosaveDebounce() {
        if (this._autosaveDebounce) clearTimeout(this._autosaveDebounce);
        this._autosaveDebounce = setTimeout(() => this.autosave(), 15000);
    }

    async autosave() {
        if (!this.props.draftId) return;
        this.state.saveStatus = 'saving';
        try {
            await rpc('/cf/mail/v3/draft/' + this.props.draftId + '/autosave', {
                to_emails: this.state.to,
                cc_emails: this.state.cc,
                bcc_emails: this.state.bcc,
                subject: this.state.subject,
                body_html: this.state.body,
                attachment_ids: this.state.attachments.map(a => a.id),
            });
            const now = new Date();
            this.state.lastSaveTime = now.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
            this.state.saveStatus = 'saved';
        } catch (e) {
            console.warn('[mail v3] autosave error:', e);
            this.state.saveStatus = 'error';
        }
    }

    get autosaveLabel() {
        if (this.state.saveStatus === 'saving') return 'Salvataggio...';
        if (this.state.saveStatus === 'error') return '\u26A0 Errore salvataggio';
        if (this.state.saveStatus === 'saved' && this.state.lastSaveTime) {
            return 'Bozza salvata alle ' + this.state.lastSaveTime;
        }
        return '';
    }

    // ── Template Panel ──────────────────────────────────────

    toggleTemplatePanel() {
        this.state.showTemplatePanel = !this.state.showTemplatePanel;
    }

    async _loadTemplates() {
        try {
            const res = await rpc('/cf/mail/v3/templates/list', {
                account_id: this.props.prefilled?.account_id || false,
            });
            this.state.templates = res.templates || [];
        } catch (e) {
            console.warn('[mail v3] template load error:', e);
        }
    }

    async _detectPartnerLanguage() {
        if (!this.state.to) return;
        const email = this.state.to.split(',')[0]?.trim();
        if (!email) return;
        try {
            const res = await rpc('/cf/mail/v3/partner/detect_language', {
                email: email,
                partner_id: this.props.prefilled?.partner_id || false,
            });
            if (res.lang) {
                this.state.detectedLang = res.lang;
                this.state.templateLangFilter = res.lang;
            }
        } catch (e) {
            // Non-critical
        }
    }

    get filteredTemplates() {
        let tpls = this.state.templates;
        const search = this.state.templateSearch.toLowerCase();
        const lang = this.state.templateLangFilter;

        if (lang) {
            tpls = [
                ...tpls.filter(t => t.language === lang),
                ...tpls.filter(t => t.language !== lang),
            ];
        }
        if (search) {
            tpls = tpls.filter(t =>
                (t.name || '').toLowerCase().includes(search) ||
                (t.subject || '').toLowerCase().includes(search) ||
                (t.category || '').toLowerCase().includes(search)
            );
        }
        return tpls;
    }

    onTemplateSearchInput(ev) {
        this.state.templateSearch = ev.target.value;
    }

    onTemplateLangFilter(ev) {
        this.state.templateLangFilter = ev.target.value;
    }

    async onTemplateHover(tpl) {
        this.state.hoveredTemplate = tpl.id;
        try {
            const res = await rpc('/cf/mail/v3/template/' + tpl.id + '/preview', {
                partner_id: this.props.prefilled?.partner_id || false,
                thread_id: this.props.prefilled?.thread_id || false,
            });
            this.state.hoveredPreviewHtml = res.body_html || tpl.subject || '';
        } catch {
            this.state.hoveredPreviewHtml = tpl.subject || '';
        }
    }

    onTemplateLeave() {
        this.state.hoveredTemplate = null;
        this.state.hoveredPreviewHtml = '';
    }

    async applyTemplate(tpl) {
        try {
            const res = await rpc('/cf/mail/v3/template/' + tpl.id + '/preview', {
                partner_id: this.props.prefilled?.partner_id || false,
                thread_id: this.props.prefilled?.thread_id || false,
            });
            if (res.subject) this.state.subject = res.subject;
            if (res.body_html && this.editorRef.el) {
                this.editorRef.el.innerHTML = res.body_html;
                if (this.state.signatureHtml) {
                    this._appendSignature(this.state.signatureHtml);
                }
                this._syncBody();
            }
            this.state.showTemplatePanel = false;
        } catch (e) {
            console.error('[mail v3] template apply error:', e);
        }
    }

    getLangBadge(lang) {
        const map = {
            'it_IT': '\u{1F1EE}\u{1F1F9}', 'en_US': '\u{1F1EC}\u{1F1E7}',
            'de_DE': '\u{1F1E9}\u{1F1EA}', 'es_ES': '\u{1F1EA}\u{1F1F8}',
            'fr_FR': '\u{1F1EB}\u{1F1F7}',
        };
        return map[lang] || lang || '';
    }

    getCategoryLabel(cat) {
        const map = {
            'follow_up': 'Follow-up', 'sample_offer': 'Sample/Offer',
            'post_fair': 'Post-Fair', 'quote': 'Quote',
            'reminder': 'Reminder', 'generic': 'Generic',
        };
        return map[cat] || cat || '';
    }

    isTemplateDetectedLang(tpl) {
        return this.state.detectedLang && tpl.language === this.state.detectedLang;
    }

    // ── Snippet Autocomplete ───────────────────────────────

    _getSlashQuery() {
        const sel = window.getSelection();
        if (!sel || sel.rangeCount === 0) return null;
        const range = sel.getRangeAt(0);
        const node = range.startContainer;
        if (node.nodeType !== Node.TEXT_NODE) return null;
        const text = node.textContent.substring(0, range.startOffset);
        const match = text.match(/(?:^|\s)(\/\S*)$/);
        if (!match) return null;
        return { query: match[1], node, offset: range.startOffset, matchStart: range.startOffset - match[1].length };
    }

    _onEditorKeydown(ev) {
        if (!this.state.snippetVisible) return;
        if (ev.key === 'ArrowDown') {
            ev.preventDefault();
            this.state.snippetSelectedIndex = Math.min(
                this.state.snippetSelectedIndex + 1, this.state.snippetResults.length - 1);
        } else if (ev.key === 'ArrowUp') {
            ev.preventDefault();
            this.state.snippetSelectedIndex = Math.max(this.state.snippetSelectedIndex - 1, 0);
        } else if (ev.key === 'Enter' || ev.key === 'Tab') {
            if (this.state.snippetResults.length > 0) {
                ev.preventDefault();
                this._applySnippet(this.state.snippetResults[this.state.snippetSelectedIndex]);
            }
        } else if (ev.key === 'Escape') {
            ev.preventDefault();
            this.state.snippetVisible = false;
        }
    }

    _onEditorKeyup(ev) {
        if (['ArrowDown', 'ArrowUp', 'Enter', 'Tab', 'Escape'].includes(ev.key)) return;
        const slashData = this._getSlashQuery();
        if (!slashData || slashData.query.length < 2) {
            this.state.snippetVisible = false;
            return;
        }
        this.state.snippetQuery = slashData.query;
        if (this._snippetDebounce) clearTimeout(this._snippetDebounce);
        this._snippetDebounce = setTimeout(() => this._fetchSnippets(slashData.query), 200);
    }

    async _fetchSnippets(query) {
        try {
            const res = await rpc('/cf/mail/v3/snippets/list', { code_prefix: query });
            this.state.snippetResults = res.snippets || [];
            this.state.snippetSelectedIndex = 0;
            this.state.snippetVisible = this.state.snippetResults.length > 0;
        } catch (e) {
            this.state.snippetVisible = false;
        }
    }

    async _applySnippet(snippet) {
        this.state.snippetVisible = false;
        try {
            const res = await rpc('/cf/mail/v3/snippets/apply', {
                snippet_id: snippet.id,
                partner_id: this.props.prefilled?.partner_id || false,
            });
            if (res.success && res.body) {
                // Replace /code with snippet body in editor
                const slashData = this._getSlashQuery();
                if (slashData) {
                    const { node, matchStart, offset } = slashData;
                    const before = node.textContent.substring(0, matchStart);
                    const after = node.textContent.substring(offset);
                    node.textContent = before + after;
                    // Insert rendered HTML at cursor
                    const sel = window.getSelection();
                    const range = document.createRange();
                    range.setStart(node, matchStart);
                    range.collapse(true);
                    sel.removeAllRanges();
                    sel.addRange(range);
                    document.execCommand('insertHTML', false, res.body);
                }
                if (res.subject && !this.state.subject) {
                    this.state.subject = res.subject;
                }
                this._syncBody();
            }
        } catch (e) {
            console.error('[mail v3] snippet apply error:', e);
        }
    }

    onSnippetClick(snippet) {
        this._applySnippet(snippet);
    }

    // ── Preview Modal ───────────────────────────────────────

    async openPreviewModal() {
        this.state.showPreviewModal = true;
        this.state.previewData = {
            from: this.props.prefilled?.from_email || '',
            to: this.state.to,
            subject: this.state.subject,
            body_html: this.state.body,
        };
    }

    closePreviewModal() {
        this.state.showPreviewModal = false;
        this.state.previewData = null;
    }

    // ── Send / Discard ──────────────────────────────────────

    async send() {
        if (!this.state.to.trim()) {
            this.state.error = 'Inserisci almeno un destinatario';
            return;
        }
        this.state.sending = true;
        this.state.error = '';
        await this.autosave();

        try {
            const res = await rpc('/cf/mail/v3/draft/' + this.props.draftId + '/send');
            if (res.success) {
                if (this.props.onSent) this.props.onSent();
            } else {
                this.state.error = res.error || 'Errore invio';
            }
        } catch (e) {
            this.state.error = 'Errore: ' + (e.message || e);
        }
        this.state.sending = false;
    }

    discard() {
        if (this.props.onClose) this.props.onClose();
    }
}
