/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class CfCardTitle extends Component {
    static template = "casafolino_crm_export.CfCardTitle";
    static props = { ...standardFieldProps };

    get title() {
        return this.props.record.data.casafolino_card_title || "Senza titolo";
    }
}

registry.category("fields").add("cf_card_title", {
    component: CfCardTitle,
    supportedTypes: ["char"],
});
