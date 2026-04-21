import logging
import re as _re

from odoo import api, fields, models
from odoo.exceptions import UserError

from .sender_decision import FREE_EMAIL_DOMAINS

_logger = logging.getLogger(__name__)

_BUYER_KEYWORDS = _re.compile(
    r'\b(quote|offer|sample|interesse|prezzo|listino|buyer|importer|'
    r'distributor|distribuire|campioni|offerta|pricing|price list|catalogo|'
    r'import|export|wholesale|bulk order)\b',
    _re.IGNORECASE)



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

    # ── Info Enrichment (F7 §3.8) ────────────────────────────────────
    sender_tld = fields.Char('TLD', compute='_compute_enrichment', store=False)
    partner_website_detected = fields.Char('Sito web', compute='_compute_enrichment', store=False)
    is_likely_buyer = fields.Boolean('Probabile buyer', compute='_compute_enrichment', store=False)
    similar_partners_count = fields.Integer('Partner simili', compute='_compute_enrichment', store=False)

    @api.depends('partner_email', 'last_email_subject', 'last_email_body_preview')
    def _compute_enrichment(self):
        for rec in self:
            email = (rec.partner_email or '').lower().strip()
            # TLD
            if '@' in email:
                domain = email.split('@')[1]
                parts = domain.split('.')
                rec.sender_tld = '.' + parts[-1] if parts else ''
                # Website (non-free domains)
                if domain not in FREE_EMAIL_DOMAINS:
                    rec.partner_website_detected = domain
                else:
                    rec.partner_website_detected = ''
                # Similar partners count (same domain)
                rec.similar_partners_count = self.env['res.partner'].search_count([
                    ('email', '=ilike', '%%@' + domain),
                    ('id', '!=', rec.partner_id.id),
                ])
            else:
                rec.sender_tld = ''
                rec.partner_website_detected = ''
                rec.similar_partners_count = 0

            # Is likely buyer
            text = (rec.last_email_subject or '') + ' ' + (rec.last_email_body_preview or '')
            rec.is_likely_buyer = bool(_BUYER_KEYWORDS.search(text))

    # Campo editabile
    notes = fields.Text('Note')

    # ── Navigation ───────────────────────────────────────────────────

    @api.model
    def _open_next_orphan(self, exclude_partner_ids=None):
        """Trova prossimo orfano non triagiato, crea wizard, apre form.

        Args:
            exclude_partner_ids: list of partner IDs to exclude (usually the current one)
        """
        Orphan = self.env['casafolino.mail.orphan.partner']
        Decision = self.env['casafolino.mail.sender.decision']

        triaged_ids = Decision.search([
            ('active', '=', True)
        ]).mapped('partner_id').ids
        exclude_ids = list(set(triaged_ids + (exclude_partner_ids or [])))

        next_orphan = Orphan.search([
            ('partner_id', 'not in', exclude_ids)
        ], limit=1)

        if not next_orphan:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Triage completo!',
                    'message': 'Tutti gli orfani triagiati. (%d decisioni attive)' % len(triaged_ids),
                    'type': 'success',
                    'sticky': False,
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
        return self._open_next_orphan(exclude_partner_ids=[self.partner_id.id])

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
        return self._open_next_orphan(exclude_partner_ids=[self.partner_id.id])

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
        # Retroactive apply: update existing new/review messages from this sender
        self._retroactive_apply_policy(policy, [
            ('sender_email', '=ilike', email),
        ])
        self._create_decision('ignored_sender', sender_policy_id=policy.id)
        return self._open_next_orphan(exclude_partner_ids=[self.partner_id.id])

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
        # Retroactive apply: update existing new/review messages from this domain
        self._retroactive_apply_policy(policy, [
            ('sender_domain', '=ilike', domain),
        ])
        self._create_decision('ignored_domain', sender_policy_id=policy.id)
        return self._open_next_orphan(exclude_partner_ids=[self.partner_id.id])

    def _retroactive_apply_policy(self, policy, extra_domain):
        """Apply a newly created policy retroactively to existing new/review messages.

        Args:
            policy: casafolino.mail.sender_policy record
            extra_domain: list of domain tuples to filter messages (e.g. sender_email match)
        """
        Msg = self.env['casafolino.mail.message'].sudo()
        domain = [
            ('state', 'in', ['new', 'review']),
            ('direction', '=', 'inbound'),
        ] + extra_domain
        msgs = Msg.search(domain)
        if msgs:
            state_map = {
                'auto_keep': 'auto_keep',
                'auto_discard': 'auto_discard',
                'escalate': 'review',
                'review': 'review',
            }
            new_state = state_map.get(policy.action, 'review')
            vals = {'state': new_state, 'policy_applied_id': policy.id}
            if policy.action == 'escalate':
                vals['is_important'] = True
            msgs.write(vals)
            _logger.info(
                "[triage wizard] Retroactive apply policy %s to %d messages",
                policy.name, len(msgs))

    def action_triage_keep(self):
        """Tieni partner come contatto valido, nessuna policy, nessun discard.
        Crea decisione 'kept' per rimuoverlo dalla queue."""
        self.ensure_one()
        self._create_decision('kept', notes='Contatto valido, gestito da triage orfano')
        return self._open_next_orphan(exclude_partner_ids=[self.partner_id.id])

    def action_triage_skip(self):
        """Skip senza decisione, vai al prossimo."""
        self.ensure_one()
        return self._open_next_orphan(exclude_partner_ids=[self.partner_id.id])
