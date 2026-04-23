/** @odoo-module **/
import { Component } from "@odoo/owl";

export class ReadingPane extends Component {
    static template = "casafolino_mail.ReadingPane";
    static props = ["*"];

    getTimeGap() {
        const messages = this.props.messages || [];
        if (messages.length === 0) return null;

        const inbound = [...messages].reverse().find(
            m => m.direction === 'inbound' || m.direction_computed === 'inbound'
        );
        const outbound = [...messages].reverse().find(
            m => m.direction === 'outbound' || m.direction_computed === 'outbound'
        );

        if (!inbound) return null;

        const lastInDate = new Date(inbound.email_date);
        const now = new Date();
        const daysSinceInbound = Math.floor((now - lastInDate) / (1000 * 60 * 60 * 24));

        if (outbound) {
            const lastOutDate = new Date(outbound.email_date);
            if (lastOutDate > lastInDate) return null;
            const daysSinceReply = Math.floor((now - lastOutDate) / (1000 * 60 * 60 * 24));
            if (daysSinceReply > 3) {
                return {
                    text: 'Ultima risposta ' + daysSinceReply + ' gg fa',
                    severity: daysSinceReply > 7 ? 'critical' : 'warning',
                    icon: daysSinceReply > 7 ? '\u26a0\ufe0f' : '\u23f1\ufe0f',
                };
            }
        } else if (daysSinceInbound > 3) {
            return {
                text: 'Nessuna risposta da ' + daysSinceInbound + ' gg',
                severity: daysSinceInbound > 7 ? 'critical' : 'warning',
                icon: '\u26a0\ufe0f',
            };
        }
        return null;
    }

    onAction(action, msgId) {
        this.props.onAction(action, msgId);
    }

    onReply(msgId) {
        if (this.props.onReply) this.props.onReply(msgId);
    }

    onReplyAll(msgId) {
        if (this.props.onReplyAll) this.props.onReplyAll(msgId);
    }

    onForward(msgId) {
        if (this.props.onForward) this.props.onForward(msgId);
    }

    onAiReply(msgId) {
        if (this.props.onAiReply) this.props.onAiReply(msgId);
    }

    onSnooze(msgId) {
        if (this.props.onSnooze) this.props.onSnooze();
    }

    onCreateLead() {
        if (this.props.onCreateLead) this.props.onCreateLead();
    }

    onCreateProject() {
        if (this.props.onCreateProject) this.props.onCreateProject();
    }

    onDismissSender() {
        if (this.props.onDismissSender) this.props.onDismissSender();
    }

    formatDate(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        return d.toLocaleDateString('it-IT', {
            day: '2-digit', month: 'short', year: 'numeric',
            hour: '2-digit', minute: '2-digit',
        });
    }
}
