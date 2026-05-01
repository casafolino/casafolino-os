/** @odoo-module **/
/**
 * F2.6: Panel "To-Do" — standalone cf.todo on initiative (no task parent).
 */
import { Component, useState, useEnv } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class LavagnaPanelTodo extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaPanelTodo";
    static props = ["*"];

    setup() {
        this.env = useEnv();
        this.state = useState({
            addingTodo: false,
            newTodoName: '',
            editingId: null,
            editingName: '',
        });
    }

    get todos() {
        return this.props.todos || [];
    }

    get todoStats() {
        const total = this.todos.length;
        const done = this.todos.filter(t => t.done).length;
        return { total, done, pct: total ? Math.round((done / total) * 100) : 0 };
    }

    // Add
    onNewInput(ev) { this.state.newTodoName = ev.target.value; }

    onNewKeydown(ev) {
        if (ev.key === 'Enter' && this.state.newTodoName.trim()) this.addTodo();
        else if (ev.key === 'Escape') { this.state.addingTodo = false; this.state.newTodoName = ''; }
    }

    async addTodo() {
        const name = this.state.newTodoName.trim();
        if (!name) return;
        try {
            const result = await rpc('/casafolino/todo/create', {
                initiative_id: this.env.initiativeId, name,
            });
            if (result && !result.error) {
                this.todos.push(result);
                this.state.newTodoName = '';
            }
        } catch {}
    }

    // Toggle
    async toggleTodo(todo) {
        const newDone = !todo.done;
        todo.done = newDone;
        try { await rpc('/casafolino/todo/update', { id: todo.id, done: newDone }); }
        catch { todo.done = !newDone; }
    }

    // Edit inline
    startEdit(todo) { this.state.editingId = todo.id; this.state.editingName = todo.name; }
    onEditInput(ev) { this.state.editingName = ev.target.value; }
    onEditKeydown(ev, todo) {
        if (ev.key === 'Enter') this.saveEdit(todo);
        else if (ev.key === 'Escape') this.state.editingId = null;
    }
    async saveEdit(todo) {
        const name = this.state.editingName.trim();
        if (!name) return;
        todo.name = name;
        this.state.editingId = null;
        await rpc('/casafolino/todo/update', { id: todo.id, name });
    }

    // Delete
    async deleteTodo(todo) {
        const idx = this.todos.indexOf(todo);
        if (idx >= 0) this.todos.splice(idx, 1);
        await rpc('/casafolino/todo/delete', { id: todo.id });
    }

    // Drag reorder
    onDragStart(ev, todo) {
        ev.dataTransfer.effectAllowed = 'move';
        ev.dataTransfer.setData('text/plain', String(todo.id));
    }
    onDragOver(ev) { ev.preventDefault(); }
    async onDrop(ev, targetTodo) {
        ev.preventDefault();
        const dragId = parseInt(ev.dataTransfer.getData('text/plain'));
        if (!dragId || dragId === targetTodo.id) return;
        const todos = this.todos;
        const di = todos.findIndex(t => t.id === dragId);
        const ti = todos.findIndex(t => t.id === targetTodo.id);
        if (di < 0 || ti < 0) return;
        const [moved] = todos.splice(di, 1);
        todos.splice(ti, 0, moved);
        await rpc('/casafolino/todo/reorder', {
            initiative_id: this.env.initiativeId,
            ordered_ids: todos.map(t => t.id),
        });
    }
}
