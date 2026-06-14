import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class IntelligenceFeedback(models.Model):
    _name = 'casafolino.partner.intelligence.feedback'
    _description = 'User feedback for hotness/NBA calibration'
    _order = 'date desc'

    partner_id = fields.Many2one('res.partner', required=True, index=True,
                                  ondelete='cascade')
    user_id = fields.Many2one('res.users', required=True,
                               default=lambda self: self.env.user)
    action_type = fields.Selection([
        ('pinned_hot', 'Pinned hot'),
        ('pinned_ignore', 'Pinned ignore'),
        ('nba_useful', 'NBA utile'),
        ('nba_dismissed', 'NBA ignorato'),
        ('manual_lead_created', 'Lead creato manualmente'),
        ('manual_close', 'Chiuso manualmente'),
    ], required=True, index=True)
    hotness_at_action = fields.Integer('Hotness al momento')
    nba_text_at_action = fields.Char('NBA al momento')
    nba_rule_id = fields.Integer('NBA rule ID')
    context_json = fields.Text('Contesto JSON')
    date = fields.Datetime(default=fields.Datetime.now, index=True)

    @staticmethod
    def _log_feedback(env, partner_id, action_type, extra=None):
        """Helper to create feedback record from anywhere."""
        vals = {
            'partner_id': partner_id,
            'action_type': action_type,
        }
        # Enrich with current intelligence data
        intel = env['casafolino.partner.intelligence'].search([
            ('partner_id', '=', partner_id)
        ], limit=1)
        if intel:
            vals['hotness_at_action'] = intel.hotness_score
            vals['nba_text_at_action'] = (intel.nba_text or '')[:255]
            vals['nba_rule_id'] = intel.nba_rule_id or 0
        if extra:
            import json
            vals['context_json'] = json.dumps(extra)
        try:
            env['casafolino.partner.intelligence.feedback'].create(vals)
        except Exception as e:
            _logger.warning('[mail v3] Feedback log error: %s', e)
