/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class SenderDecisionPopup extends Component {
    static template = "casafolino_mail.SenderDecisionPopup";
    static props = ["*"];

    setup() {
        this.state = useState({
            loading: false,
            decided: false,
        });
    }

    get senderInitials() {
        const email = this.props.senderEmail || '';
        const name = this.props.senderName || email;
        const parts = name.split(/[\s@.]+/).filter(Boolean);
        return parts.slice(0, 2).map(p => p[0].toUpperCase()).join('');
    }

    async onKeep() {
        this.state.loading = true;
        try {
            await rpc('/cf/mail/v3/sender_decision/keep', {
                email: this.props.senderEmail,
            });
            this.state.decided = true;
            if (this.props.onDecision) this.props.onDecision('kept');
        } catch (e) {
            console.error('[sender decision] keep error:', e);
        }
        this.state.loading = false;
    }

    async onDismiss() {
        this.state.loading = true;
        try {
            const res = await rpc('/cf/mail/v3/sender_decision/dismiss', {
                email: this.props.senderEmail,
            });
            this.state.decided = true;
            if (this.props.onDismiss) {
                this.props.onDismiss(this.props.senderEmail, res.undo_token, res.pending_deletion_count);
            }
        } catch (e) {
            console.error('[sender decision] dismiss error:', e);
        }
        this.state.loading = false;
    }

    async onCreateLead() {
        await this.onKeep();
        if (this.props.onCreateLead) this.props.onCreateLead();
    }

    async onCreateProject() {
        await this.onKeep();
        if (this.props.onCreateProject) this.props.onCreateProject();
    }

    onDefer() {
        rpc('/cf/mail/v3/sender_decision/defer', {
            email: this.props.senderEmail,
        }).catch(() => {});
        if (this.props.onDecision) this.props.onDecision('deferred');
    }
}
