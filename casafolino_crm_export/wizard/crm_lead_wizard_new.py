import json
import logging
import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CrmLeadWizardNew(models.TransientModel):
    _name = 'crm.lead.wizard.new'
    _description = "Wizard Nuovo Lead"

    # --- Cliente ---
    partner_id = fields.Many2one(
        'res.partner', string='Cliente esistente',
        domain=[('is_company', '=', True)],
    )
    is_new_partner = fields.Boolean(string='Nuovo cliente')
    new_partner_name = fields.Char(string='Nome azienda')
    new_partner_email = fields.Char(string='Email')
    new_partner_country_id = fields.Many2one('res.country', string='Paese')

    # --- Origine ---
    origin_type = fields.Selection([
        ('fair', 'Fiera'),
        ('inbound_mail', 'Email in entrata'),
        ('agent_referral', 'Segnalazione agente'),
        ('web', 'Web'),
        ('reorder', 'Riordino'),
        ('cold_outreach', 'Cold outreach'),
    ], string='Origine')
    origin_fair_tag_id = fields.Many2one(
        'crm.tag', string='Fiera',
        domain=[('cf_category', '=', 'fair')],
    )
    origin_agent_id = fields.Many2one(
        'res.partner', string='Agente',
        domain=[('cf_partner_role', '=', 'agent')],
    )

    # --- Prodotto ---
    product_tag_ids = fields.Many2many(
        'crm.tag', string='Prodotti',
        relation='crm_lead_wizard_product_tag_rel',
        domain=[('cf_category', '=', 'product')],
    )
    expected_revenue = fields.Float(string='Revenue atteso')
    priority = fields.Selection([
        ('0', 'Bassa'),
        ('1', 'Media'),
        ('2', 'Alta'),
    ], string='Priorita', default='1')

    # --- Owner ---
    user_id = fields.Many2one(
        'res.users', string='Owner', required=True,
        default=lambda self: self.env.user,
    )

    # --- Prossima azione ---
    next_activity_type = fields.Selection([
        ('email', 'Email'),
        ('call', 'Chiamata'),
        ('meeting', 'Meeting'),
        ('todo', 'Todo'),
    ], string='Tipo attivita')
    next_activity_summary = fields.Char(string='Sommario attivita')
    next_activity_date = fields.Date(string='Data attivita')

    # --- Computed / AI ---
    existing_projects_count = fields.Integer(
        string='Progetti esistenti', compute='_compute_existing_projects',
    )
    existing_projects_data = fields.Text(
        string='Dati progetti', compute='_compute_existing_projects',
    )
    ai_suggestion_text = fields.Text(string='Suggerimento AI')
    ai_suggestion_action = fields.Selection([
        ('continue', 'Continua'),
        ('see_existing', 'Vedi esistenti'),
        ('duplicate', 'Possibile duplicato'),
    ], string='Azione suggerita AI')

    @api.depends('partner_id')
    def _compute_existing_projects(self):
        for rec in self:
            if rec.partner_id:
                projects = self.env['project.project'].search([
                    ('partner_id', '=', rec.partner_id.id),
                ])
                rec.existing_projects_count = len(projects)
                rec.existing_projects_data = json.dumps([{
                    'id': p.id,
                    'name': p.name,
                    'stage': p.stage_id.name if p.stage_id else '',
                } for p in projects[:10]])
            else:
                rec.existing_projects_count = 0
                rec.existing_projects_data = '[]'

    def action_get_ai_suggestion(self):
        """Call Groq LLM to get AI suggestion about this lead."""
        self.ensure_one()
        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'casafolino.groq_api_key', ''
        )
        if not api_key:
            self.ai_suggestion_text = _("Chiave API Groq non configurata.")
            self.ai_suggestion_action = 'continue'
            return

        partner_name = self.partner_id.name if self.partner_id else self.new_partner_name or ''
        existing_leads = self.env['crm.lead'].search_count([
            ('partner_id', '=', self.partner_id.id),
        ]) if self.partner_id else 0

        prompt = (
            f"Sei un assistente CRM per un'azienda food italiana (CasaFolino). "
            f"Un operatore sta creando un nuovo lead per il cliente '{partner_name}'. "
            f"Il cliente ha gia {self.existing_projects_count} progetti e {existing_leads} lead nel sistema. "
            f"Origine: {self.origin_type or 'non specificata'}. "
            f"Rispondi in JSON con: "
            f'{{"suggestion": "breve consiglio in italiano (max 60 parole)", '
            f'"action": "continue|see_existing|duplicate"}}'
        )

        try:
            resp = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'llama-3.3-70b-versatile',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.3,
                    'max_tokens': 200,
                },
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data['choices'][0]['message']['content']
            parsed = json.loads(content)
            self.ai_suggestion_text = parsed.get('suggestion', '')
            action = parsed.get('action', 'continue')
            if action in ('continue', 'see_existing', 'duplicate'):
                self.ai_suggestion_action = action
            else:
                self.ai_suggestion_action = 'continue'
        except Exception as e:
            _logger.warning("Groq AI suggestion failed: %s", e)
            self.ai_suggestion_text = _("Suggerimento AI non disponibile.")
            self.ai_suggestion_action = 'continue'

    def get_preview_data(self):
        """Return dict for live preview in the dialog."""
        self.ensure_one()
        partner_name = ''
        if self.partner_id:
            partner_name = self.partner_id.name
        elif self.new_partner_name:
            partner_name = self.new_partner_name

        return {
            'partner_name': partner_name,
            'origin_type': dict(self._fields['origin_type'].selection).get(
                self.origin_type, ''
            ) if self.origin_type else '',
            'product_tags': [t.name for t in self.product_tag_ids],
            'expected_revenue': self.expected_revenue,
            'priority': self.priority,
            'user_name': self.user_id.name if self.user_id else '',
            'next_activity_type': self.next_activity_type or '',
            'next_activity_date': str(self.next_activity_date) if self.next_activity_date else '',
        }

    def action_create_lead(self):
        """Atomic creation: partner (if new) + lead + tags + activity."""
        self.ensure_one()

        # Validation
        if not self.partner_id and not self.is_new_partner:
            raise UserError(_("Seleziona un cliente esistente o creane uno nuovo."))
        if self.is_new_partner and not self.new_partner_name:
            raise UserError(_("Inserisci il nome dell'azienda."))

        # Create partner if new
        partner = self.partner_id
        if self.is_new_partner:
            partner = self.env['res.partner'].create({
                'name': self.new_partner_name,
                'email': self.new_partner_email or False,
                'country_id': self.new_partner_country_id.id if self.new_partner_country_id else False,
                'is_company': True,
            })

        # Build tag list
        tag_ids = self.product_tag_ids.ids[:]
        if self.origin_fair_tag_id:
            tag_ids.append(self.origin_fair_tag_id.id)

        # Determine source
        source_map = {
            'fair': 'Fiera',
            'inbound_mail': 'Email',
            'agent_referral': 'Agente',
            'web': 'Web',
            'reorder': 'Riordino',
            'cold_outreach': 'Cold outreach',
        }

        # Create lead
        lead_vals = {
            'name': f"{partner.name} - Nuovo lead",
            'partner_id': partner.id,
            'user_id': self.user_id.id,
            'expected_revenue': self.expected_revenue,
            'priority': self.priority,
            'tag_ids': [(6, 0, tag_ids)] if tag_ids else False,
            'type': 'opportunity',
        }
        if self.origin_type:
            lead_vals['description'] = f"Origine: {source_map.get(self.origin_type, self.origin_type)}"

        lead = self.env['crm.lead'].create(lead_vals)

        # Create activity if specified
        if self.next_activity_type and self.next_activity_date:
            activity_type_map = {
                'email': 'mail.mail_activity_data_email',
                'call': 'mail.mail_activity_data_call',
                'meeting': 'mail.mail_activity_data_meeting',
                'todo': 'mail.mail_activity_data_todo',
            }
            activity_type_xmlid = activity_type_map.get(self.next_activity_type)
            if activity_type_xmlid:
                activity_type = self.env.ref(activity_type_xmlid, raise_if_not_found=False)
                if activity_type:
                    self.env['mail.activity'].create({
                        'res_model_id': self.env['ir.model']._get_id('crm.lead'),
                        'res_id': lead.id,
                        'activity_type_id': activity_type.id,
                        'summary': self.next_activity_summary or '',
                        'date_deadline': self.next_activity_date,
                        'user_id': self.user_id.id,
                    })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': lead.id,
            'view_mode': 'form',
            'target': 'current',
        }
