import json
import logging
import math

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CasafolinoPartnerIntelligence(models.Model):
    _name = 'casafolino.partner.intelligence'
    _description = 'Intelligence partner — Mail V3'
    _order = 'hotness_score desc'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True,
                                  index=True, ondelete='cascade')
    hotness_score = fields.Integer('Hotness Score', default=0, index=True)
    hotness_tier = fields.Selection([
        ('hot', '\U0001f525 Hot'),
        ('warm', '\U0001f536 Warm'),
        ('active', '\U0001f4bc Active'),
        ('cold', '\U0001f9ca Cold'),
        ('dormant', '\u26ab Dormant'),
    ], string='Hotness Tier', compute='_compute_hotness_tier', store=True)
    hotness_components_json = fields.Text('Componenti Hotness (JSON)')
    last_rebuild_at = fields.Datetime('Ultimo rebuild')
    pinned_hot = fields.Boolean('Pinnato Hot', default=False)
    pinned_ignore = fields.Boolean('Pinnato Ignora', default=False)

    # F3 stubs
    nba_text = fields.Char('NBA Text', default='')
    nba_urgency = fields.Selection([
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('info', 'Info'),
    ], string='NBA Urgency', default=False)
    nba_rule_id = fields.Integer('NBA Rule ID', default=0)
    nba_from_llm = fields.Boolean('NBA da LLM', default=False)

    _sql_constraints = [
        ('partner_unique', 'UNIQUE(partner_id)',
         'Un solo record intelligence per partner'),
    ]

    @api.depends('hotness_score')
    def _compute_hotness_tier(self):
        for rec in self:
            s = rec.hotness_score or 0
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
        """Calcola e salva intelligence per un partner."""
        partner = self.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return

        c_revenue = self._compute_component_revenue(partner)
        c_activity = self._compute_component_activity(partner)
        c_pipeline = self._compute_component_pipeline(partner)
        c_freshness = self._compute_component_freshness(partner)
        c_strategic = self._compute_component_strategic_boost(partner)

        score = round(
            0.30 * c_revenue
            + 0.25 * c_activity
            + 0.20 * c_pipeline
            + 0.15 * c_freshness
            + 0.10 * c_strategic
        )
        score = max(0, min(100, score))

        components = {
            'revenue': c_revenue,
            'activity': c_activity,
            'pipeline': c_pipeline,
            'freshness': c_freshness,
            'strategic_boost': c_strategic,
        }

        vals = {
            'hotness_score': score,
            'hotness_components_json': json.dumps(components),
            'last_rebuild_at': fields.Datetime.now(),
        }

        intel = self.search([('partner_id', '=', partner_id)], limit=1)
        if intel:
            if intel.pinned_ignore:
                return intel
            if intel.pinned_hot:
                vals['hotness_score'] = max(score, 80)
            intel.write(vals)
        else:
            vals['partner_id'] = partner_id
            intel = self.create(vals)

        _logger.debug('[mail v3] Intelligence: partner %s score=%s', partner_id, score)
        return intel

    def _compute_component_revenue(self, partner):
        """Scala log fatturato 12 mesi da account.move confirmed."""
        from datetime import timedelta
        cutoff = fields.Date.today() - timedelta(days=365)

        # Cerchiamo su company partner o partner diretto
        partner_ids = [partner.id]
        if partner.parent_id:
            partner_ids.append(partner.parent_id.id)
        # Includi anche figli (contatti dell'azienda)
        if partner.is_company:
            children = self.env['res.partner'].search([('parent_id', '=', partner.id)])
            partner_ids.extend(children.ids)

        try:
            invoices = self.env['account.move'].sudo().search([
                ('partner_id', 'in', partner_ids),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', cutoff),
            ])
            total = sum(inv.amount_untaxed_signed for inv in invoices)
        except Exception:
            total = 0

        if total <= 0:
            return 0
        # Scala log: 1K→30, 10K→60, 50K→90, 100K+→100
        if total >= 100000:
            return 100
        return min(100, int(30 * math.log10(max(total, 1)) - 60))

    def _compute_component_activity(self, partner):
        """Count eventi 90gg: email + ordini + attività."""
        from datetime import timedelta
        cutoff = fields.Datetime.now() - timedelta(days=90)

        partner_ids = [partner.id]
        if partner.is_company:
            children = self.env['res.partner'].search([('parent_id', '=', partner.id)])
            partner_ids.extend(children.ids)

        count = 0
        # Email keep
        count += self.env['casafolino.mail.message'].search_count([
            ('partner_id', 'in', partner_ids),
            ('state', 'in', ['keep', 'auto_keep']),
            ('email_date', '>=', cutoff),
        ])
        # Ordini vendita
        try:
            count += self.env['sale.order'].sudo().search_count([
                ('partner_id', 'in', partner_ids),
                ('date_order', '>=', cutoff),
            ])
        except Exception:
            pass
        # Attività
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
        elif count <= 5:
            return 30
        elif count <= 15:
            return 60
        elif count <= 30:
            return 80
        else:
            return 100

    def _compute_component_pipeline(self, partner):
        """Max(stage_weight × probability) su crm.lead open."""
        partner_ids = [partner.id]
        if partner.is_company:
            children = self.env['res.partner'].search([('parent_id', '=', partner.id)])
            partner_ids.extend(children.ids)

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

        # Stage weight mapping
        stage_weights = {
            'new': 10, 'qualified': 30, 'proposition': 70,
            'proposal': 70, 'negotiation': 85, 'won': 100,
        }

        max_val = 0
        for lead in leads:
            stage_name = (lead.stage_id.name or '').lower()
            seq = lead.stage_id.sequence or 0

            # Match by name
            weight = 0
            for key, w in stage_weights.items():
                if key in stage_name:
                    weight = w
                    break

            # Fallback by sequence
            if not weight:
                if seq <= 1:
                    weight = 10
                elif seq <= 3:
                    weight = 30
                elif seq <= 5:
                    weight = 70
                elif seq <= 7:
                    weight = 85
                else:
                    weight = 100

            prob = (lead.probability or 0) / 100
            val = weight * prob
            if val > max_val:
                max_val = val

        return min(100, int(max_val))

    def _compute_component_freshness(self, partner):
        """Interpolazione giorni dall'ultima interazione."""
        from datetime import timedelta

        partner_ids = [partner.id]
        if partner.is_company:
            children = self.env['res.partner'].search([('parent_id', '=', partner.id)])
            partner_ids.extend(children.ids)

        last_msg = self.env['casafolino.mail.message'].search([
            ('partner_id', 'in', partner_ids),
            ('state', 'in', ['keep', 'auto_keep']),
        ], order='email_date desc', limit=1)

        if not last_msg or not last_msg.email_date:
            return 5

        days = (fields.Datetime.now() - last_msg.email_date).days

        if days <= 0:
            return 100
        elif days <= 7:
            return 80
        elif days <= 30:
            return 50
        elif days <= 90:
            return 20
        elif days <= 180:
            return 10
        else:
            return 5

    def _compute_component_strategic_boost(self, partner):
        """Tag-based: GDO/DACH/ExportVIP→100, Prospect Qualificato→70, else→0."""
        tags = set()

        # category_id tags (standard Odoo)
        if partner.category_id:
            for cat in partner.category_id:
                tags.add((cat.name or '').lower())

        # cf_tag_ids (custom CasaFolino)
        if hasattr(partner, 'cf_tag_ids') and partner.cf_tag_ids:
            for tag in partner.cf_tag_ids:
                tags.add((tag.name or '').lower())

        # Parent company tags too
        if partner.parent_id:
            if partner.parent_id.category_id:
                for cat in partner.parent_id.category_id:
                    tags.add((cat.name or '').lower())

        # Check strategic keywords
        strategic_high = {'gdo', 'dach', 'exportvip', 'export vip', 'export_vip',
                          'key account', 'strategic', 'strategico'}
        strategic_medium = {'prospect qualificato', 'prospect qualif', 'qualified prospect',
                            'prospect'}

        for tag in tags:
            for kw in strategic_high:
                if kw in tag:
                    return 100
        for tag in tags:
            for kw in strategic_medium:
                if kw in tag:
                    return 70

        return 0

    @api.model
    def _rebuild_top_partners(self, limit=500):
        """Ricostruisce intelligence per top N partner più attivi."""
        _logger.info('[mail v3] Intelligence rebuild: start (limit=%s)', limit)

        # Partner con email keep, ordinati per attività recente
        self.env.cr.execute("""
            SELECT DISTINCT partner_id
            FROM casafolino_mail_message
            WHERE partner_id IS NOT NULL
              AND state IN ('keep', 'auto_keep')
            ORDER BY partner_id
            LIMIT %s
        """, (limit,))
        partner_ids = [r[0] for r in self.env.cr.fetchall()]

        # Aggiungi partner con lead aperti
        try:
            leads = self.env['crm.lead'].sudo().search([
                ('active', '=', True),
                ('partner_id', '!=', False),
                ('stage_id.is_won', '=', False),
            ])
            lead_partner_ids = leads.mapped('partner_id').ids
            partner_ids = list(set(partner_ids + lead_partner_ids))[:limit]
        except Exception:
            pass

        count = 0
        for pid in partner_ids:
            try:
                self._compute_for_partner(pid)
                count += 1
            except Exception as e:
                _logger.warning('[mail v3] Intelligence fail partner %s: %s', pid, e)

            if count % 100 == 0:
                self.env.cr.commit()
                _logger.info('[mail v3] Intelligence progress: %s/%s', count, len(partner_ids))

        self.env.cr.commit()
        _logger.info('[mail v3] Intelligence rebuild: done (%s partners)', count)

    def _compute_nba_for_partner(self):
        """F3 stub — Next Best Action."""
        pass
