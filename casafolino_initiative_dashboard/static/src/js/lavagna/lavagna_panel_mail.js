/** @odoo-module **/
/**
 * F2.6: Panel "Comunicazioni" — internal messages on cf.initiative via mail.thread.
 * Replaces old mail-on-task panel with internal discussion.
 */
import { Component, useState, useEnv, useRef, onMounted } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class LavagnaPanelMail extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaPanelMail";
    static props = ["*"];

    setup() {
        this.env = useEnv();
        this.state = useState({
            newMessage: '',
            sending: false,
        });
        this.scrollRef = useRef("msgList");

        onMounted(() => this.scrollToBottom());
    }

    get messages() {
        return this.props.messages || [];
    }

    scrollToBottom() {
        const el = this.scrollRef.el;
        if (el) el.scrollTop = el.scrollHeight;
    }

    onInputChange(ev) {
        this.state.newMessage = ev.target.value;
    }

    onInputKeydown(ev) {
        if ((ev.key === 'Enter' && (ev.metaKey || ev.ctrlKey)) && this.state.newMessage.trim()) {
            this.sendMessage();
        }
    }

    async sendMessage() {
        const body = this.state.newMessage.trim();
        if (!body || this.state.sending) return;

        this.state.sending = true;
        const optimisticMsg = {
            id: Date.now(),
            body: body,
            author_name: 'Tu',
            author_avatar: '',
            date: new Date().toISOString(),
            _pending: true,
        };

        // Optimistic add
        if (this.props.messages) {
            this.props.messages.push(optimisticMsg);
        }
        this.state.newMessage = '';
        this.scrollToBottom();

        try {
            const result = await rpc('/casafolino/initiative/internal_message/create', {
                initiative_id: this.env.initiativeId,
                body: body,
            });
            // Replace optimistic with real
            if (this.props.messages) {
                const idx = this.props.messages.indexOf(optimisticMsg);
                if (idx >= 0) this.props.messages.splice(idx, 1, result);
            }
        } catch (e) {
            // Mark as error
            optimisticMsg._error = true;
            optimisticMsg._pending = false;
        } finally {
            this.state.sending = false;
            this.scrollToBottom();
        }
    }

    formatDate(isoStr) {
        if (!isoStr) return '';
        const d = new Date(isoStr);
        const now = new Date();
        const diff = (now - d) / (1000 * 60 * 60);
        if (diff < 1) return 'ora';
        if (diff < 24) return Math.floor(diff) + 'h fa';
        if (diff < 48) return 'ieri';
        return d.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' });
    }

    stripHtml(html) {
        if (!html) return '';
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        return tmp.textContent || tmp.innerText || '';
    }
}
