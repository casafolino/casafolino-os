/** @odoo-module **/
import { Component, useState, onWillStart, useEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class LavagnaDrawerTask extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaDrawerTask";
    static props = ["*"];

    setup() {
        this.env = useEnv();
        this.orm = useService("orm");
        this.state = useState({
            task: null,
            loading: true,
            activeTab: 'details',
            messages: [],
        });

        onWillStart(() => this.loadTask());
    }

    async loadTask() {
        if (!this.props.taskId) return;
        this.state.loading = true;
        try {
            const [task] = await this.orm.read('project.task', [this.props.taskId], [
                'name', 'description', 'stage_id', 'partner_id', 'user_ids',
                'date_deadline', 'priority', 'kanban_state', 'cf_tag_ids',
                'project_id',
            ]);
            this.state.task = task;

            // Load messages
            const messages = await this.orm.searchRead('mail.message', [
                ['model', '=', 'project.task'],
                ['res_id', '=', this.props.taskId],
                ['message_type', 'in', ['email', 'comment']],
            ], ['subject', 'body', 'author_id', 'date', 'message_type'], {
                order: 'date desc', limit: 20,
            });
            this.state.messages = messages;
        } catch (e) {
            this.state.task = null;
        } finally {
            this.state.loading = false;
        }
    }

    close() {
        this.env.actions.closeTaskDrawer();
    }

    openFullForm() {
        this.env.actions.openOdooRecord('project.task', this.props.taskId);
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    stripHtml(html) {
        if (!html) return '';
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        return tmp.textContent || tmp.innerText || '';
    }

    formatDate(isoStr) {
        if (!isoStr) return '';
        return new Date(isoStr).toLocaleDateString('it-IT', {
            day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
        });
    }
}
