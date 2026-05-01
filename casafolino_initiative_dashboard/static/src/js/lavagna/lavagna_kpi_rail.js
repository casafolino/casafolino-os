/** @odoo-module **/
import { Component, useEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const SHORT_NAMES = {
    'Task in Scouting': 'Scouting',
    'In Campionatura': 'Camp.',
    'Appuntamenti': 'Appunt.',
    'Incontri': 'Incontri',
    'Lead CRM': 'Lead',
    'Spedizioni Campioni': 'Spediz.',
    'Mail Nuove': 'Mail',
};

export class LavagnaKpiRail extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaKpiRail";
    static props = ["*"];

    setup() {
        this.env = useEnv();
        this.actionService = useService("action");
        this.orm = useService("orm");
    }

    onKpiClick(kpi) {
        this.env.actions.filterByKpi(kpi);
    }

    isActive(kpi) {
        const filter = this.env.lavagnaState.kpiFilter;
        return filter && filter.id === kpi.id;
    }

    getDisplayName(kpi) {
        return SHORT_NAMES[kpi.name] || kpi.name;
    }

    // Counter actions
    get counters() {
        return this.props.counters || {};
    }

    get initiative() {
        return this.env.lavagnaState.data ? this.env.lavagnaState.data.initiative : {};
    }

    onCampClick() {
        const c = this.counters.samples || {};
        if (c.total > 0) {
            // Open list of sample requests for this initiative
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Campionature',
                res_model: 'cf.sample.request',
                view_mode: 'list,form',
                domain: [['initiative_id', '=', this.env.initiativeId]],
                target: 'current',
            });
        } else {
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'cf.sample.request',
                view_mode: 'form',
                target: 'new',
                context: {
                    default_initiative_id: this.env.initiativeId,
                    default_partner_id: this.initiative.partner_id || false,
                },
            });
        }
    }

    onAppuntClick() {
        const c = this.counters.appointments || {};
        if (c.total > 0) {
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Appuntamenti',
                res_model: 'calendar.event',
                view_mode: 'list,form',
                domain: [['cf_initiative_ids', 'in', [this.env.initiativeId]]],
                target: 'current',
            });
        } else {
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'calendar.event',
                view_mode: 'form',
                target: 'new',
                context: {
                    default_cf_initiative_ids: [[6, 0, [this.env.initiativeId]]],
                    default_name: 'Iniziativa: ' + (this.initiative.name || ''),
                },
            });
        }
    }

    async onLeadClick() {
        const c = this.counters.leads || {};
        if (c.total > 0) {
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Lead',
                res_model: 'crm.lead',
                view_mode: 'list,form',
                domain: [['cf_initiative_id', '=', this.env.initiativeId]],
                target: 'current',
            });
        } else {
            // Quick create lead via ORM
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'crm.lead',
                view_mode: 'form',
                target: 'new',
                context: {
                    default_cf_initiative_id: this.env.initiativeId,
                    default_partner_name: this.initiative.partner_name || '',
                },
            });
        }
    }

    onMailClick() {
        // Open mail compose as placeholder
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'mail.compose.message',
            view_mode: 'form',
            target: 'new',
            context: {
                default_subject: 'Re: ' + (this.initiative.name || ''),
            },
        });
    }
}
