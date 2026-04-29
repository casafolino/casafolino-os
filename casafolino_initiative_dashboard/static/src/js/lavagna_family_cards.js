/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class LavagnaFamilyCards extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaFamilyCards";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ families: [], loading: true });

        onWillStart(async () => {
            const families = await this.orm.searchRead(
                "cf.initiative.family",
                [["active", "=", true]],
                ["id", "name", "code", "description", "icon"],
                { order: "sequence, id" }
            );
            this.state.families = families;
            this.state.loading = false;
        });
    }

    selectFamily(familyId) {
        this.props.record.update({ [this.props.name]: [familyId, ""] });
    }

    isSelected(familyId) {
        const value = this.props.record.data[this.props.name];
        return value && value[0] === familyId;
    }

    getFamilyIcon(family) {
        if (family.icon) return family.icon;
        // Fallback icons per family code
        const icons = {
            'OC': 'fa-handshake-o',
            'EV': 'fa-calendar-check-o',
            'CE': 'fa-flask',
        };
        return icons[family.code] || 'fa-folder-o';
    }
}

registry.category("fields").add("lavagna_family_cards", {
    component: LavagnaFamilyCards,
    supportedTypes: ["many2one"],
});
