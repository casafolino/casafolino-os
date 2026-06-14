/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class ReplyAssistant extends Component {
    static template = "casafolino_mail.ReplyAssistant";
    static props = ["*"];

    setup() {
        this.state = useState({
            loading: true,
            error: '',
            bozze: [],
        });

        onWillStart(async () => {
            await this.loadDrafts();
        });
    }

    async loadDrafts() {
        this.state.loading = true;
        this.state.error = '';
        try {
            const res = await rpc('/cf/mail/v3/message/' + this.props.messageId + '/reply_assistant');
            if (res.error) {
                this.state.error = res.error;
            } else {
                this.state.bozze = res.bozze || [];
            }
        } catch (e) {
            this.state.error = 'Errore connessione AI: ' + (e.message || e);
        }
        this.state.loading = false;
    }

    selectDraft(bozza) {
        if (this.props.onSelectDraft) {
            this.props.onSelectDraft(bozza.testo);
        }
    }

    close() {
        if (this.props.onClose) {
            this.props.onClose();
        }
    }

    getDraftIcon(tipo) {
        if (tipo === 'Diretta') return '⚡';
        if (tipo === 'Relazionale') return '🤝';
        if (tipo === 'Proattiva') return '🚀';
        return '📝';
    }
}
