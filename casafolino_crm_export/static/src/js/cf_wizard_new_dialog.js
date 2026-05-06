/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

const OWNER_LOGIN_TO_CLASS = {
    "antonio@casafolino.com": "cf-owner-antonio",
    "josefina.lazzaro@casafolino.com": "cf-owner-josefina",
    "martina.sinopoli@casafolino.com": "cf-owner-martina",
};

function getInitials(name) {
    if (!name) return "?";
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return parts[0].substring(0, 2).toUpperCase();
}

function getShortName(name) {
    if (!name) return "";
    return name.trim().split(/\s+/)[0];
}

export class CrmLeadWizardNewDialog extends Component {
    static template = "casafolino_crm_export.CrmLeadWizardNewDialog";
    static components = { Dialog };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.dialogService = useService("dialog");

        this._searchTimeout = null;

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
            originAgentName: "",
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
            // Autocomplete
            partnerSearchQuery: "",
            partnerSearchOpen: false,
            partnerSearchResults: [],
            // Reference data
            originOptions: [
                { value: "fair", label: "Fiera" },
                { value: "inbound_mail", label: "Email" },
                { value: "agent_referral", label: "Agente" },
                { value: "web", label: "Web" },
                { value: "reorder", label: "Riordino" },
                { value: "cold_outreach", label: "Cold outreach" },
            ],
            fairTagsList: [],
            productTagsList: [],
            countriesList: [],
            usersList: [],
            // Preview
            preview: null,
            previewOwnerColor: "#ccc",
        });

        onWillStart(async () => {
            await this._loadInitialData();
        });
    }

    async _loadInitialData() {
        try {
            const [wizardId] = await this.orm.create("crm.lead.wizard.new", [{}]);
            this.state.wizardId = wizardId;

            const [fairTags, productTags, countries, users] = await Promise.all([
                this.orm.searchRead("crm.tag", [["cf_category", "=", "fair"]], ["name"], { limit: 50 }),
                this.orm.searchRead("crm.tag", [["cf_category", "=", "product"]], ["name"], { limit: 50 }),
                this.orm.searchRead("res.country", [], ["name"], { limit: 300, order: "name" }),
                this.orm.searchRead("res.users", [["share", "=", false]], ["name", "login"], { limit: 50, order: "name" }),
            ]);

            this.state.fairTagsList = fairTags;
            this.state.productTagsList = productTags;
            this.state.countriesList = countries;

            this.state.usersList = users.map((u) => ({
                id: u.id,
                name: u.name,
                short_name: getShortName(u.name),
                login: u.login,
                avatar_class: OWNER_LOGIN_TO_CLASS[u.login] || "",
                initials: getInitials(u.name),
            }));

            // Set default user
            const currentUser = this.state.usersList.find((u) => u.id === odoo.session_info.uid);
            if (currentUser) {
                this.state.userId = currentUser.id;
                this.state.userName = currentUser.name;
                this._updatePreviewOwnerColor(currentUser);
            }
        } catch (e) {
            console.error("Failed to load wizard data", e);
        }
    }

    _updatePreviewOwnerColor(user) {
        const colorMap = {
            "cf-owner-antonio": "#3F8A4F",
            "cf-owner-josefina": "#8B5CF6",
            "cf-owner-martina": "#6B4A1E",
        };
        this.state.previewOwnerColor = colorMap[user?.avatar_class] || "#ccc";
    }

    // --- Partner autocomplete ---

    onPartnerSearchInput(ev) {
        const query = ev.target.value;
        this.state.partnerSearchQuery = query;

        if (this._searchTimeout) {
            clearTimeout(this._searchTimeout);
        }

        if (!query || query.length < 2) {
            this.state.partnerSearchOpen = false;
            this.state.partnerSearchResults = [];
            return;
        }

        this._searchTimeout = setTimeout(async () => {
            try {
                const results = await this.orm.searchRead(
                    "res.partner",
                    [["is_company", "=", true], ["name", "ilike", query]],
                    ["name", "city", "country_id"],
                    { limit: 10, order: "name" }
                );
                this.state.partnerSearchResults = results.map((r) => ({
                    id: r.id,
                    name: r.name,
                    location: [r.city, r.country_id ? r.country_id[1] : ""].filter(Boolean).join(", "),
                }));
                this.state.partnerSearchOpen = true;
            } catch (e) {
                console.error("Partner search failed", e);
            }
        }, 250);
    }

    async onPartnerSelect(partnerId, partnerName) {
        this.state.partnerId = partnerId;
        this.state.partnerName = partnerName;
        this.state.partnerSearchQuery = partnerName;
        this.state.partnerSearchOpen = false;
        this.state.partnerSearchResults = [];
        this.state.isNewPartner = false;

        // Write to wizard and fetch projects count
        try {
            await this.orm.write("crm.lead.wizard.new", [this.state.wizardId], {
                partner_id: partnerId,
            });
            const [rec] = await this.orm.read("crm.lead.wizard.new", [this.state.wizardId], [
                "existing_projects_count",
            ]);
            this.state.existingProjectsCount = rec.existing_projects_count || 0;

            if (this.state.existingProjectsCount > 0) {
                this.fetchAiSuggestion();
            }
        } catch (e) {
            console.error("Failed to update partner on wizard", e);
        }

        await this.refreshPreview();
    }

    setNewPartnerMode(isNew) {
        this.state.isNewPartner = isNew;
        if (isNew) {
            this.state.partnerId = null;
            this.state.partnerName = "";
            this.state.partnerSearchQuery = "";
            this.state.partnerSearchOpen = false;
            this.state.existingProjectsCount = 0;
        }
    }

    // --- New partner inputs ---

    onNewPartnerNameInput(ev) {
        this.state.newPartnerName = ev.target.value;
    }

    onNewPartnerEmailInput(ev) {
        this.state.newPartnerEmail = ev.target.value;
    }

    onNewPartnerCountryChange(ev) {
        this.state.newPartnerCountryId = parseInt(ev.target.value) || null;
    }

    // --- Origin ---

    onOriginTypeChange(type) {
        this.state.originType = type;
    }

    onFairTagChange(ev) {
        this.state.originFairTagId = parseInt(ev.target.value) || null;
    }

    onAgentInputChange(ev) {
        this.state.originAgentName = ev.target.value;
    }

    // --- Product tags ---

    onProductTagToggle(tagId) {
        const idx = this.state.productTagIds.indexOf(tagId);
        if (idx >= 0) {
            this.state.productTagIds.splice(idx, 1);
        } else {
            this.state.productTagIds.push(tagId);
        }
    }

    // --- Priority ---

    onPriorityChange(val) {
        this.state.priority = val;
    }

    // --- Revenue ---

    async onExpectedRevenueChange(ev) {
        this.state.expectedRevenue = parseFloat(ev.target.value) || 0;
        if (this.state.wizardId) {
            try {
                await this.orm.write("crm.lead.wizard.new", [this.state.wizardId], {
                    expected_revenue: this.state.expectedRevenue,
                });
            } catch (e) {
                // silent
            }
            await this.refreshPreview();
        }
    }

    // --- Owner ---

    onUserChange(userId, userName) {
        this.state.userId = userId;
        this.state.userName = userName;
        const user = this.state.usersList.find((u) => u.id === userId);
        this._updatePreviewOwnerColor(user);
        this.refreshPreview();
    }

    onAgentUserChange(ev) {
        const val = parseInt(ev.target.value);
        if (val) {
            const u = this.state.usersList.find((x) => x.id === val);
            this.onUserChange(val, u ? u.name : "");
        }
    }

    // --- Activity ---

    onActivityTypeChange(ev) {
        this.state.nextActivityType = ev.target.value;
        this._syncActivityToWizard();
    }

    onActivitySummaryInput(ev) {
        this.state.nextActivitySummary = ev.target.value;
    }

    onActivityDateChange(ev) {
        this.state.nextActivityDate = ev.target.value;
        this._syncActivityToWizard();
    }

    async _syncActivityToWizard() {
        if (!this.state.wizardId) return;
        try {
            await this.orm.write("crm.lead.wizard.new", [this.state.wizardId], {
                next_activity_type: this.state.nextActivityType || false,
                next_activity_summary: this.state.nextActivitySummary || false,
                next_activity_date: this.state.nextActivityDate || false,
            });
        } catch (e) {
            // silent
        }
    }

    // --- Preview ---

    async refreshPreview() {
        if (!this.state.wizardId) return;
        try {
            // Sync current state to wizard before preview
            const vals = {
                partner_id: this.state.partnerId || false,
                is_new_partner: this.state.isNewPartner,
                new_partner_name: this.state.newPartnerName || false,
                origin_type: this.state.originType || false,
                product_tag_ids: [[6, 0, this.state.productTagIds]],
                expected_revenue: this.state.expectedRevenue || 0,
                priority: this.state.priority,
                user_id: this.state.userId || false,
                next_activity_type: this.state.nextActivityType || false,
                next_activity_date: this.state.nextActivityDate || false,
            };
            await this.orm.write("crm.lead.wizard.new", [this.state.wizardId], vals);

            const preview = await this.orm.call(
                "crm.lead.wizard.new",
                "get_preview_data",
                [[this.state.wizardId]]
            );
            this.state.preview = preview;
        } catch (e) {
            console.error("Preview refresh failed", e);
        }
    }

    // --- AI ---

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

    // --- Create / Cancel ---

    async onCreateLead() {
        this.state.loading = true;
        try {
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

            const result = await this.orm.call(
                "crm.lead.wizard.new", "action_create_lead", [[this.state.wizardId]]
            );

            this.props.close();

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

    // --- Handlers referenced by template (Brief #4.2 warm) ---

    onApplyAiSuggestion() {
        this.state.aiSuggestionText = "";
        this.state.aiSuggestionAction = "";
    }

    onDismissAi() {
        this.state.aiSuggestionText = "";
        this.state.aiSuggestionAction = "";
    }

    onPartnerSearchFocus() {
        if (this.state.partnerSearchQuery && this.state.partnerSearchQuery.length >= 2) {
            this.state.partnerSearchOpen = true;
        }
    }

    onSeeExistingProjects() {
        // TODO: navigate to partner's projects list
        this.state.aiSuggestionText = "";
        this.state.aiSuggestionAction = "";
    }

    onNewPartnerChange(ev) {
        // Generic handler for new partner inputs (name/email/country)
        // State is bound via t-model, this just triggers any needed side effects
    }

    onOriginFairChange(ev) {
        const val = parseInt(ev.target.value) || null;
        this.state.originFairTagId = val;
    }

    onAgentSearchInput(ev) {
        this.state.agentSearchQuery = ev.target.value;
        // Delegates to existing agent input handler if available
        if (typeof this.onAgentInputChange === "function") {
            this.onAgentInputChange(ev);
        }
    }

    onNextActivityChange(ev) {
        // Generic handler for activity inputs — state bound via t-model
        this._syncActivityToWizard();
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
