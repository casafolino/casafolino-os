from odoo import api, fields, models


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    cf_tag_ids = fields.Many2many(
        'casafolino.mail.template.tag',
        string='Tag CasaFolino',
    )
    cf_is_fair_template = fields.Boolean(
        string='Template Fiera',
        compute='_compute_is_fair_template', store=True,
    )
    cf_owner_id = fields.Many2one(
        'res.users',
        string='Proprietario',
        default=lambda self: self.env.user,
    )
    cf_use_count = fields.Integer(
        string='Numero invii',
        compute='_compute_use_count',
    )

    @api.depends('cf_tag_ids', 'cf_tag_ids.is_fair_tag')
    def _compute_is_fair_template(self):
        for t in self:
            t.cf_is_fair_template = any(tag.is_fair_tag for tag in t.cf_tag_ids)

    def _compute_use_count(self):
        for t in self:
            count = 0
            if t.id:
                self.env.cr.execute("""
                    SELECT COUNT(*) FROM mailing_mailing
                    WHERE body_html IS NOT NULL
                      AND subject = %s
                """, (t.subject or '',))
                count = self.env.cr.fetchone()[0] or 0
            t.cf_use_count = count

    def action_send_test_email(self):
        """Open compose wizard to send test email using this template."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invia Test — %s' % self.name,
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_template_id': self.id,
                'default_composition_mode': 'comment',
                'default_model': self.model_id.model if self.model_id else 'res.partner',
            },
        }

    def action_duplicate_template(self):
        """Duplicate this template with '(Copy)' suffix."""
        self.ensure_one()
        new = self.copy({'name': '%s (Copy)' % self.name})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.template',
            'view_mode': 'form',
            'res_id': new.id,
        }

    def action_open_snippet_picker(self):
        """Open snippet library to pick and insert."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Libreria Snippet',
            'res_model': 'casafolino.mail.snippet',
            'view_mode': 'list',
            'target': 'new',
            'domain': [('is_active', '=', True)],
        }
