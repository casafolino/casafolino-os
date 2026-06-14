import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class CFMailPositionFeedback(models.Model):
    _name = 'cf.mail.position.feedback'
    _description = 'Mail Position AI Feedback'
    _order = 'create_date desc'
    _rec_name = 'message_id'

    message_id = fields.Many2one(
        'casafolino.mail.message', string='Mail',
        required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one(
        'res.partner', string='Partner',
        required=True, index=True)
    ai_suggested_project_id = fields.Many2one(
        'project.project', string='Suggerito AI', ondelete='set null')
    ai_confidence_at_position = fields.Float(
        'AI confidence', digits=(3, 2))
    actual_project_id = fields.Many2one(
        'project.project', string='Posizionato su',
        required=True, ondelete='cascade')
    was_correct = fields.Boolean(
        'AI corretta', compute='_compute_was_correct', store=True, index=True)
    user_id = fields.Many2one(
        'res.users', string='Posizionato da',
        required=True, default=lambda self: self.env.user)
    user_reason = fields.Char('Motivo')

    @api.depends('ai_suggested_project_id', 'actual_project_id')
    def _compute_was_correct(self):
        for feedback in self:
            feedback.was_correct = (
                bool(feedback.ai_suggested_project_id)
                and feedback.ai_suggested_project_id == feedback.actual_project_id
            )
