import json
import logging
import math
import re
import time
from datetime import timedelta

import requests as req

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

# ── NBA Rules (20 rules, priority order) ────────────────────────────────
# Each rule: (id, name, condition_fn, urgency, template_it)
# condition_fn receives a dict with partner data and returns bool

NBA_RULES = [
    # === CRITICAL (1-5) ===
    (1, 'overdue_payment',
     lambda d: d['overdue_amount'] > 0,
     'critical',
     "Pagamento scaduto: €{overdue_amount:.0f}. Sollecitare subito."),

    (2, 'complaint_unanswered',
     lambda d: d['last_inbound_unanswered'] and d['days_since_last_inbound'] <= 3
               and d['last_sentiment'] == 'negative',
     'critical',
     "Reclamo senza risposta da {days_since_last_inbound}g. Rispondere urgentemente."),

    (3, 'lead_stale_hot',
     lambda d: d['has_open_lead'] and d['lead_stage'] in ('proposition', 'negotiation')
               and d['days_lead_no_activity'] > 7,
     'high',
     "Trattativa in {lead_stage} ferma da {days_lead_no_activity}g. Riattivare."),

    (4, 'order_pending_confirmation',
     lambda d: d['pending_orders'] > 0,
     'high',
     "{pending_orders} ordine/i in attesa di conferma. Verificare."),

    (5, 'high_urgency_email',
     lambda d: d['last_ai_urgency'] == 'high' and d['last_inbound_unanswered'],
     'high',
     "Email urgente senza risposta. Priorita massima."),

    # === HIGH (6-10) ===
    (6, 'silent_warm_lead',
     lambda d: d['has_open_lead'] and d['days_since_last_email'] > 14
               and d['hotness_tier'] in ('hot', 'warm'),
     'high',
     "Partner {hotness_tier} silente da {days_since_last_email}g con lead aperto. Follow-up."),

    (7, 'reorder_opportunity',
     lambda d: d['last_order_days'] and 60 <= d['last_order_days'] <= 120
               and d['ytd_revenue'] > 1000,
     'high',
     "Ultimo ordine {last_order_days}g fa (fatturato YTD €{ytd_revenue:.0f}). Proporre riordino."),

    (8, 'fair_followup',
     lambda d: d['met_at_fair'] and d['days_since_fair'] and 1 <= d['days_since_fair'] <= 14,
     'high',
     "Incontrato in fiera {fair_name} {days_since_fair}g fa. Follow-up entro 48h."),

    (9, 'new_contact_no_action',
     lambda d: d['is_new_contact'] and d['days_since_creation'] <= 7
               and d['total_emails'] == 0,
     'medium',
     "Nuovo contatto da {days_since_creation}g senza email. Inviare intro."),

    (10, 'action_required_pending',
     lambda d: d['last_ai_action_required'] and d['last_inbound_unanswered']
                and d['days_since_last_inbound'] <= 5,
     'high',
     "Email richiede azione, senza risposta da {days_since_last_inbound}g."),

    # === MEDIUM (11-15) ===
    (11, 'upsell_top_buyer',
     lambda d: d['ytd_revenue'] > 10000 and d['order_count_ytd'] >= 3
               and d['hotness_tier'] == 'hot',
     'medium',
     "Top buyer (€{ytd_revenue:.0f} YTD, {order_count_ytd} ordini). Proporre upsell/cross-sell."),

    (12, 'dormant_reactivation',
     lambda d: d['hotness_tier'] == 'dormant' and d['lifetime_revenue'] > 5000,
     'medium',
     "Partner dormiente con storico €{lifetime_revenue:.0f}. Campagna riattivazione."),

    (13, 'sentiment_declining',
     lambda d: d['sentiment_trend'] == 'declining',
     'medium',
     "Sentiment in calo nelle ultime email. Attenzione alla relazione."),

    (14, 'missing_key_info',
     lambda d: not d['has_phone'] and not d['has_linkedin']
               and d['total_emails'] >= 3,
     'low',
     "3+ email ma nessun telefono/LinkedIn. Arricchire contatto (007)."),

    (15, 'lead_qualification_needed',
     lambda d: d['has_open_lead'] and d['lead_stage'] == 'new'
               and d['days_lead_no_activity'] > 3,
     'medium',
     "Lead in 'new' da {days_lead_no_activity}g. Qualificare o scartare."),

    # === LOW / INFO (16-20) ===
    (16, 'birthday_coming',
     lambda d: d['days_to_birthday'] is not None and 0 <= d['days_to_birthday'] <= 7,
     'info',
     "Compleanno tra {days_to_birthday}g. Inviare auguri."),

    (17, 'no_007_enrichment',
     lambda d: not d['is_007_enriched'] and d['total_emails'] >= 5
               and d['hotness_tier'] in ('hot', 'warm'),
     'low',
     "Partner {hotness_tier} non arricchito con 007. Lanciare enrichment."),

    (18, 'gdpr_consent_missing',
     lambda d: not d['has_gdpr_consent'] and d['total_emails'] >= 5,
     'low',
     "5+ email senza consenso GDPR registrato. Richiedere."),

    (19, 'quarterly_review',
     lambda d: d['ytd_revenue'] > 5000 and d['days_since_last_email'] > 60,
     'info',
     "Partner con fatturato >€5K silente da {days_since_last_email}g. Review trimestrale."),

    (20, 'positive_momentum',
     lambda d: d['sentiment_trend'] == 'improving' and d['has_open_lead'],
     'info',
     "Sentiment positivo e lead aperto. Buon momento per proposta."),
]


class CasafolinoPartnerIntelligence(models.Model):
    _name = 'casafolino.partner.intelligence'
    _description = 'Partner Intelligence & NBA'
    _order = 'hotness_score desc'

    partner_id = fields.Many2one('res.partner', string='Partner',
                                  required=True, ondelete='cascade', index=True)
    # ── Hotness ──
    hotness_score = fields.Integer('Hotness Score', default=0, index=True)
    hotness_tier = fields.Selection([
        ('hot', '\U0001f525 Hot'), ('warm', '\U0001f536 Warm'), ('active', '\U0001f4bc Active'),
        ('cold', '\U0001f9ca Cold'), ('dormant', '\u26ab Dormant'),
    ], string='Tier', compute='_compute_tier', store=True)
    hotness_components_json = fields.Text('Componenti Hotness')
    last_rebuild_at = fields.Datetime('Ultimo rebuild')
    pinned_hot = fields.Boolean('Forzato Hot', default=False)
    pinned_ignore = fields.Boolean('Ignora rebuild', default=False)

    # ── NBA ──
    nba_text = fields.Char('NBA Suggerimento', default='')
    nba_urgency = fields.Selection([
        ('critical', 'Critico'), ('high', 'Alto'),
        ('medium', 'Medio'), ('low', 'Basso'), ('info', 'Info'),
    ], string='NBA Urgenza')
    nba_rule_id = fields.Integer('NBA Rule ID', default=0)
    nba_from_llm = fields.Boolean('NBA da LLM', default=False)
    nba_computed_at = fields.Datetime('NBA calcolato il')

    _sql_constraints = [
        ('partner_unique', 'unique(partner_id)', 'Intelligence record duplicato per partner.'),
    ]

    @api.depends('hotness_score')
    def _compute_tier(self):
        for rec in self:
            s = rec.hotness_score
            if s >= 80:
                rec.hotness_tier = 'hot'
            elif s >= 60:
                rec.hotness_tier = 'warm'
            elif s >= 40:
                rec.hotness_tier = 'active'
            elif s >= 20:
                rec.hotness_tier = 'cold'
            else:
                rec.hotness_tier = 'dormant'

    # ── Hotness computation ──────────────────────────────────────────

    def _compute_for_partner(self, partner_id):
        """Compute hotness + NBA for a single partner. Creates or updates record."""
        partner = self.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return

        rec = self.search([('partner_id', '=', partner_id)], limit=1)
        if rec and rec.pinned_ignore:
            return rec

        # Compute hotness components
        revenue = self._compute_component_revenue(partner)
        activity = self._compute_component_activity(partner)
        pipeline = self._compute_component_pipeline(partner)
        freshness = self._compute_component_freshness(partner)
        strategic = self._compute_component_strategic_boost(partner)

        score = int(
            0.30 * revenue +
            0.25 * activity +
            0.20 * pipeline +
            0.15 * freshness +
            0.10 * strategic
        )
        score = min(100, max(0, score))

        if rec and rec.pinned_hot:
            score = max(80, score)

        components = {
            'revenue': revenue,
            'activity': activity,
            'pipeline': pipeline,
            'freshness': freshness,
            'strategic': strategic,
        }

        vals = {
            'hotness_score': score,
            'hotness_components_json': json.dumps(components),
            'last_rebuild_at': fields.Datetime.now(),
        }

        if rec:
            rec.write(vals)
        else:
            vals['partner_id'] = partner_id
            rec = self.create(vals)

        # Compute NBA
        self._compute_nba_for_partner(rec, partner)

        return rec

    def _get_partner_ids(self, partner):
        """Get partner + parent + children IDs for hierarchical queries."""
        partner_ids = [partner.id]
        if partner.parent_id:
            partner_ids.append(partner.parent_id.id)
        if partner.is_company:
            children = self.env['res.partner'].search([('parent_id', '=', partner.id)])
            partner_ids.extend(children.ids)
        return partner_ids

    def _compute_component_revenue(self, partner):
        """Revenue score 0-100 (log scale, 12-month invoices). Includes company hierarchy."""
        cutoff = fields.Date.context_today(self) - timedelta(days=365)
        partner_ids = self._get_partner_ids(partner)
        try:
            invoices = self.env['account.move'].sudo().search([
                ('partner_id', 'in', partner_ids),
                ('move_type', 'in', ('out_invoice', 'out_refund')),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', cutoff),
            ])
            total = sum(inv.amount_untaxed_signed for inv in invoices)
        except Exception:
            total = 0
        if total <= 0:
            return 0
        if total >= 100000:
            return 100
        return min(100, int(30 * math.log10(max(total, 1)) - 60))

    def _compute_component_activity(self, partner):
        """Activity score: 90-day event count (emails + orders + activities). Includes hierarchy."""
        cutoff = fields.Datetime.now() - timedelta(days=90)
        partner_ids = self._get_partner_ids(partner)
        count = 0
        count += self.env['casafolino.mail.message'].search_count([
            ('partner_id', 'in', partner_ids),
            ('state', 'in', ('keep', 'auto_keep')),
            ('email_date', '>=', cutoff),
        ])
        try:
            count += self.env['sale.order'].sudo().search_count([
                ('partner_id', 'in', partner_ids),
                ('date_order', '>=', cutoff),
            ])
        except Exception:
            pass
        try:
            partner_model = self.env['ir.model']._get('res.partner')
            if partner_model:
                count += self.env['mail.activity'].sudo().search_count([
                    ('res_model_id', '=', partner_model.id),
                    ('res_id', 'in', partner_ids),
                    ('create_date', '>=', cutoff),
                ])
        except Exception:
            pass
        if count == 0:
            return 0
        if count <= 5:
            return 30
        if count <= 15:
            return 60
        if count <= 30:
            return 80
        return 100

    def _compute_component_pipeline(self, partner):
        """Pipeline score: max(stage_weight * probability) on open leads. Includes hierarchy."""
        partner_ids = self._get_partner_ids(partner)
        try:
            leads = self.env['crm.lead'].sudo().search([
                ('partner_id', 'in', partner_ids),
                ('active', '=', True),
                ('stage_id.is_won', '=', False),
                ('probability', '<', 100),
            ])
        except Exception:
            return 0
        if not leads:
            return 0
        stage_weights = {
            'new': 10, 'qualified': 30, 'proposition': 70,
            'proposal': 70, 'negotiation': 85, 'won': 100,
        }
        best = 0
        for lead in leads:
            stage_name = (lead.stage_id.name or '').lower().replace(' ', '_')
            # Try partial match
            weight = 10
            for key, w in stage_weights.items():
                if key in stage_name:
                    weight = w
                    break
            prob = (lead.probability or 10) / 100.0
            best = max(best, int(weight * prob))
        return min(100, best)

    def _compute_component_freshness(self, partner):
        """Freshness: interpolation of days since last keep email."""
        last_msg = self.env['casafolino.mail.message'].search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ('keep', 'auto_keep')),
        ], order='email_date desc', limit=1)
        if not last_msg or not last_msg.email_date:
            return 5
        days = (fields.Datetime.now() - last_msg.email_date).days
        if days <= 0:
            return 100
        if days <= 7:
            return 80
        if days <= 30:
            return 50
        if days <= 90:
            return 20
        if days <= 180:
            return 10
        return 5

    def _compute_component_strategic_boost(self, partner):
        """Strategic boost from tags."""
        tag_names = set()
        if hasattr(partner, 'cf_tag_ids'):
            tag_names = {t.name.lower() for t in partner.cf_tag_ids if t.name}
        if hasattr(partner, 'category_id'):
            tag_names |= {t.name.lower() for t in partner.category_id if t.name}

        high_tags = {'gdo', 'dach', 'exportvip', 'key account', 'strategic', 'strategico'}
        medium_tags = {'prospect qualificato', 'prospect'}
        if tag_names & high_tags:
            return 100
        if tag_names & medium_tags:
            return 70
        return 0

    # ── NBA Engine ───────────────────────────────────────────────────

    def _compute_nba_for_partner(self, rec, partner):
        """Evaluate 20 NBA rules + LLM fallback. Updates rec in place."""
        data = self._build_nba_context(partner)

        # Evaluate rules in priority order
        for rule_id, rule_name, condition_fn, urgency, template in NBA_RULES:
            try:
                if condition_fn(data):
                    text = template.format(**{k: v for k, v in data.items()
                                              if v is not None})
                    rec.write({
                        'nba_text': text[:200],
                        'nba_urgency': urgency,
                        'nba_rule_id': rule_id,
                        'nba_from_llm': False,
                        'nba_computed_at': fields.Datetime.now(),
                    })
                    return
            except (KeyError, TypeError, ValueError):
                continue

        # No rule matched — try LLM fallback
        llm_enabled = self.env['ir.config_parameter'].sudo().get_param(
            'casafolino.mail.v3_nba_llm_fallback', 'False')
        if llm_enabled in ('True', '1', 'true'):
            self._nba_llm_fallback(rec, partner, data)
        else:
            rec.write({
                'nba_text': '',
                'nba_urgency': False,
                'nba_rule_id': 0,
                'nba_from_llm': False,
                'nba_computed_at': fields.Datetime.now(),
            })

    def _build_nba_context(self, partner):
        """Build context dict for NBA rule evaluation."""
        now = fields.Datetime.now()
        today = fields.Date.context_today(self)
        Message = self.env['casafolino.mail.message']

        # Last inbound email
        last_inbound = Message.search([
            ('partner_id', '=', partner.id),
            ('direction', '=', 'inbound'),
            ('state', 'in', ('keep', 'auto_keep')),
        ], order='email_date desc', limit=1)

        # Last outbound email
        last_outbound = Message.search([
            ('partner_id', '=', partner.id),
            ('direction', '=', 'outbound'),
            ('state', 'in', ('keep', 'auto_keep')),
        ], order='email_date desc', limit=1)

        # Check if last inbound is unanswered
        last_inbound_unanswered = False
        days_since_last_inbound = 999
        if last_inbound and last_inbound.email_date:
            days_since_last_inbound = (now - last_inbound.email_date).days
            if not last_outbound or not last_outbound.email_date:
                last_inbound_unanswered = True
            elif last_outbound.email_date < last_inbound.email_date:
                last_inbound_unanswered = True

        # Last email (any direction)
        last_any = Message.search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ('keep', 'auto_keep')),
        ], order='email_date desc', limit=1)
        days_since_last_email = 999
        if last_any and last_any.email_date:
            days_since_last_email = (now - last_any.email_date).days

        # Total emails
        total_emails = Message.search_count([
            ('partner_id', '=', partner.id),
            ('state', 'in', ('keep', 'auto_keep')),
        ])

        # Open leads
        open_leads = self.env['crm.lead'].search([
            ('partner_id', '=', partner.id),
            ('active', '=', True),
            ('stage_id.is_won', '=', False),
            ('probability', '<', 100),
        ], order='create_date desc', limit=1)
        has_open_lead = bool(open_leads)
        lead_stage = ''
        days_lead_no_activity = 0
        if open_leads:
            stage_name = (open_leads.stage_id.name or '').lower().replace(' ', '_')
            lead_stage = stage_name
            # Days since last activity on lead
            last_activity = self.env['mail.activity'].search([
                ('res_model', '=', 'crm.lead'),
                ('res_id', '=', open_leads.id),
            ], order='create_date desc', limit=1)
            if last_activity and last_activity.create_date:
                days_lead_no_activity = (now - last_activity.create_date).days
            else:
                days_lead_no_activity = (now - open_leads.create_date).days

        # Overdue payments
        overdue_amount = 0.0
        try:
            overdue_invoices = self.env['account.move'].sudo().search([
                ('partner_id', '=', partner.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('invoice_date_due', '<', today),
            ])
            overdue_amount = sum(overdue_invoices.mapped('amount_residual_signed'))
        except Exception:
            pass

        # Pending orders
        pending_orders = 0
        try:
            pending_orders = self.env['sale.order'].sudo().search_count([
                ('partner_id', '=', partner.id),
                ('state', '=', 'sale'),
                ('invoice_status', '=', 'to invoice'),
            ])
        except Exception:
            pass

        # Revenue YTD
        ytd_start = today.replace(month=1, day=1)
        ytd_revenue = 0.0
        try:
            ytd_invoices = self.env['account.move'].sudo().search([
                ('partner_id', '=', partner.id),
                ('move_type', 'in', ('out_invoice', 'out_refund')),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', ytd_start),
            ])
            ytd_revenue = sum(ytd_invoices.mapped('amount_total_signed'))
        except Exception:
            pass

        # Lifetime revenue
        lifetime_revenue = 0.0
        try:
            all_invoices = self.env['account.move'].sudo().search([
                ('partner_id', '=', partner.id),
                ('move_type', 'in', ('out_invoice', 'out_refund')),
                ('state', '=', 'posted'),
            ])
            lifetime_revenue = sum(all_invoices.mapped('amount_total_signed'))
        except Exception:
            pass

        # Order count YTD
        order_count_ytd = 0
        try:
            order_count_ytd = self.env['sale.order'].sudo().search_count([
                ('partner_id', '=', partner.id),
                ('state', 'in', ('sale', 'done')),
                ('date_order', '>=', str(ytd_start)),
            ])
        except Exception:
            pass

        # Last order days
        last_order_days = None
        try:
            last_order = self.env['sale.order'].sudo().search([
                ('partner_id', '=', partner.id),
                ('state', 'in', ('sale', 'done')),
            ], order='date_order desc', limit=1)
            if last_order and last_order.date_order:
                last_order_days = (now - last_order.date_order).days
        except Exception:
            pass

        # Sentiment trend (last 5 emails)
        recent_msgs = Message.search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ('keep', 'auto_keep')),
            ('ai_sentiment', '!=', False),
        ], order='email_date desc', limit=5)
        sentiment_map = {'positive': 1, 'neutral': 0, 'negative': -1}
        sentiment_trend = 'stable'
        if len(recent_msgs) >= 3:
            scores = [sentiment_map.get(m.ai_sentiment, 0) for m in recent_msgs]
            first_half = sum(scores[:len(scores)//2]) / max(1, len(scores)//2)
            second_half = sum(scores[len(scores)//2:]) / max(1, len(scores) - len(scores)//2)
            if first_half - second_half > 0.3:
                sentiment_trend = 'improving'
            elif second_half - first_half > 0.3:
                sentiment_trend = 'declining'

        # AI fields from last inbound
        last_sentiment = last_inbound.ai_sentiment if last_inbound else None
        last_ai_urgency = last_inbound.ai_urgency if last_inbound else None
        last_ai_action_required = last_inbound.ai_action_required if last_inbound else False

        # Fair info
        met_at_fair = bool(partner.cf_fair_met) if hasattr(partner, 'cf_fair_met') else False
        fair_name = partner.cf_fair_met or '' if hasattr(partner, 'cf_fair_met') else ''
        days_since_fair = None
        if hasattr(partner, 'cf_last_contact_date') and partner.cf_last_contact_date and met_at_fair:
            days_since_fair = (today - partner.cf_last_contact_date).days

        # Contact info
        is_new_contact = (now - partner.create_date).days <= 14 if partner.create_date else False
        days_since_creation = (now - partner.create_date).days if partner.create_date else 999

        # Birthday
        days_to_birthday = None
        if hasattr(partner, 'cf_birthday') and partner.cf_birthday:
            next_bday = partner.cf_birthday.replace(year=today.year)
            if next_bday < today:
                next_bday = next_bday.replace(year=today.year + 1)
            days_to_birthday = (next_bday - today).days

        # Hotness tier from current intelligence
        intel = self.search([('partner_id', '=', partner.id)], limit=1)
        hotness_tier = intel.hotness_tier if intel else 'cold'

        return {
            'overdue_amount': overdue_amount,
            'last_inbound_unanswered': last_inbound_unanswered,
            'days_since_last_inbound': days_since_last_inbound,
            'last_sentiment': last_sentiment,
            'has_open_lead': has_open_lead,
            'lead_stage': lead_stage,
            'days_lead_no_activity': days_lead_no_activity,
            'pending_orders': pending_orders,
            'last_ai_urgency': last_ai_urgency,
            'last_ai_action_required': last_ai_action_required,
            'days_since_last_email': days_since_last_email,
            'hotness_tier': hotness_tier,
            'last_order_days': last_order_days,
            'ytd_revenue': ytd_revenue,
            'lifetime_revenue': lifetime_revenue,
            'order_count_ytd': order_count_ytd,
            'met_at_fair': met_at_fair,
            'fair_name': fair_name,
            'days_since_fair': days_since_fair,
            'is_new_contact': is_new_contact,
            'days_since_creation': days_since_creation,
            'total_emails': total_emails,
            'sentiment_trend': sentiment_trend,
            'has_phone': bool(partner.phone or partner.mobile),
            'has_linkedin': bool(getattr(partner, 'cf_linkedin', '')),
            'is_007_enriched': bool(getattr(partner, 'cf_007_enriched', False)),
            'has_gdpr_consent': bool(getattr(partner, 'cf_gdpr_consent', False)),
            'days_to_birthday': days_to_birthday,
        }

    def _nba_llm_fallback(self, rec, partner, data):
        """LLM fallback when no rule matches. Uses Groq API."""
        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'casafolino.groq_api_key', '')
        if not api_key:
            return

        prompt = (
            "Sei un assistant commerciale per CasaFolino (food B2B export italiano). "
            "Dato il contesto del partner, suggerisci la prossima azione commerciale. "
            "Rispondi con JSON: {\"text\": \"...\", \"urgency\": \"medium|low|info\"}\n\n"
            "Partner: %s\n"
            "Email totali: %d\n"
            "Ultimo contatto: %dg fa\n"
            "Fatturato YTD: €%.0f\n"
            "Lead aperto: %s (stage: %s)\n"
            "Tier: %s\n"
            "Sentiment trend: %s\n"
        ) % (
            partner.name or '?',
            data['total_emails'],
            data['days_since_last_email'],
            data['ytd_revenue'],
            'Si' if data['has_open_lead'] else 'No',
            data['lead_stage'] or '-',
            data['hotness_tier'],
            data['sentiment_trend'],
        )

        try:
            resp = req.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={
                    'Authorization': 'Bearer %s' % api_key,
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'llama-3.3-70b-versatile',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.3,
                    'max_tokens': 150,
                },
                timeout=15,
            )
            if resp.status_code != 200:
                return

            content = resp.json()['choices'][0]['message']['content']
            content = content.strip()
            if content.startswith('```'):
                content = re.sub(r'^```\w*\n?', '', content)
                content = re.sub(r'\n?```$', '', content)
                content = content.strip()

            result = json.loads(content)
            text = (result.get('text') or '')[:200]
            urgency = result.get('urgency', 'info')
            if urgency not in ('critical', 'high', 'medium', 'low', 'info'):
                urgency = 'info'

            rec.write({
                'nba_text': text,
                'nba_urgency': urgency,
                'nba_rule_id': 0,
                'nba_from_llm': True,
                'nba_computed_at': fields.Datetime.now(),
            })
        except Exception as e:
            _logger.warning("NBA LLM fallback error for partner %s: %s", partner.id, e)

    # ── Cron: rebuild top partners ───────────────────────────────────

    @api.model
    def _rebuild_top_partners(self, limit=500):
        """Cron job: rebuild intelligence for top N partners."""
        _logger.info("[intelligence] Starting rebuild for top %d partners", limit)

        # Select partners with recent email activity + open leads
        self.env.cr.execute("""
            SELECT DISTINCT p.id
            FROM res_partner p
            LEFT JOIN casafolino_mail_message m
                ON m.partner_id = p.id
                AND m.state IN ('keep', 'auto_keep')
            LEFT JOIN crm_lead l
                ON l.partner_id = p.id
                AND l.active = true
            WHERE p.active = true
              AND (m.id IS NOT NULL OR l.id IS NOT NULL)
            ORDER BY p.id
            LIMIT %s
        """, (limit,))
        partner_ids = [r[0] for r in self.env.cr.fetchall()]

        done = 0
        for pid in partner_ids:
            try:
                self._compute_for_partner(pid)
                done += 1
                if done % 100 == 0:
                    self.env.cr.commit()
                    _logger.info("[intelligence] Rebuilt %d/%d", done, len(partner_ids))
            except Exception as e:
                _logger.warning("[intelligence] Error partner %s: %s", pid, e)

        self.env.cr.commit()
        _logger.info("[intelligence] Rebuild complete: %d partners", done)
        return done
