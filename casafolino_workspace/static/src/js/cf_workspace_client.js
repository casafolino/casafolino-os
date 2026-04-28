/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { WorkspaceHero } from "./components/workspace_hero";
import { WorkspaceKpis } from "./components/workspace_kpis";
import { WorkspaceMacro } from "./components/workspace_macro";
import { WorkspaceWork } from "./components/workspace_work";
import { WorkspaceDetail } from "./components/workspace_detail";
import { WorkspaceFeed } from "./components/workspace_feed";
import { WorkspaceLead } from "./lead/workspace_lead";

class CfWorkspaceMain extends Component {
    static template = "casafolino_workspace.CfWorkspaceMain";
    static props = ["*"];
    static components = {
        WorkspaceHero,
        WorkspaceKpis,
        WorkspaceMacro,
        WorkspaceWork,
        WorkspaceDetail,
        WorkspaceFeed,
        WorkspaceLead,
    };

    setup() {
        this.state = useState({
            page: "home",
            loading: true,
            error: null,
            data: null,
            searchQuery: "",
            workView: "oggi",
            selectedItem: null,
        });
        onWillStart(async () => {
            await this._loadData();
        });
    }

    async _loadData() {
        try {
            const result = await rpc("/workspace/dashboard/data", {});
            this.state.data = result;
            this.state.loading = false;
        } catch (e) {
            this.state.error = e.message || "Errore caricamento dashboard";
            this.state.loading = false;
        }
    }

    async onRefresh() {
        this.state.loading = true;
        this.state.error = null;
        if (this.state.page === "home") {
            await this._loadData();
        }
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
    }

    onSearchKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
        }
    }

    onWorkViewChange(view) {
        this.state.workView = view;
    }

    onSelectItem(item) {
        // If macro tile with link, navigate
        if (item && item.id === "pipeline") {
            this.state.page = "lead";
            return;
        }
        this.state.selectedItem = item;
    }

    onCloseDetail() {
        this.state.selectedItem = null;
    }

    onNavigate(page) {
        this.state.page = page;
        this.state.selectedItem = null;
    }

    onGoHome() {
        this.state.page = "home";
    }
}

registry.category("actions").add("cf_workspace_main", CfWorkspaceMain);
