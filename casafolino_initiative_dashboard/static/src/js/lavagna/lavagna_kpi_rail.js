/** @odoo-module **/
import { Component, useEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

const SHORT_NAMES = {
    'Task in Scouting': 'Scouting',
    'In Campionatura': 'Camp.',
    'Appuntamenti': 'Appunt.',
    'Incontri': 'Incontri',
    'Lead CRM': 'Lead',
    'Spedizioni Campioni': 'Spediz.',
    'Mail Nuove': 'Mail',
};

// KPI names that map to counter actions (click opens modal instead of filtering)
const ACTION_KPI_MAP = {
    'In Campionatura': 'camp',
    'Appuntamenti': 'appunt',
    'Lead CRM': 'lead',
    'Mail Nuove': 'mail',
};

export class LavagnaKpiRail extends Component {
    static template = "casafolino_initiative_dashboard.LavagnaKpiRail";
    static props = ["*"];

    setup() {
        this.env = useEnv();
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");
    }

    get counters() {
        return this.props.counters || {};
    }

    get initiative() {
        return this.env.lavagnaState.data ? this.env.lavagnaState.data.initiative : {};
    }

    getDisplayName(kpi) {
        return SHORT_NAMES[kpi.name] || kpi.name;
    }

    isActive(kpi) {
        const filter = this.env.lavagnaState.kpiFilter;
        return filter && filter.id === kpi.id;
    }

    isActionable(kpi) {
        return kpi.name in ACTION_KPI_MAP;
    }

    getCounterValue(kpi) {
        // For actionable KPIs, show counter from backend counters if available
        const action = ACTION_KPI_MAP[kpi.name];
        if (action) {
            const c = this.counters;
            if (action === 'camp') return (c.samples || {}).total || kpi.value;
            if (action === 'appunt') return (c.appointments || {}).total || kpi.value;
            if (action === 'lead') return (c.leads || {}).total || kpi.value;
            if (action === 'mail') return (c.mail || {}).total || kpi.value;
        }
        return kpi.value;
    }

    onKpiClick(kpi) {
        const action = ACTION_KPI_MAP[kpi.name];
        if (action) {
            this._doCounterAction(action);
        } else {
            this.env.actions.filterByKpi(kpi);
        }
    }

    _doCounterAction(action) {
        const partnerId = this.initiative.partner_id || false;
        const initId = this.env.initiativeId;
        const initName = this.initiative.name || '';

        switch (action) {
            case 'camp':
                this._openCamp(initId, partnerId);
                break;
            case 'appunt':
                this._openAppunt(initId, partnerId, initName);
                break;
            case 'lead':
                this._openLead(initId);
                break;
            case 'mail':
                this._openMail(initName);
                break;
        }
    }

    _openCamp(initId, partnerId) {
        const c = this.counters.samples || {};
        if (c.total > 0) {
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Campionature',
                res_model: 'cf.sample.request',
                views: [[false, 'list'], [false, 'form']],
                domain: [['initiative_id', '=', initId]],
                target: 'current',
            });
        } else {
            const ctx = { default_initiative_id: initId };
            if (partnerId) ctx.default_partner_id = partnerId;
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'cf.sample.request',
                views: [[false, 'form']],
                target: 'new',
                context: ctx,
            });
        }
    }

    _openAppunt(initId, partnerId, initName) {
        const c = this.counters.appointments || {};
        if (c.total > 0) {
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Appuntamenti',
                res_model: 'calendar.event',
                views: [[false, 'list'], [false, 'form']],
                domain: [['cf_initiative_ids', 'in', [initId]]],
                target: 'current',
            });
        } else {
            const ctx = {
                default_cf_initiative_ids: [[6, 0, [initId]]],
                default_name: 'Iniziativa: ' + initName,
            };
            if (partnerId) ctx.default_partner_ids = [partnerId];
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'calendar.event',
                views: [[false, 'form']],
                target: 'new',
                context: ctx,
            });
        }
    }

    _openLead(initId) {
        const c = this.counters.leads || {};
        if (c.total > 0) {
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Lead',
                res_model: 'crm.lead',
                views: [[false, 'list'], [false, 'form']],
                domain: [['cf_initiative_id', '=', initId]],
                target: 'current',
            });
        } else {
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'crm.lead',
                views: [[false, 'form']],
                target: 'new',
                context: { default_cf_initiative_id: initId },
            });
        }
    }

    async _openMail(initName) {
        const partnerId = this.initiative.partner_id || false;
        let partnerEmail = '';
        if (partnerId) {
            try {
                const [partner] = await this.orm.read('res.partner', [partnerId], ['email']);
                partnerEmail = partner.email || '';
            } catch {}
        }

        const { ComposeWizardDialog } = await import(
            "@casafolino_mail/js/mail_v3/compose_wizard_dialog"
        );
        this.dialogService.add(ComposeWizardDialog, {
            partnerEmail: partnerEmail,
            defaultSubject: 'Re: ' + initName,
            onSent: () => {
                this.notificationService.add('Mail inviata', { type: 'success' });
                this.env.actions.refreshData();
            },
        });
    }
}
