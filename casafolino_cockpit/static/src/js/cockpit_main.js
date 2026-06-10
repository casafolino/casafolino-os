/** @odoo-module **/
import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { CockpitRegia } from "./cockpit_regia";
import { CockpitDossier } from "./cockpit_dossier";

class CockpitMain extends Component {
    static template = "casafolino_cockpit.CockpitMain";
    static components = { CockpitRegia, CockpitDossier };
    static props = ["*"];

    setup() {
        this.state = useState({
            screen: "regia",
            selectedPartnerId: null,
            selectedInitiativeId: null,
            dailyLineEnabled: false,
        });
        onMounted(() => this._loadConfig());
    }

    async _loadConfig() {
        try {
            const res = await rpc("/web/dataset/call_kw", {
                model: "ir.config_parameter",
                method: "get_param",
                args: ["casafolino_cockpit.daily_line_enabled", "false"],
                kwargs: {},
            });
            this.state.dailyLineEnabled = (res === "true" || res === "1");
        } catch (_e) {}
    }

    goToDossier(partnerId, initiativeId) {
        this.state.selectedPartnerId = partnerId;
        this.state.selectedInitiativeId = initiativeId;
        this.state.screen = "dossier";
    }

    goToRegia() {
        this.state.screen = "regia";
        this.state.selectedPartnerId = null;
        this.state.selectedInitiativeId = null;
    }
}

registry.category("actions").add("casafolino_cockpit.CockpitMain", CockpitMain);
export { CockpitMain };
