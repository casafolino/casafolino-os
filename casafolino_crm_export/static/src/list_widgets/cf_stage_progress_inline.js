/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class CfStageProgressInline extends Component {
    static template = "casafolino_crm_export.CfStageProgressInline";
    static props = { ...standardFieldProps };

    get segments() {
        const stageId = this.props.record.data.stage_id;
        const position = this.props.record.data.casafolino_stage_position || 0;
        const ownerClass = this.props.record.data.casafolino_owner_avatar_class || "cf-owner-other";
        const segs = [];
        for (let i = 1; i <= 9; i++) {
            segs.push({ index: i, filled: i <= position });
        }
        return segs;
    }
    get stageLabel() {
        return this.props.record.data.casafolino_stage_label || "";
    }
    get ownerColorVar() {
        const cls = this.props.record.data.casafolino_owner_avatar_class || "";
        const map = {
            "cf-owner-antonio": "#3F8A4F",
            "cf-owner-josefina": "#8B5CF6",
            "cf-owner-martina": "#6B4A1E",
            "cf-owner-other": "#888780",
        };
        return map[cls] || "#888780";
    }
}

registry.category("fields").add("cf_stage_progress_inline", {
    component: CfStageProgressInline,
    supportedTypes: ["many2one"],
});
