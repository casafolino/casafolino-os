/** @odoo-module **/
import { Component } from "@odoo/owl";

export class ThreadList extends Component {
    static template = "casafolino_mail.ThreadList";
    static props = ["*"];

    get groupedThreads() {
        const groups = [];
        let currentKey = null;
        let currentGroup = null;

        for (const thread of this.props.threads || []) {
            const group = this.getDateGroup(thread.last_message_date);
            if (group.key !== currentKey) {
                currentKey = group.key;
                currentGroup = { ...group, threads: [] };
                groups.push(currentGroup);
            }
            currentGroup.threads.push(thread);
        }
        return groups;
    }

    selectThread(threadId) {
        this.props.onSelect(threadId);
    }

    toggleSelect(threadId) {
        if (this.props.onToggleSelect) {
            this.props.onToggleSelect(threadId);
        }
    }

    isSelected(threadId) {
        const ids = this.props.selectedThreadIds || [];
        return ids.includes(threadId);
    }

    getAccountColor(accountId) {
        const colors = ['#5A6E3A', '#2980B9', '#8E44AD'];
        const accounts = this.props.accounts || [];
        const idx = accounts.findIndex(a => a.id === accountId);
        return colors[idx >= 0 ? idx % colors.length : 0];
    }

    parseDate(dateStr) {
        if (!dateStr) {
            return null;
        }
        const normalized = dateStr.includes("T")
            ? dateStr
            : `${dateStr.replace(" ", "T")}Z`;
        const date = new Date(normalized);
        return Number.isNaN(date.getTime()) ? null : date;
    }

    startOfDay(date) {
        return new Date(date.getFullYear(), date.getMonth(), date.getDate());
    }

    startOfWeek(date) {
        const start = this.startOfDay(date);
        const day = start.getDay() || 7;
        start.setDate(start.getDate() - day + 1);
        return start;
    }

    getDateGroup(dateStr) {
        const date = this.parseDate(dateStr);
        if (!date) {
            return { key: "no-date", label: "Senza data" };
        }

        const now = new Date();
        const today = this.startOfDay(now);
        const yesterday = new Date(today);
        yesterday.setDate(today.getDate() - 1);
        const messageDay = this.startOfDay(date);

        if (messageDay.getTime() === today.getTime()) {
            return { key: "today", label: "Oggi" };
        }
        if (messageDay.getTime() === yesterday.getTime()) {
            return { key: "yesterday", label: "Ieri" };
        }
        if (date >= this.startOfWeek(now)) {
            return { key: "week", label: "Questa settimana" };
        }
        if (date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth()) {
            return { key: "month", label: "Questo mese" };
        }
        return { key: "older", label: "Più vecchie" };
    }

    formatThreadDate(dateStr) {
        const date = this.parseDate(dateStr);
        if (!date) {
            return "";
        }

        const now = new Date();
        const today = this.startOfDay(now);
        const yesterday = new Date(today);
        yesterday.setDate(today.getDate() - 1);
        const messageDay = this.startOfDay(date);
        const time = date.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });

        if (messageDay.getTime() === today.getTime()) {
            return `Oggi ${time}`;
        }
        if (messageDay.getTime() === yesterday.getTime()) {
            return `Ieri ${time}`;
        }
        return date.toLocaleDateString("it-IT", {
            day: "2-digit",
            month: "short",
        }) + ` ${time}`;
    }
}
