/** @odoo-module **/
import { Component } from "@odoo/owl";

export class WorkspaceFeed extends Component {
    static template = "casafolino_workspace.WorkspaceFeed";
    static props = ["*"];

    getRelativeTime(isoDate) {
        if (!isoDate) return "";
        const now = luxon.DateTime.now();
        const dt = luxon.DateTime.fromISO(isoDate);
        const diff = now.diff(dt, ["days", "hours", "minutes"]);
        if (diff.days >= 1) {
            const d = Math.floor(diff.days);
            return d === 1 ? "ieri" : d + " gg fa";
        }
        if (diff.hours >= 1) {
            return Math.floor(diff.hours) + " h fa";
        }
        const m = Math.max(1, Math.floor(diff.minutes));
        return m + " min fa";
    }
}
