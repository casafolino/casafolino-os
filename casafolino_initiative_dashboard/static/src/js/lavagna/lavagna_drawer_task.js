/** @odoo-module **/
import { Component, useState, onWillStart, onWillUpdateProps, useEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

const PRIORITY_LABELS = [
    { value: '0', label: 'Normale', color: '#A89B85', icon: 'fa-minus' },
    { value: '1', label: 'Alta', color: '#f39c12', icon: 'fa-arrow-up' },
    { value: '2', label: 'Urgente', color: '#C0392B', icon: 'fa-exclamation' },
];

export class LavagnaDrawerTask extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaDrawerTask";
    static props = ["*"];

    setup() {
        this.env = useEnv();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            task: null,
            loading: true,
            activeTab: 'details',
            messages: [],
            todos: [],
            attachments: [],
            // Todo inline add
            newTodoName: '',
            addingTodo: false,
            // Edit inline
            editingTodoId: null,
            editingTodoName: '',
        });
        this.priorityOptions = PRIORITY_LABELS;

        onWillStart(() => this.loadTask());
        onWillUpdateProps((nextProps) => {
            if (nextProps.taskId !== this.props.taskId) {
                this.loadTask(nextProps.taskId);
            }
        });
    }

    async loadTask(taskId) {
        const id = taskId || this.props.taskId;
        if (!id) return;
        this.state.loading = true;
        try {
            const [task] = await this.orm.read('project.task', [id], [
                'name', 'description', 'stage_id', 'partner_id', 'user_ids',
                'date_deadline', 'priority', 'kanban_state', 'cf_tag_ids',
                'project_id', 'cf_todo_count', 'cf_todo_progress',
            ]);
            this.state.task = task;

            // Messages
            const messages = await this.orm.searchRead('mail.message', [
                ['model', '=', 'project.task'],
                ['res_id', '=', id],
                ['message_type', 'in', ['email', 'comment']],
            ], ['subject', 'body', 'author_id', 'date', 'message_type'], {
                order: 'date desc', limit: 20,
            });
            this.state.messages = messages;

            // Todos
            const todos = await this.orm.searchRead('cf.todo', [
                ['task_id', '=', id],
            ], ['name', 'done', 'done_date', 'sequence', 'assigned_user_id'], {
                order: 'sequence asc, create_date asc',
            });
            this.state.todos = todos;

            // Attachments
            const attachments = await this.orm.searchRead('ir.attachment', [
                ['res_model', '=', 'project.task'],
                ['res_id', '=', id],
            ], ['name', 'mimetype', 'file_size', 'create_date'], {
                order: 'create_date desc', limit: 20,
            });
            this.state.attachments = attachments;

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

    // Priority
    async setPriority(value) {
        await this.orm.write('project.task', [this.props.taskId], { priority: value });
        this.state.task.priority = value;
    }

    getPriorityLabel() {
        const p = this.state.task ? this.state.task.priority : '0';
        return PRIORITY_LABELS.find(o => o.value === p) || PRIORITY_LABELS[0];
    }

    // Todo CRUD
    async addTodo() {
        const name = this.state.newTodoName.trim();
        if (!name) return;
        try {
            const result = await rpc('/casafolino/todo/create', {
                task_id: this.props.taskId,
                name: name,
            });
            if (result && !result.error) {
                this.state.todos.push(result);
                this.state.newTodoName = '';
                this.state.addingTodo = false;
            }
        } catch (e) {
            this.notification.add('Errore creazione todo', { type: 'danger' });
        }
    }

    async toggleTodo(todo) {
        const newDone = !todo.done;
        todo.done = newDone; // optimistic
        try {
            await rpc('/casafolino/todo/update', { id: todo.id, done: newDone });
        } catch {
            todo.done = !newDone; // rollback
        }
    }

    startEditTodo(todo) {
        this.state.editingTodoId = todo.id;
        this.state.editingTodoName = todo.name;
    }

    async saveEditTodo(todo) {
        const name = this.state.editingTodoName.trim();
        if (!name) return;
        todo.name = name;
        this.state.editingTodoId = null;
        await rpc('/casafolino/todo/update', { id: todo.id, name: name });
    }

    cancelEditTodo() {
        this.state.editingTodoId = null;
    }

    async deleteTodo(todo) {
        const idx = this.state.todos.indexOf(todo);
        if (idx >= 0) this.state.todos.splice(idx, 1);
        await rpc('/casafolino/todo/delete', { id: todo.id });
    }

    onNewTodoInput(ev) {
        this.state.newTodoName = ev.target.value;
    }

    onNewTodoKeydown(ev) {
        if (ev.key === 'Enter') this.addTodo();
        else if (ev.key === 'Escape') {
            this.state.addingTodo = false;
            this.state.newTodoName = '';
        }
    }

    onEditTodoInput(ev) {
        this.state.editingTodoName = ev.target.value;
    }

    onEditTodoKeydown(ev, todo) {
        if (ev.key === 'Enter') this.saveEditTodo(todo);
        else if (ev.key === 'Escape') this.cancelEditTodo();
    }

    // Todo drag reorder
    onTodoDragStart(ev, todo) {
        ev.dataTransfer.effectAllowed = 'move';
        ev.dataTransfer.setData('text/plain', String(todo.id));
        this._dragTodoId = todo.id;
    }

    onTodoDragOver(ev) {
        ev.preventDefault();
    }

    async onTodoDrop(ev, targetTodo) {
        ev.preventDefault();
        const dragId = parseInt(ev.dataTransfer.getData('text/plain'));
        if (!dragId || dragId === targetTodo.id) return;
        const todos = this.state.todos;
        const dragIdx = todos.findIndex(t => t.id === dragId);
        const targetIdx = todos.findIndex(t => t.id === targetTodo.id);
        if (dragIdx < 0 || targetIdx < 0) return;
        const [moved] = todos.splice(dragIdx, 1);
        todos.splice(targetIdx, 0, moved);
        // Persist new order
        const orderedIds = todos.map(t => t.id);
        await rpc('/casafolino/todo/reorder', {
            task_id: this.props.taskId,
            ordered_ids: orderedIds,
        });
    }

    get todoStats() {
        const total = this.state.todos.length;
        const done = this.state.todos.filter(t => t.done).length;
        const pct = total ? Math.round((done / total) * 100) : 0;
        return { total, done, pct };
    }

    // Helpers
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

    formatFileSize(bytes) {
        if (!bytes) return '';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return Math.round(bytes / 1024) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    }
}
