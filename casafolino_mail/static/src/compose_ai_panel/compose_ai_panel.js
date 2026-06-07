/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class CFComposeAIPanel extends Component {
    static template = "casafolino_mail.CFComposeAIPanel";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            collapsed: false,
            isLoading: false,
            tone: null,
            language: null,
            signature: null,
            quickReplies: [],
            currentTab: "replies",
        });

        this.debouncedLangDetect = useDebounced(this._detectLanguage.bind(this), 800);

        onWillStart(async () => {
            await this._loadInitial();
        });
    }

    async _loadInitial() {
        const partnerId = this.props.partnerId || null;
        const threadId = this.props.threadId || null;
        await Promise.all([
            this._refreshSignature(partnerId),
            this._refreshTone(threadId, "", partnerId),
            this._refreshQuickReplies(threadId, partnerId),
        ]);
        if (!this.state.quickReplies.length) {
            this.state.currentTab = "tone";
        }
    }

    async _refreshTone(threadId, body, partnerId) {
        this.state.isLoading = true;
        try {
            this.state.tone = await this.orm.call(
                "cf.mail.compose.ai", "cf_suggest_tone", [],
                { thread_id: threadId, current_body: body, partner_id: partnerId });
        } catch (e) { /* silent */ }
        this.state.isLoading = false;
    }

    async _detectLanguage(text, partnerId) {
        if (!text || text.length < 20) { this.state.language = null; return; }
        try {
            this.state.language = await this.orm.call(
                "cf.mail.compose.ai", "cf_detect_language", [],
                { text: text, partner_id: partnerId });
        } catch (e) { /* silent */ }
    }

    async _refreshSignature(partnerId) {
        try {
            this.state.signature = await this.orm.call(
                "cf.mail.compose.ai", "cf_get_signature", [],
                { partner_id: partnerId });
        } catch (e) { /* silent */ }
    }

    async _refreshQuickReplies(threadId, partnerId) {
        try {
            const result = await this.orm.call(
                "cf.mail.compose.ai", "cf_suggest_quick_replies", [],
                { thread_id: threadId, partner_id: partnerId });
            this.state.quickReplies = result.replies || [];
        } catch (e) { /* silent */ }
    }

    // --- Handlers ---

    onTabChange(tab) {
        this.state.currentTab = tab;
    }

    onCollapseToggle() {
        this.state.collapsed = !this.state.collapsed;
    }

    async onTranslateClick() {
        if (!this.state.language?.mismatch) return;
        const currentText = this.props.getBody?.() || "";
        if (!currentText) return;
        try {
            const result = await this.orm.call(
                "cf.mail.compose.ai", "cf_translate", [],
                { text: currentText, target_lang: this.state.language.partner_lang });
            this.props.onApplyBody?.(result.translated);
            this.notification.add("Body tradotto", { type: "success" });
        } catch (e) {
            this.notification.add("Traduzione fallita", { type: "danger" });
        }
    }

    onAcceptToneRewrite() {
        if (!this.state.tone?.rewrite_hint) return;
        this.notification.add(this.state.tone.rewrite_hint, { type: "info" });
    }

    onApplySignature() {
        if (!this.state.signature?.signature_html) return;
        this.props.onAppendBody?.(this.state.signature.signature_html);
    }

    onApplyQuickReply(reply) {
        this.props.onApplyBody?.(this._textToHtml(reply.text));
    }

    onAppendQuickReply(reply) {
        this.props.onAppendBody?.(this._textToHtml(reply.text));
    }

    _textToHtml(text) {
        return (text || "")
            .split(/\n{2,}/)
            .map((part) => "<p>" + part.replace(/\n/g, "<br/>") + "</p>")
            .join("");
    }

    onBodyChanged(text) {
        this.debouncedLangDetect(text, this.props.partnerId);
    }
}
