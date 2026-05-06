/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class CrmLeadWizardNewDialog extends Component {
    static template = "casafolino_crm_export.CrmLeadWizardNewDialog";
    static components = { Dialog };
    static props = { close: Function };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.dialogService = useService("dialog");

        this.state = useState({
            wizardId: null,
            isNewPartner: false,
            partnerId: null,
            partnerName: "",
            newPartnerName: "",
            newPartnerEmail: "",
            newPartnerCountryId: null,
            originType: "",
            originFairTagId: null,
            originAgentId: null,
            productTagIds: [],
            expectedRevenue: 0,
            priority: "1",
            userId: null,
            userName: "",
            nextActivityType: "",
            nextActivitySummary: "",
            nextActivityDate: "",
            aiSuggestionText: "",
            aiSuggestionAction: "",
            existingProjectsCount: 0,
            loading: false,
            aiLoading: false,
            partners: [],
            fairTags: [],
            agents: [],
            productTags: [],
            users: [],
            countries: [],
        });

        onWillStart(async () => {
            await this._loadInitialData();
        });
    }

    async _loadInitialData() {
        try {
            // Create wizard record
            const [wizardId] = await this.orm.create("crm.lead.wizard.new", [{}]);
            this.state.wizardId = wizardId;

            // Load reference data in parallel
            const [partners, fairTags, productTags, agents, users, countries] = await Promise.all([
                this.orm.searchRead("res.partner", [["is_company", "=", true]], ["name"], { limit: 200, order: "name" }),
                this.orm.searchRead("crm.tag", [["cf_category", "=", "fair"]], ["name"], { limit: 50 }),
                this.orm.searchRead("crm.tag", [["cf_category", "=", "product"]], ["name"], { limit: 50 }),
                this.orm.searchRead("res.partner", [["cf_partner_role", "=", "agent"]], ["name"], { limit: 50 }),
                this.orm.searchRead("res.users", [["share", "=", false]], ["name"], { limit: 50, order: "name" }),
                this.orm.searchRead("res.country", [], ["name"], { limit: 300, order: "name" }),
            ]);

            this.state.partners = partners;
            this.state.fairTags = fairTags;
            this.state.productTags = productTags;
            this.state.agents = agents;
            this.state.users = users;
            this.state.countries = countries;

            // Set default user
            const currentUser = users.find((u) => u.id === odoo.session_info.uid);
            if (currentUser) {
                this.state.userId = currentUser.id;
                this.state.userName = currentUser.name;
            }
        } catch (e) {
            console.error("Failed to load wizard data", e);
        }
    }

    onPartnerSelected(ev) {
        const val = parseInt(ev.target.value);
        if (val) {
            this.state.partnerId = val;
            const p = this.state.partners.find((x) => x.id === val);
            this.state.partnerName = p ? p.name : "";
            this.state.isNewPartner = false;
            this.fetchAiSuggestion();
        } else {
            this.state.partnerId = null;
            this.state.partnerName = "";
        }
    }

    onToggleNewPartner() {
        this.state.isNewPartner = !this.state.isNewPartner;
        if (this.state.isNewPartner) {
            this.state.partnerId = null;
            this.state.partnerName = "";
        }
    }

    onOriginChange(type) {
        this.state.originType = type;
    }

    onProductTagToggle(tagId) {
        const idx = this.state.productTagIds.indexOf(tagId);
        if (idx >= 0) {
            this.state.productTagIds.splice(idx, 1);
        } else {
            this.state.productTagIds.push(tagId);
        }
    }

    onPriorityChange(val) {
        this.state.priority = val;
    }

    onUserChange(ev) {
        const val = parseInt(ev.target.value);
        if (val) {
            this.state.userId = val;
            const u = this.state.users.find((x) => x.id === val);
            this.state.userName = u ? u.name : "";
        }
    }

    async fetchAiSuggestion() {
        if (!this.state.wizardId || !this.state.partnerId) return;
        this.state.aiLoading = true;
        try {
            await this.orm.write("crm.lead.wizard.new", [this.state.wizardId], {
                partner_id: this.state.partnerId,
                origin_type: this.state.originType || false,
            });
            await this.orm.call("crm.lead.wizard.new", "action_get_ai_suggestion", [[this.state.wizardId]]);
            const [rec] = await this.orm.read("crm.lead.wizard.new", [this.state.wizardId], [
                "ai_suggestion_text", "ai_suggestion_action", "existing_projects_count",
            ]);
            this.state.aiSuggestionText = rec.ai_suggestion_text || "";
            this.state.aiSuggestionAction = rec.ai_suggestion_action || "";
            this.state.existingProjectsCount = rec.existing_projects_count || 0;
        } catch (e) {
            console.error("AI suggestion failed", e);
        }
        this.state.aiLoading = false;
    }

    async onCreateLead() {
        this.state.loading = true;
        try {
            // Write all fields to wizard record
            const vals = {
                partner_id: this.state.partnerId || false,
                is_new_partner: this.state.isNewPartner,
                new_partner_name: this.state.newPartnerName || false,
                new_partner_email: this.state.newPartnerEmail || false,
                new_partner_country_id: this.state.newPartnerCountryId || false,
                origin_type: this.state.originType || false,
                origin_fair_tag_id: this.state.originFairTagId || false,
                origin_agent_id: this.state.originAgentId || false,
                product_tag_ids: [[6, 0, this.state.productTagIds]],
                expected_revenue: this.state.expectedRevenue || 0,
                priority: this.state.priority,
                user_id: this.state.userId || false,
                next_activity_type: this.state.nextActivityType || false,
                next_activity_summary: this.state.nextActivitySummary || false,
                next_activity_date: this.state.nextActivityDate || false,
            };
            await this.orm.write("crm.lead.wizard.new", [this.state.wizardId], vals);

            // Call create action
            const result = await this.orm.call(
                "crm.lead.wizard.new", "action_create_lead", [[this.state.wizardId]]
            );

            this.props.close();

            // Navigate to the new lead
            if (result && result.res_id) {
                this.action.doAction(result);
            }
        } catch (e) {
            this.notification.add(e.message || "Errore nella creazione del lead", { type: "danger" });
        }
        this.state.loading = false;
    }

    onCancel() {
        this.props.close();
    }
}

// Register as client action (function pattern, not Component)
async function openWizardNewLead(env, action) {
    return new Promise((resolve) => {
        env.services.dialog.add(CrmLeadWizardNewDialog, {
            close: () => resolve(),
        });
    });
}

registry.category("actions").add("casafolino_crm_export.open_wizard_new_lead", openWizardNewLead);
