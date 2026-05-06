# CrmLeadWizardNewDialog — Contract

**Last updated:** 2026-05-06 — Brief #4.4.1
**JS:** `casafolino_crm_export/static/src/js/cf_wizard_new_dialog.js`
**Template:** `casafolino_crm_export/static/src/xml/cf_wizard_new.xml`
**CSS:** `casafolino_crm_export/static/src/css/wizard_new.css`

## Purpose

OWL Dialog for rapid CRM lead creation. Opened via:
- Client action `casafolino_crm_export.open_wizard_new_lead` (function pattern)
- `createRecord()` override in `CasafolinoCrmLeadListController` (list view)
- `createRecord()` override in `CasafolinoCrmLeadKanbanController` (kanban view)

## State (useState)

| Field | Type | Initial | Description |
|---|---|---|---|
| wizardId | int/null | null | ID of transient crm.lead.wizard.new record |
| isNewPartner | bool | false | Toggle: existing vs new partner mode |
| partnerId | int/null | null | Selected existing partner ID |
| partnerName | string | "" | Selected partner display name |
| newPartnerName | string | "" | Name for new partner creation |
| newPartnerEmail | string | "" | Email for new partner creation |
| newPartnerCountryId | int/null | null | Country for new partner |
| originType | string | "" | Selected origin: fair/inbound_mail/agent_referral/web/reorder/cold_outreach |
| originFairTagId | int/null | null | Selected fair tag ID |
| originAgentId | int/null | null | Selected agent partner ID |
| originAgentName | string | "" | Agent display name |
| productTagIds | int[] | [] | Selected product tag IDs (multi-select) |
| expectedRevenue | float | 0 | Estimated deal value |
| priority | string | "1" | Lead priority: "0"/"1"/"2" |
| userId | int/null | null | Owner user ID |
| userName | string | "" | Owner display name |
| nextActivityType | string | "" | Activity type: email/call/meeting/todo |
| nextActivitySummary | string | "" | Activity summary text |
| nextActivityDate | string | "" | Activity deadline (date string) |
| aiSuggestionText | string | "" | AI suggestion text from Groq backend |
| aiSuggestionAction | string | "" | AI action: continue/see_existing/duplicate |
| existingProjectsCount | int | 0 | Count of open projects for selected partner |
| loading | bool | false | Global loading state |
| saving | bool | false | Create in progress |
| aiLoading | bool | false | AI suggestion loading |
| partnerSearchQuery | string | "" | Autocomplete search text |
| partnerSearchOpen | bool | false | Autocomplete dropdown visible |
| partnerSearchResults | array | [] | Autocomplete results [{id, name, location}] |
| originOptions | array | [...] | Static list of 6 origin options |
| fairTagsList | array | [] | Preloaded fair tags [{id, name}] |
| productTagsList | array | [] | Preloaded product tags [{id, name}] |
| countriesList | array | [] | Preloaded countries [{id, name}] |
| usersList | array | [] | Preloaded users [{id, name, short_name, login, avatar_class, initials}] |
| preview | object/null | null | Live preview data from get_preview_data() |
| previewOwnerColor | string | "#ccc" | Owner color hex for preview accent |

## Props

| Prop | Type | Required | Description |
|---|---|---|---|
| close | Function | yes | Callback to close the dialog |
| * | any | no | Accepts all props (static props = ["*"]) |

## Service dependencies

| Service | Variable | Usage |
|---|---|---|
| orm | this.orm | CRUD on crm.lead.wizard.new, searchRead for autocomplete |
| notification | this.notification | Toast messages on error |
| action | this.action | doAction for navigation (see existing projects, open created lead) |
| dialog | this.dialogService | (available but not used directly — dialog opened by caller) |

## Public methods

| Method | Args | Returns | Description | Status |
|---|---|---|---|---|
| _loadInitialData | — | Promise | Creates wizard record, preloads reference data | OK |
| onPartnerSearchInput | ev | void | Debounced partner autocomplete (250ms) | OK |
| onPartnerSelect | partnerId, partnerName | Promise | Sets partner, fetches projects, triggers AI | OK |
| setNewPartnerMode | isNew:bool | void | Toggles existing/new partner mode | OK |
| onNewPartnerChange | — | void | No-op, t-model handles state | OK |
| onOriginTypeChange | type:string | void | Sets origin type | OK |
| onOriginFairChange | ev | void | Parses fair tag ID from select | OK |
| onAgentSearchInput | ev | void | Updates agent search query | OK |
| onProductTagToggle | tagId:int | void | Toggles product tag in/out of selection | OK |
| onPriorityChange | val:string | void | Sets priority "0"/"1"/"2" | OK |
| onExpectedRevenueChange | ev | Promise | Updates revenue, syncs to wizard | OK |
| onUserChange | userId, userName | void | Sets owner, updates preview color | OK |
| onAgentUserChange | ev | void | Sets agent from dropdown | OK |
| onApplyAiSuggestion | — | void | Acknowledges AI suggestion, clears banner | OK |
| onDismissAi | — | void | Dismisses AI suggestion banner | OK |
| onPartnerSearchFocus | — | void | Reopens autocomplete if query exists | OK |
| onSeeExistingProjects | — | Promise | Navigates to partner's projects list | OK |
| onNextActivityChange | — | void | Syncs activity fields to wizard record | OK |
| refreshPreview | — | Promise | Calls get_preview_data, updates state.preview | OK |
| fetchAiSuggestion | — | Promise | Calls action_get_ai_suggestion on backend | OK |
| onCreateLead | — | Promise | Writes all fields, calls action_create_lead, closes dialog | OK |
| onCancel | — | void | Closes dialog without saving | OK |

## Template handler mapping (cf_wizard_new.xml)

| Template binding | Element | Class method |
|---|---|---|
| t-on-click | AI "Applica" button | onApplyAiSuggestion |
| t-on-click | AI "Chiudi" button | onDismissAi |
| t-on-click | "Esistente" pill | setNewPartnerMode(false) |
| t-on-click | "+ Nuovo" pill | setNewPartnerMode(true) |
| t-on-input | partner search input | onPartnerSearchInput |
| t-on-focus | partner search input | onPartnerSearchFocus |
| t-on-click | autocomplete item | onPartnerSelect(p.id, p.name) |
| t-on-click | "Vedi esistenti" link | onSeeExistingProjects |
| t-on-input | new partner name input | onNewPartnerChange |
| t-on-input | new partner email input | onNewPartnerChange |
| t-on-change | new partner country select | onNewPartnerChange |
| t-on-click | origin pill | onOriginTypeChange(opt.value) |
| t-on-change | fair tag select | onOriginFairChange |
| t-on-input | agent search input | onAgentSearchInput |
| t-on-click | product tag chip | onProductTagToggle(tag.id) |
| t-on-change | expected revenue input | onExpectedRevenueChange |
| t-on-click | priority pill Bassa | onPriorityChange('0') |
| t-on-click | priority pill Media | onPriorityChange('1') |
| t-on-click | priority pill Alta | onPriorityChange('2') |
| t-on-click | owner avatar option | onUserChange(u.id, u.name) |
| t-on-change | agent user select | onAgentUserChange |
| t-on-change | activity type select | onNextActivityChange |
| t-on-input | activity summary input | onNextActivityChange |
| t-on-change | activity date input | onNextActivityChange |
| t-on-click | "Annulla" button | onCancel |
| t-on-click | "Crea lead" button | onCreateLead |

## Events emitted

None.

## Maintenance

**Golden rule:** no one modifies the template XML without first reading this file
AND confirming the modification is consistent with the class. No one modifies
the class without updating this file in the same commit.

When this file updates:
- Add/modify a public method → update "Public methods" section
- Add/modify a template binding → update "Template handler mapping" section
- Add/modify a state field → update "State" section
- Add/modify a service → update "Service dependencies" section
