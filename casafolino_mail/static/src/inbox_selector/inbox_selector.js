/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

class CFInboxSelectorState {
    constructor() {
        this.viewingAsUserId = user.userId;
        this.listeners = new Set();
    }
    subscribe(cb) {
        this.listeners.add(cb);
        return () => this.listeners.delete(cb);
    }
    notify() {
        for (const cb of this.listeners) cb(this.viewingAsUserId);
    }
}

export const cfInboxSelectorState = new CFInboxSelectorState();

export class CFInboxSelector extends Component {
    static template = "casafolino_mail.CFInboxSelector";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            isVisible: false,
            isOpen: false,
            viewingAsUserId: user.userId,
            supervisableUsers: [],
        });

        onWillStart(async () => {
            try {
                const users = await this.orm.call(
                    "casafolino.mail.message", "cf_get_supervisable_users", []);
                this.state.supervisableUsers = users || [];
                this.state.isVisible = users.length > 1;
            } catch (e) {
                this.state.isVisible = false;
            }
        });
    }

    get currentUser() {
        return this.state.supervisableUsers.find(
            (u) => u.id === this.state.viewingAsUserId
        ) || { name: "?", color_class: "gray", is_self: true };
    }

    getInitials(name) {
        if (!name) return "?";
        return name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
    }

    onToggleDropdown() {
        this.state.isOpen = !this.state.isOpen;
    }

    onSelectUser(userId) {
        this.state.viewingAsUserId = userId;
        this.state.isOpen = false;
        cfInboxSelectorState.viewingAsUserId = userId;
        cfInboxSelectorState.notify();
        const target = this.state.supervisableUsers.find((u) => u.id === userId);
        this.notification.add(
            target?.is_self ? "Tornato alla tua inbox" : "Vedo come " + (target?.name || "?"),
            { type: "info" }
        );
    }
}
