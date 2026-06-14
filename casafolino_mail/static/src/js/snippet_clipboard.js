/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

class CopySnippetAction extends Component {
    static template = "casafolino_mail.CopySnippetEmpty";
    static props = ["*"];

    setup() {
        const text = (this.props.action && this.props.action.params && this.props.action.params.text) || '';
        if (text && navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                this.env.services.notification.add(
                    "Snippet copiato negli appunti! Incollalo nella risposta.",
                    { type: "success", sticky: false }
                );
            }).catch(() => {
                this.env.services.notification.add(
                    "Clipboard non disponibile. Seleziona e copia manualmente.",
                    { type: "warning" }
                );
            });
        }
        this.env.services.action.doAction({ type: "ir.actions.act_window_close" });
    }
}

registry.category("actions").add("casafolino_mail.copy_snippet", CopySnippetAction);
