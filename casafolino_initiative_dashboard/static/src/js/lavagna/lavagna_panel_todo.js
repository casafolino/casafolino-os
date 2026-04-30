/** @odoo-module **/
import { Component, useEnv } from "@odoo/owl";

export class LavagnaPanelTodo extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaPanelTodo";
    static props = ["*"];

    setup() {
        this.env = useEnv();
    }

    onTodoClick(todo) {
        this.env.actions.openTaskDrawer(todo.id);
    }

    isOverdue(todo) {
        if (!todo.date_deadline) return false;
        return new Date(todo.date_deadline) < new Date();
    }
}
