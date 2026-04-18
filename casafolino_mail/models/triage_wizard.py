import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from .sender_decision import FREE_EMAIL_DOMAINS

_logger = logging.getLogger(__name__)


class CasafolinoMailTriageWizard(models.TransientModel):
    _name = 'casafolino.mail.triage.wizard'
    _description = 'Wizard triage orfano (form transient)'

    partner_id = fields.Many2one('res.partner', required=True, readonly=True)
    partner_name = fields.Char(related='partner_id.name', readonly=True)
    partner_email = fields.Char(related='partner_id.email', readonly=True)
    country_id = fields.Many2one(related='partner_id.country_id', readonly=True)

    # Stats read-only, popolati al create da orphan view
    inbound_count_90d = fields.Integer('Email IN 90gg', readonly=True)
    outbound_count_90d = fields.Integer('Email OUT 90gg', readonly=True)
    last_inbound_date = fields.Datetime('Ultimo IN', readonly=True)
    has_reply = fields.Boolean('Risposto', readonly=True)
    days_active = fields.Integer('Giorni attivi', readonly=True)
    priority = fields.Selection([
        ('hot', 'Hot'),
        ('warm', 'Warm'),
        ('cold', 'Cold'),
    ], string='Priorità', readonly=True)

    # Email preview, popolati al create
    last_email_subject = fields.Char('Ultimo oggetto', readonly=True)
    last_email_body_preview = fields.Text('Anteprima email', readonly=True)

    # Campo editabile
    notes = fields.Text('Note')

    # ── Navigation ───────────────────────────────────────────────────

    @api.model
    def _open_next_orphan(self):
        """Trova prossimo orfano non triagiato, crea wizard, apre form."""
        Orphan = self.env['casafolino.mail.orphan.partner']
        Decision = self.env['casafolino.mail.sender.decision']

        triaged_ids = Decision.search([
            ('active', '=', True)
        ]).mapped('partner_id').ids

        next_orphan = Orphan.search([
            ('partner_id', 'not in', triaged_ids)
        ], limit=1)

        if not next_orphan:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Triage completo!',
                    'message': 'Tutti gli orfani sono stati triagiati.',
                    'type': 'success',
                    'sticky': True,
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }

        # Leggi preview email
        subject, body = Decision._get_last_email_preview(next_orphan.partner_id.id)

        wizard = self.create({
            'partner_id': next_orphan.partner_id.id,
            'inbound_count_90d': next_orphan.inbound_count_90d,
            'outbound_count_90d': next_orphan.outbound_count_90d,
            'last_inbound_date': next_orphan.last_inbound_date,
            'has_reply': next_orphan.has_reply,
            'days_active': next_orphan.days_active,
            'priority': next_orphan.priority,
            'last_email_subject': subject,
            'last_email_body_preview': body,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Triage Orfani',
            'res_model': 'casafolino.mail.triage.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def action_start(self):
        """Entry point menu: apre primo orfano non triagiato."""
        return self._open_next_orphan()

    # ── Decision helper ──────────────────────────────────────────────

    def _create_decision(self, decision, **kwargs):
        """Crea record decisione per il partner corrente."""
        self.ensure_one()
        vals = {
            'partner_id': self.partner_id.id,
            'sender_email': self.partner_email or '',
            'decision': decision,
        }
        if self.notes:
            vals['notes'] = self.notes
        vals.update(kwargs)
        return self.env['casafolino.mail.sender.decision'].create(vals)

    # ── Triage actions ───────────────────────────────────────────────

    def action_triage_lead(self):
        """Crea Lead CRM e avanza al prossimo."""
        self.ensure_one()
        stage = self.env['crm.stage'].search(
            [('is_won', '!=', True)], order='sequence', limit=1)
        lead = self.env['crm.lead'].create({
            'name': 'Triage: %s' % self.partner_name,
            'partner_id': self.partner_id.id,
            'email_from': self.partner_email or '',
            'type': 'opportunity',
            'stage_id': stage.id if stage else False,
        })
        self._create_decision('lead_created', lead_id=lead.id)
        return self._open_next_orphan()

    def action_triage_assign(self):
        """Assegna a Josefina via mail.activity e avanza."""
        self.ensure_one()
        josefina = self.env['res.users'].search(
            [('login', 'ilike', 'josefina')], limit=1)
        if not josefina:
            josefina = self.env['res.users'].search(
                [('name', 'ilike', 'josefina')], limit=1)
        if not josefina:
            josefina = self.env.user

        partner_model_id = self.env['ir.model']._get('res.partner').id
        todo_type = self.env.ref('mail.mail_activity_data_todo')
        activity = self.env['mail.activity'].create({
            'activity_type_id': todo_type.id,
            'summary': 'Triage: contattare %s' % self.partner_name,
            'note': 'Ultima email:\n%s' % (
                self.last_email_body_preview or '(nessuna)')[:2000],
            'date_deadline': fields.Date.today(),
            'user_id': josefina.id,
            'res_model_id': partner_model_id,
            'res_id': self.partner_id.id,
        })
        self._create_decision('assigned', activity_id=activity.id)
        return self._open_next_orphan()

    def action_triage_snippet(self):
        """Marca come replied e apre snippet picker."""
        self.ensure_one()
        self._create_decision('replied')
        last_msg = self.env['casafolino.mail.sender.decision']._get_last_email(
            self.partner_id.id)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Seleziona Snippet',
            'res_model': 'casafolino.mail.snippet.picker',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': last_msg.id if last_msg else False},
        }

    def action_triage_ignore_sender(self):
        """Ignora mittente: crea sender_policy auto_discard per l'email."""
        self.ensure_one()
        email = (self.partner_email or '').lower().strip()
        if not email:
            raise UserError("Il partner non ha email, impossibile creare regola.")

        Policy = self.env['casafolino.mail.sender_policy'].sudo()
        policy = Policy.create({
            'name': 'Triage: ignora %s' % email,
            'pattern_type': 'domain',
            'pattern_value': '*%s*' % email,
            'action': 'auto_discard',
            'priority': 15,
            'notes': 'Creata da triage orfano il %s, decisione di %s' % (
                fields.Date.today(), self.env.user.name),
        })
        self._create_decision('ignored_sender', sender_policy_id=policy.id)
        return self._open_next_orphan()

    def action_triage_ignore_domain(self):
        """Ignora dominio: crea sender_policy auto_discard per il dominio."""
        self.ensure_one()
        email = (self.partner_email or '').lower().strip()
        if not email or '@' not in email:
            raise UserError("Il partner non ha email valida, impossibile estrarre dominio.")

        domain = email.split('@')[1]
        if domain in FREE_EMAIL_DOMAINS:
            raise UserError(
                "Impossibile ignorare il dominio %s: e' un dominio email pubblico "
                "(gmail/yahoo/hotmail/ecc.). Usa 'Ignora mittente' per il singolo indirizzo."
                % domain)

        Policy = self.env['casafolino.mail.sender_policy'].sudo()
        policy = Policy.create({
            'name': 'Triage: ignora dominio @%s' % domain,
            'pattern_type': 'domain',
            'pattern_value': '*@%s*' % domain,
            'action': 'auto_discard',
            'priority': 10,
            'notes': 'Triage dominio il %s da %s' % (
                fields.Date.today(), self.env.user.name),
        })
        self._create_decision('ignored_domain', sender_policy_id=policy.id)
        return self._open_next_orphan()

    def action_triage_skip(self):
        """Skip senza decisione, vai al prossimo."""
        return self._open_next_orphan()
