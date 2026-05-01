/** @odoo-module **/
import { Component, useState, onWillStart, onWillUpdateProps, useEnv, useRef, onPatched } from "@odoo/owl";
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
        this.notesRef = useRef("notesEditor");
        this.chatterRef = useRef("chatterList");
        this.state = useState({
            task: null,
            loading: true,
            activeTab: 'details',
            messages: [],
            todos: [],
            attachments: [],
            // Notes editing
            notesEditing: false,
            notesDirty: false,
            // Chatter composer
            newMessage: '',
            sendingMessage: false,
            // Todo inline add
            newTodoName: '',
            addingTodo: false,
            editingTodoId: null,
            editingTodoName: '',
        });
        this.priorityOptions = PRIORITY_LABELS;
        this._saveTimer = null;

        onWillStart(() => this.loadTask());
        onWillUpdateProps((nextProps) => {
            if (nextProps.taskId !== this.props.taskId) {
                this.loadTask(nextProps.taskId);
            }
        });
        onPatched(() => {
            if (this.state.activeTab === 'messages' && this.chatterRef.el) {
                this.chatterRef.el.scrollTop = this.chatterRef.el.scrollHeight;
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

            const messages = await this.orm.searchRead('mail.message', [
                ['model', '=', 'project.task'],
                ['res_id', '=', id],
                ['message_type', 'in', ['email', 'comment', 'notification']],
            ], ['subject', 'body', 'author_id', 'date', 'message_type'], {
                order: 'date asc', limit: 50,
            });
            this.state.messages = messages;

            const todos = await this.orm.searchRead('cf.todo', [
                ['task_id', '=', id],
            ], ['name', 'done', 'done_date', 'sequence', 'assigned_user_id'], {
                order: 'sequence asc, create_date asc',
            });
            this.state.todos = todos;

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

    close() { this.env.actions.closeTaskDrawer(); }
    openFullForm() { this.env.actions.openOdooRecord('project.task', this.props.taskId); }
    setTab(tab) { this.state.activeTab = tab; }

    // ===== Priority =====
    async setPriority(value) {
        await this.orm.write('project.task', [this.props.taskId], { priority: value });
        this.state.task.priority = value;
    }

    getPriorityLabel() {
        const p = this.state.task ? this.state.task.priority : '0';
        return PRIORITY_LABELS.find(o => o.value === p) || PRIORITY_LABELS[0];
    }

    // ===== Notes WYSIWYG (contenteditable + autosave) =====
    onNotesInput() {
        this.state.notesDirty = true;
        if (this._saveTimer) clearTimeout(this._saveTimer);
        this._saveTimer = setTimeout(() => this.saveNotes(), 1500);
    }

    onNotesFocus() {
        this.state.notesEditing = true;
    }

    onNotesBlur() {
        this.state.notesEditing = false;
        if (this.state.notesDirty) {
            this.saveNotes();
        }
    }

    async saveNotes() {
        if (this._saveTimer) clearTimeout(this._saveTimer);
        this.state.notesDirty = false;
        const el = this.notesRef.el;
        if (!el) return;
        const html = el.innerHTML;
        try {
            await this.orm.write('project.task', [this.props.taskId], {
                description: html || false,
            });
        } catch (e) {
            this.notification.add('Errore salvataggio note', { type: 'danger' });
        }
    }

    // Notes toolbar actions
    execCommand(cmd, value) {
        document.execCommand(cmd, false, value || null);
        this.onNotesInput();
    }

    insertLink() {
        const url = prompt('URL:');
        if (url) document.execCommand('createLink', false, url);
        this.onNotesInput();
    }

    // ===== Chatter composer =====
    onMsgInput(ev) { this.state.newMessage = ev.target.value; }

    onMsgKeydown(ev) {
        if (ev.key === 'Enter' && (ev.metaKey || ev.ctrlKey) && this.state.newMessage.trim()) {
            this.sendMessage();
        }
    }

    async sendMessage() {
        const body = this.state.newMessage.trim();
        if (!body || this.state.sendingMessage) return;
        this.state.sendingMessage = true;

        try {
            await this.orm.call('project.task', 'message_post', [[this.props.taskId]], {
                body: body,
                message_type: 'comment',
                subtype_xmlid: 'mail.mt_comment',
            });
            this.state.newMessage = '';
            // Reload messages
            const messages = await this.orm.searchRead('mail.message', [
                ['model', '=', 'project.task'],
                ['res_id', '=', this.props.taskId],
                ['message_type', 'in', ['email', 'comment', 'notification']],
            ], ['subject', 'body', 'author_id', 'date', 'message_type'], {
                order: 'date asc', limit: 50,
            });
            this.state.messages = messages;
        } catch (e) {
            this.notification.add('Errore invio messaggio', { type: 'danger' });
        } finally {
            this.state.sendingMessage = false;
        }
    }

    // ===== Todo CRUD =====
    async addTodo() {
        const name = this.state.newTodoName.trim();
        if (!name) return;
        try {
            const result = await rpc('/casafolino/todo/create', {
                task_id: this.props.taskId, name,
            });
            if (result && !result.error) {
                this.state.todos.push(result);
                this.state.newTodoName = '';
                this.state.addingTodo = false;
            }
        } catch { this.notification.add('Errore creazione todo', { type: 'danger' }); }
    }

    async toggleTodo(todo) {
        const newDone = !todo.done;
        todo.done = newDone;
        try { await rpc('/casafolino/todo/update', { id: todo.id, done: newDone }); }
        catch { todo.done = !newDone; }
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
        await rpc('/casafolino/todo/update', { id: todo.id, name });
    }

    cancelEditTodo() { this.state.editingTodoId = null; }

    async deleteTodo(todo) {
        const idx = this.state.todos.indexOf(todo);
        if (idx >= 0) this.state.todos.splice(idx, 1);
        await rpc('/casafolino/todo/delete', { id: todo.id });
    }

    onNewTodoInput(ev) { this.state.newTodoName = ev.target.value; }
    onNewTodoKeydown(ev) {
        if (ev.key === 'Enter') this.addTodo();
        else if (ev.key === 'Escape') { this.state.addingTodo = false; this.state.newTodoName = ''; }
    }
    onEditTodoInput(ev) { this.state.editingTodoName = ev.target.value; }
    onEditTodoKeydown(ev, todo) {
        if (ev.key === 'Enter') this.saveEditTodo(todo);
        else if (ev.key === 'Escape') this.cancelEditTodo();
    }

    // Todo drag
    onTodoDragStart(ev, todo) {
        ev.dataTransfer.effectAllowed = 'move';
        ev.dataTransfer.setData('text/plain', String(todo.id));
    }
    onTodoDragOver(ev) { ev.preventDefault(); }
    async onTodoDrop(ev, targetTodo) {
        ev.preventDefault();
        const dragId = parseInt(ev.dataTransfer.getData('text/plain'));
        if (!dragId || dragId === targetTodo.id) return;
        const todos = this.state.todos;
        const di = todos.findIndex(t => t.id === dragId);
        const ti = todos.findIndex(t => t.id === targetTodo.id);
        if (di < 0 || ti < 0) return;
        const [moved] = todos.splice(di, 1);
        todos.splice(ti, 0, moved);
        await rpc('/casafolino/todo/reorder', {
            task_id: this.props.taskId,
            ordered_ids: todos.map(t => t.id),
        });
    }

    get todoStats() {
        const total = this.state.todos.length;
        const done = this.state.todos.filter(t => t.done).length;
        return { total, done, pct: total ? Math.round((done / total) * 100) : 0 };
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
        const d = new Date(isoStr);
        const now = new Date();
        const diff = (now - d) / (1000 * 60 * 60);
        if (diff < 1) return 'ora';
        if (diff < 24) return Math.floor(diff) + 'h fa';
        if (diff < 48) return 'ieri';
        return d.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' });
    }

    formatFileSize(bytes) {
        if (!bytes) return '';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return Math.round(bytes / 1024) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    }
}
