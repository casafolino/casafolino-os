/** @odoo-module **/
import { Component, useState, onMounted } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class CockpitRegia extends Component {
    static template = "casafolino_cockpit.CockpitRegia";
    static props = ["*"];

    setup() {
        this.state = useState({
            projects: [],
            loading: true,
            filter: "all",
        });
        onMounted(() => this._loadProjects());
    }

    async _loadProjects() {
        this.state.loading = true;
        try {
            const data = await rpc("/web/dataset/call_kw", {
                model: "cf.initiative",
                method: "search_read",
                args: [[["state", "in", ["in_progress", "active"]]]],
                kwargs: {
                    fields: [
                        "id", "name", "partner_id", "template_id",
                        "current_stage_id", "traffic_light", "progress",
                        "baton_user_id", "date_deadline", "write_date",
                    ],
                    order: "write_date desc",
                    limit: 200,
                },
            });
            const enriched = await this._enrichWithStageDays(data);
            this.state.projects = this._sortProjects(enriched);
        } catch (e) {
            console.error("CockpitRegia load error:", e);
        }
        this.state.loading = false;
    }

    async _enrichWithStageDays(projects) {
        const stageIds = [...new Set(projects.map(p => p.current_stage_id?.[0]).filter(Boolean))];
        if (!stageIds.length) return projects;
        try {
            const stages = await rpc("/web/dataset/call_kw", {
                model: "cf.initiative.stage",
                method: "search_read",
                args: [[["id", "in", stageIds]]],
                kwargs: { fields: ["id", "date_start", "user_id", "state"] },
            });
            const sm = Object.fromEntries(stages.map(s => [s.id, s]));
            const now = new Date();
            return projects.map(p => {
                const st = sm[p.current_stage_id?.[0]];
                const days = st?.date_start
                    ? Math.floor((now - new Date(st.date_start)) / 86400000)
                    : null;
                return { ...p, _stageDays: days, _stageUser: st?.user_id || null };
            });
        } catch (_e) { return projects; }
    }

    _sortProjects(projects) {
        const order = { red: 0, orange: 1, yellow: 2, green: 3 };
        return [...projects].sort((a, b) => {
            const ao = order[a.traffic_light] ?? 4;
            const bo = order[b.traffic_light] ?? 4;
            if (ao !== bo) return ao - bo;
            if (ao <= 1) return (b._stageDays || 0) - (a._stageDays || 0);
            return 0;
        });
    }

    get filteredProjects() {
        const now = new Date();
        if (this.state.filter === "stuck") {
            return this.state.projects.filter(p =>
                ["red","orange","yellow"].includes(p.traffic_light)
            );
        }
        if (this.state.filter === "deadline") {
            return this.state.projects.filter(p =>
                p.date_deadline && (new Date(p.date_deadline) - now) / 86400000 <= 7
            );
        }
        return this.state.projects;
    }

    get counters() {
        const all = this.state.projects;
        const now = new Date();
        return {
            all: all.length,
            stuck: all.filter(p => ["red","orange","yellow"].includes(p.traffic_light)).length,
            deadline: all.filter(p =>
                p.date_deadline && (new Date(p.date_deadline) - now) / 86400000 <= 7
            ).length,
        };
    }

    setFilter(filter) { this.state.filter = filter; }
    setFilterAll() { this.state.filter = "all"; }
    setFilterStuck() { this.state.filter = "stuck"; }
    setFilterDeadline() { this.state.filter = "deadline"; }
    refresh() { this._loadProjects(); }

    onProjectClick(project) {
        const pid = project.partner_id?.[0];
        if (pid && this.props.onSelectProject) {
            this.props.onSelectProject(pid, project.id);
        }
    }

    getTrafficClass(tl) {
        return { red: "ck-tl--red", orange: "ck-tl--orange", yellow: "ck-tl--yellow", green: "ck-tl--green" }[tl] || "ck-tl--neutral";
    }

    getInitials(name) {
        if (!name) return "?";
        return name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
    }

    formatStageDays(days) {
        if (days === null || days === undefined) return "";
        return days < 1 ? "oggi" : `fermo da ${days} gg`;
    }
}
