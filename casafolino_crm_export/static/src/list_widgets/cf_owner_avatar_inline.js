/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class CfOwnerAvatarInline extends Component {
    static template = "casafolino_crm_export.CfOwnerAvatarInline";
    static props = { ...standardFieldProps };

    get avatarClass() {
        return this.props.record.data.casafolino_owner_avatar_class || "cf-owner-other";
    }
    get initials() {
        return this.props.record.data.casafolino_owner_avatar_initials || "\u2014";
    }
    get tooltip() {
        const user = this.props.record.data.user_id;
        return user ? user[1] : "";
    }
}

registry.category("fields").add("cf_owner_avatar_inline", {
    component: CfOwnerAvatarInline,
    supportedTypes: ["many2one"],
});
