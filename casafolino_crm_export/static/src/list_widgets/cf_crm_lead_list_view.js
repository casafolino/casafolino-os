/** @odoo-module **/
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, onMounted, useState } from "@odoo/owl";
import { CrmLeadWizardNewDialog } from "../js/cf_wizard_new_dialog";

export class CasafolinoCrmLeadListController extends ListController {
    static template = "casafolino_crm_export.CrmLeadListView";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.metricsState = useState({
            open_leads: 0,
            pipeline_value: 0,
            conversion_90d: 0,
            open_issues: 0,
            loading: true,
        });
        onWillStart(() => this.loadMetrics());
        onMounted(() => this.loadMetrics());
    }

    async loadMetrics() {
        try {
            const metrics = await this.orm.call(
                "casafolino.crm.lead.dashboard",
                "get_metrics",
                [[]]
            );
            Object.assign(this.metricsState, metrics, { loading: false });
        } catch (e) {
            console.error("Failed to load CRM dashboard metrics", e);
            this.metricsState.loading = false;
        }
    }

    async createRecord() {
        this.dialogService.add(CrmLeadWizardNewDialog, {
            close: () => {},
        });
    }

    formatPipelineValue(value) {
        if (!value) return "\u20ac0";
        if (value >= 1000000) return `\u20ac${(value / 1000000).toFixed(1)}M`;
        if (value >= 1000) return `\u20ac${(value / 1000).toFixed(0)}k`;
        return `\u20ac${value.toFixed(0)}`;
    }
}

registry.category("views").add("casafolino_crm_lead_list", {
    ...listView,
    Controller: CasafolinoCrmLeadListController,
});
