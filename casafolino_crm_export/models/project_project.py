import logging
from datetime import datetime

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

OWNER_LOGIN_COLOR = {
    'antonio@casafolino.com': 'green',
    'josefina.lazzaro@casafolino.com': 'purple',
    'martina.sinopoli@casafolino.com': 'gray',
}


class ProjectProject(models.Model):
    _inherit = 'project.project'

    cf_managed_by_id = fields.Many2one(
        comodel_name='res.partner',
        domain="[('cf_partner_role', '=', 'agent')]",
        string='Agente',
        index=True,
        tracking=True,
    )

    cf_status_dossier = fields.Selection(
        selection=[
            ('exploration', 'Esplorativo'),
            ('active', 'Attivo'),
            ('on_hold', 'In pausa'),
            ('won', 'Vinto / ricorrente'),
            ('closed', 'Chiuso'),
        ],
        string='Status dossier',
        default='exploration',
        index=True,
        tracking=True,
    )

    cf_dossier_priority = fields.Selection(
        selection=[
            ('low', 'Bassa'),
            ('medium', 'Media'),
            ('high', 'Alta'),
        ],
        string='Priorità dossier',
        default='medium',
    )

    cf_dossier_value_estimate = fields.Float(
        string='Valore stimato dossier',
    )

    cf_open_issues_count = fields.Integer(
        compute='_compute_cf_dossier_stats',
        string='Reclami aperti',
    )

    cf_last_activity_date = fields.Datetime(
        compute='_compute_cf_dossier_stats',
        string='Ultima attività',
    )

    cf_lead_count = fields.Integer(
        compute='_compute_cf_dossier_stats',
        string='Lead/quotazioni',
    )

    # Reverse relation from crm.lead.cf_project_id
    cf_lead_ids = fields.One2many(
        'crm.lead', 'cf_project_id',
        string='Lead CRM collegati',
    )

    @api.depends('partner_id')
    def _compute_cf_dossier_stats(self):
        if not self.ids:
            for p in self:
                p.cf_open_issues_count = 0
                p.cf_last_activity_date = False
                p.cf_lead_count = 0
            return

        # Lead counts
        self.env.cr.execute("""
            SELECT cf_project_id, COUNT(*)
            FROM crm_lead
            WHERE cf_project_id IN %s AND active = true
            GROUP BY cf_project_id
        """, (tuple(self.ids),))
        lead_counts = dict(self.env.cr.fetchall())

        # Last activity
        self.env.cr.execute("""
            SELECT cf_project_id, MAX(write_date)
            FROM crm_lead
            WHERE cf_project_id IN %s AND active = true
            GROUP BY cf_project_id
        """, (tuple(self.ids),))
        last_dates = dict(self.env.cr.fetchall())

        # Open issues
        self.env.cr.execute("""
            SELECT l.cf_project_id, COUNT(*)
            FROM crm_lead l
            JOIN crm_tag_rel ctr ON ctr.lead_id = l.id
            JOIN crm_tag t ON t.id = ctr.tag_id
            WHERE l.cf_project_id IN %s
              AND l.active = true
              AND t.cf_category = 'issue'
            GROUP BY l.cf_project_id
        """, (tuple(self.ids),))
        issue_counts = dict(self.env.cr.fetchall())

        for project in self:
            project.cf_lead_count = lead_counts.get(project.id, 0)
            project.cf_last_activity_date = last_dates.get(project.id) or project.write_date
            project.cf_open_issues_count = issue_counts.get(project.id, 0)

    # ------------------------------------------------------------------
    # Dashboard 360° aggregator — Brief #5.0
    # ------------------------------------------------------------------

    def cf_get_dashboard_data(self):
        """Single aggregator for the 360° OWL dashboard.
        Returns a JSON-serializable dict with all data the frontend needs."""
        self.ensure_one()

        # Find main lead (highest expected_revenue)
        leads = self.env['crm.lead'].search(
            [('cf_project_id', '=', self.id), ('active', '=', True)],
            order='expected_revenue desc',
            limit=10,
        )
        lead = leads[:1] if leads else self.env['crm.lead']
        partner = lead.partner_id if lead else self.partner_id

        return {
            'project': self._cf_serialize_project(),
            'lead': self._cf_serialize_lead(lead) if lead else None,
            'partner': self._cf_serialize_partner(partner) if partner else None,
            'kpi': self._cf_compute_kpi(leads, partner),
            'timeline': self._cf_get_timeline(limit=20),
            'contacts': self._cf_get_contacts(partner) if partner else [],
            'owner': self._cf_serialize_owner(),
        }

    def _cf_serialize_project(self):
        return {
            'id': self.id,
            'name': self.name or '',
            'status_dossier': self.cf_status_dossier or 'exploration',
            'dossier_priority': self.cf_dossier_priority or 'medium',
            'create_date': fields.Datetime.to_string(self.create_date) if self.create_date else '',
        }

    def _cf_serialize_lead(self, lead):
        if not lead:
            return None
        stage_name = lead.stage_id.name if lead.stage_id else ''
        stage_seq = lead.stage_id.sequence if lead.stage_id else 0
        return {
            'id': lead.id,
            'name': lead.name or '',
            'stage_name': stage_name,
            'stage_sequence': stage_seq,
            'stage_position': max(1, min(9, stage_seq // 10)) if stage_seq else 0,
            'expected_revenue': lead.expected_revenue or 0,
            'probability': lead.probability or 0,
            'priority': lead.priority or '0',
            'score': lead.cf_lead_score or 0,
            'rotting_state': lead.cf_rotting_state or 'ok',
            'days_in_stage': lead.cf_days_in_stage or 0,
            'forecast_value': lead.cf_forecast_value or 0,
        }

    def _cf_serialize_partner(self, partner):
        if not partner:
            return None
        country = partner.country_id
        return {
            'id': partner.id,
            'name': partner.name or '',
            'city': partner.city or '',
            'country_name': country.name if country else '',
            'country_code': (country.code or '').upper() if country else '',
            'phone': partner.phone or '',
            'mobile': partner.mobile or '',
            'email': partner.email or '',
            'website': partner.website or '',
            'lang': partner.lang or '',
        }

    def _cf_serialize_owner(self):
        user = self.user_id or self.env.user
        login = (user.login or '').lower().strip()
        color_class = OWNER_LOGIN_COLOR.get(login, 'gray')
        name = user.name or ''
        parts = name.split()
        if len(parts) >= 2:
            initials = (parts[0][0] + parts[-1][0]).upper()
        elif name:
            initials = name[:2].upper()
        else:
            initials = '?'
        return {
            'id': user.id,
            'name': name,
            'initials': initials,
            'color_class': color_class,
            'login': login,
        }

    def _cf_compute_kpi(self, leads, partner):
        # Revenue forecast
        total_revenue = sum(leads.mapped('expected_revenue'))
        total_forecast = sum(leads.mapped('cf_forecast_value'))

        # Sample count
        sample_count = 0
        if leads:
            sample_count = sum(leads.mapped('cf_sample_count'))

        # Email count
        email_count = 0
        if partner:
            email_count = self.env['mail.message'].search_count([
                ('partner_ids', 'in', partner.id),
                ('message_type', 'in', ['email', 'email_outgoing']),
            ])

        # Next activity
        next_activity = None
        activities = self.env['mail.activity'].search([
            '|',
            '&', ('res_model', '=', 'project.project'), ('res_id', '=', self.id),
            '&', ('res_model', '=', 'crm.lead'), ('res_id', 'in', leads.ids),
        ], order='date_deadline asc', limit=1)
        if activities:
            act = activities[0]
            next_activity = {
                'summary': act.summary or (act.activity_type_id.name if act.activity_type_id else ''),
                'date': fields.Date.to_string(act.date_deadline) if act.date_deadline else '',
                'type': act.activity_type_id.name if act.activity_type_id else '',
            }

        return {
            'revenue': total_revenue,
            'forecast': total_forecast,
            'sample_count': sample_count,
            'email_count': email_count,
            'next_activity': next_activity,
            'lead_count': len(leads),
        }

    def _cf_get_timeline(self, limit=20):
        """Unified timeline: mail.message + mail.activity for project and its leads."""
        events = []

        lead_ids = self.env['crm.lead'].search(
            [('cf_project_id', '=', self.id), ('active', '=', True)],
        ).ids

        # Mail messages on project
        messages = self.env['mail.message'].search([
            '|',
            '&', ('model', '=', 'project.project'), ('res_id', '=', self.id),
            '&', ('model', '=', 'crm.lead'), ('res_id', 'in', lead_ids),
        ], order='date desc', limit=limit)

        now = datetime.utcnow()
        for msg in messages:
            msg_type = msg.message_type or 'notification'
            if msg_type == 'notification' and msg.subtype_id and msg.subtype_id.internal:
                icon = 'note'
                color = 'gray'
                type_label = 'Nota'
            elif msg_type in ('email', 'email_outgoing'):
                icon = 'mail'
                color = 'blue'
                type_label = 'Email'
            elif msg_type == 'comment':
                icon = 'message'
                color = 'green'
                type_label = 'Commento'
            else:
                icon = 'bell'
                color = 'gray'
                type_label = 'Notifica'

            date_str = fields.Datetime.to_string(msg.date) if msg.date else ''
            events.append({
                'type': icon,
                'color': color,
                'type_label': type_label,
                'title': msg.subject or type_label,
                'subtitle': (msg.body or '')[:120] if msg.body else '',
                'date': date_str,
                'date_label': self._cf_relative_date(msg.date, now) if msg.date else '',
                'author': msg.author_id.name if msg.author_id else '',
                'model': msg.model or '',
            })

        # Activities (upcoming)
        activities = self.env['mail.activity'].search([
            '|',
            '&', ('res_model', '=', 'project.project'), ('res_id', '=', self.id),
            '&', ('res_model', '=', 'crm.lead'), ('res_id', 'in', lead_ids),
        ], order='date_deadline asc', limit=5)

        for act in activities:
            dl = act.date_deadline
            events.append({
                'type': 'activity',
                'color': 'orange',
                'type_label': 'Attività',
                'title': act.summary or (act.activity_type_id.name if act.activity_type_id else 'Attività'),
                'subtitle': act.note[:120] if act.note else '',
                'date': fields.Date.to_string(dl) if dl else '',
                'date_label': self._cf_relative_date(
                    datetime.combine(dl, datetime.min.time()), now
                ) if dl else '',
                'author': act.user_id.name if act.user_id else '',
                'model': act.res_model or '',
            })

        # Sort by date desc, limit
        events.sort(key=lambda e: e.get('date', ''), reverse=True)
        return events[:limit]

    def _cf_relative_date(self, dt, now):
        if not dt:
            return ''
        if isinstance(dt, str):
            return dt
        delta = now - dt
        minutes = int(delta.total_seconds() / 60)
        if minutes < 0:
            # Future (activities)
            abs_min = abs(minutes)
            if abs_min < 60:
                return 'tra %dm' % abs_min
            if abs_min < 1440:
                return 'tra %dh' % (abs_min // 60)
            return 'tra %dgg' % (abs_min // 1440)
        if minutes < 5:
            return 'ora'
        if minutes < 60:
            return '%dm fa' % minutes
        if minutes < 1440:
            return '%dh fa' % (minutes // 60)
        if minutes < 10080:
            return '%dgg fa' % (minutes // 1440)
        return '%d sett fa' % (minutes // 10080)

    def _cf_get_contacts(self, partner):
        if not partner:
            return []
        # Company + child contacts
        contacts = []
        # Primary partner first
        contacts.append(self._cf_contact_dict(partner, is_primary=True))

        children = self.env['res.partner'].search([
            ('parent_id', '=', partner.id),
            ('active', '=', True),
        ], limit=9, order='name')
        for child in children:
            contacts.append(self._cf_contact_dict(child, is_primary=False))

        return contacts[:10]

    def _cf_contact_dict(self, partner, is_primary=False):
        return {
            'id': partner.id,
            'name': partner.name or '',
            'email': partner.email or '',
            'phone': partner.phone or partner.mobile or '',
            'function': partner.function or '',
            'is_primary': is_primary,
        }
