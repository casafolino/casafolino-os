/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

class CfWorkspaceMain extends Component {
    static template = "casafolino_workspace.CfWorkspaceMain";
    static props = ["*"];

    setup() {
        this.state = useState({
            searchQuery: "",
        });
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
    }

    onSearchKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
        }
    }
}

registry.category("actions").add("cf_workspace_main", CfWorkspaceMain);
