import logging
import re

from odoo import api, fields, models, tools
from odoo.exceptions import UserError

from .sender_decision import FREE_EMAIL_DOMAINS

_logger = logging.getLogger(__name__)


class CasafolinoMailOrphanPartner(models.Model):
    _name = 'casafolino.mail.orphan.partner'
    _description = 'Buyer senza lead — partner con email ma senza opportunità CRM'
    _auto = False
    _order = 'priority desc, inbound_count_90d desc, last_inbound_date desc'

    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    partner_name = fields.Char('Nome', readonly=True)
    partner_email = fields.Char('Email', readonly=True)
    country_id = fields.Many2one('res.country', string='Paese', readonly=True)
    inbound_count_90d = fields.Integer('IN 90gg', readonly=True)
    outbound_count_90d = fields.Integer('OUT 90gg', readonly=True)
    last_inbound_date = fields.Datetime('Ultimo IN', readonly=True)
    first_inbound_date = fields.Datetime('Primo IN', readonly=True)
    days_active = fields.Integer('Giorni attivi', readonly=True)
    has_reply = fields.Boolean('Risposto', readonly=True)
    priority = fields.Selection([
        ('hot', 'Hot'),
        ('warm', 'Warm'),
        ('cold', 'Cold'),
    ], string='Priorità', readonly=True)

    # ── Virtual triage fields (store=False obbligatorio su SQL view) ──
    is_triaged = fields.Boolean(
        'Triaged', compute='_compute_triage_info',
        store=False, readonly=True, search='_search_is_triaged')
    triage_decision = fields.Char(
        'Decisione', compute='_compute_triage_info',
        store=False, readonly=True, search='_search_triage_decision')
    last_email_subject = fields.Char(
        'Ultimo oggetto', compute='_compute_last_email',
        store=False, readonly=True)
    last_email_body_preview = fields.Text(
        'Anteprima email', compute='_compute_last_email',
        store=False, readonly=True)

    def _search_is_triaged(self, operator, value):
        """Search su campo compute: filtra orfani triaged/non triaged."""
        triaged_partner_ids = self.env['casafolino.mail.sender.decision'].search([
            ('active', '=', True)
        ]).mapped('partner_id').ids
        # Normalizza: is_triaged = True  →  partner_id in triaged
        #             is_triaged = False →  partner_id not in triaged
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('partner_id', 'in', triaged_partner_ids)]
        return [('partner_id', 'not in', triaged_partner_ids)]

    def _search_triage_decision(self, operator, value):
        """Search su campo compute: filtra per tipo decisione."""
        domain = [('active', '=', True)]
        if value:
            domain.append(('decision', operator, value))
        decisions = self.env['casafolino.mail.sender.decision'].search(domain)
        return [('partner_id', 'in', decisions.mapped('partner_id').ids)]

    def _compute_triage_info(self):
        Decision = self.env['casafolino.mail.sender.decision']
        for rec in self:
            dec = Decision.search([('partner_id', '=', rec.partner_id.id),
                                   ('active', '=', True)], limit=1)
            rec.is_triaged = bool(dec)
            rec.triage_decision = dec.decision if dec else ''

    def _compute_last_email(self):
        Decision = self.env['casafolino.mail.sender.decision']
        for rec in self:
            subject, body = Decision._get_last_email_preview(rec.partner_id.id)
            rec.last_email_subject = subject
            rec.last_email_body_preview = body

    # ── Triage navigation ────────────────────────────────────────────

    def _action_next_orphan(self):
        """Trova prossimo orfano non triagiato e apre form triage."""
        triaged_ids = self.env['casafolino.mail.sender.decision'].search([
            ('active', '=', True)
        ]).mapped('partner_id').ids
        next_orphan = self.search([('partner_id', 'not in', triaged_ids)], limit=1)
        if next_orphan:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Triage Orfani',
                'res_model': 'casafolino.mail.orphan.partner',
                'res_id': next_orphan.id,
                'view_mode': 'form',
                'view_id': self.env.ref(
                    'casafolino_mail.casafolino_mail_orphan_triage_form').id,
                'target': 'current',
            }
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

    @api.model
    def action_start_triage(self):
        """Entry point menu: apre primo orfano non triagiato."""
        return self.browse()._action_next_orphan()

    # ── Triage actions ───────────────────────────────────────────────

    def _create_decision(self, decision, **kwargs):
        """Helper: crea decision record."""
        self.ensure_one()
        vals = {
            'partner_id': self.partner_id.id,
            'sender_email': self.partner_email or self.partner_id.email or '',
            'decision': decision,
        }
        vals.update(kwargs)
        return self.env['casafolino.mail.sender.decision'].create(vals)

    def action_triage_lead(self):
        """Crea Lead CRM e avanza."""
        self.ensure_one()
        stage = self.env['crm.stage'].search(
            [('is_won', '!=', True)], order='sequence', limit=1)
        lead = self.env['crm.lead'].create({
            'name': 'Triage: %s' % self.partner_name,
            'partner_id': self.partner_id.id,
            'email_from': self.partner_email or self.partner_id.email,
            'type': 'opportunity',
            'stage_id': stage.id if stage else False,
        })
        self._create_decision('lead_created', lead_id=lead.id)
        return self._action_next_orphan()

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
        _, body_preview = self.env['casafolino.mail.sender.decision']._get_last_email_preview(
            self.partner_id.id)
        activity = self.env['mail.activity'].create({
            'activity_type_id': todo_type.id,
            'summary': 'Triage: contattare %s' % self.partner_name,
            'note': 'Ultima email:\n%s' % (body_preview or '(nessuna)')[:2000],
            'date_deadline': fields.Date.today(),
            'user_id': josefina.id,
            'res_model_id': partner_model_id,
            'res_id': self.partner_id.id,
        })
        self._create_decision('assigned', activity_id=activity.id)
        return self._action_next_orphan()

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
        email = (self.partner_email or self.partner_id.email or '').lower().strip()
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
        return self._action_next_orphan()

    def action_triage_ignore_domain(self):
        """Ignora dominio: crea sender_policy auto_discard per il dominio."""
        self.ensure_one()
        email = (self.partner_email or self.partner_id.email or '').lower().strip()
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
        return self._action_next_orphan()

    def action_triage_skip(self):
        """Skip senza decisione, vai al prossimo."""
        return self._action_next_orphan()

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH partner_mail_stats AS (
                    SELECT
                        m.partner_id,
                        COUNT(CASE WHEN m.direction = 'inbound' THEN 1 END) AS inbound_count_90d,
                        COUNT(CASE WHEN m.direction = 'outbound' THEN 1 END) AS outbound_count_90d,
                        MAX(CASE WHEN m.direction = 'inbound' THEN m.email_date END) AS last_inbound_date,
                        MIN(CASE WHEN m.direction = 'inbound' THEN m.email_date END) AS first_inbound_date
                    FROM casafolino_mail_message m
                    WHERE m.partner_id IS NOT NULL
                      AND m.state IN ('keep', 'auto_keep')
                      AND m.email_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '90 days'
                    GROUP BY m.partner_id
                    HAVING COUNT(CASE WHEN m.direction = 'inbound' THEN 1 END) > 0
                )
                SELECT
                    p.id AS id,
                    p.id AS partner_id,
                    p.name AS partner_name,
                    p.email AS partner_email,
                    p.country_id,
                    pms.inbound_count_90d,
                    pms.outbound_count_90d,
                    pms.last_inbound_date,
                    pms.first_inbound_date,
                    COALESCE(
                        EXTRACT(DAY FROM pms.last_inbound_date - pms.first_inbound_date)::INTEGER,
                        0
                    ) AS days_active,
                    COALESCE(pms.outbound_count_90d, 0) > 0 AS has_reply,
                    CASE
                        WHEN pms.inbound_count_90d >= 5
                            OR pms.last_inbound_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '7 days'
                        THEN 'hot'
                        WHEN pms.inbound_count_90d >= 2
                            OR pms.last_inbound_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days'
                        THEN 'warm'
                        ELSE 'cold'
                    END AS priority
                FROM res_partner p
                JOIN partner_mail_stats pms ON pms.partner_id = p.id
                WHERE NOT EXISTS (
                    SELECT 1 FROM crm_lead l
                    JOIN crm_stage s ON s.id = l.stage_id
                    WHERE l.partner_id = p.id
                      AND l.active = TRUE
                      AND l.type = 'opportunity'
                      AND COALESCE(s.is_won, FALSE) = FALSE
                )
                AND (p.email IS NULL OR p.email NOT ILIKE '%%@casafolino.com')
                AND p.id NOT IN (SELECT COALESCE(partner_id, 0) FROM res_users)
            )
        """ % self._table)

    def action_create_lead(self):
        """Crea un crm.lead per questo partner orfano e apre il form."""
        self.ensure_one()
        stage = self.env['crm.stage'].search(
            [('is_won', '!=', True)], order='sequence', limit=1)
        lead = self.env['crm.lead'].create({
            'name': 'Lead da email: %s' % self.partner_name,
            'partner_id': self.partner_id.id,
            'email_from': self.partner_email or self.partner_id.email,
            'type': 'opportunity',
            'stage_id': stage.id if stage else False,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lead — %s' % self.partner_name,
            'res_model': 'crm.lead',
            'res_id': lead.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_emails(self):
        """Apre lista email filtrata per questo partner."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Email — %s' % self.partner_name,
            'res_model': 'casafolino.mail.message',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.partner_id.id),
                       ('state', 'in', ['keep', 'auto_keep'])],
        }
