from datetime import timedelta

from odoo import _, api, fields, models


class CfInitiativeWizard(models.TransientModel):
    _name = 'cf.initiative.wizard'
    _description = 'Wizard Creazione Iniziativa'

    step = fields.Selection([
        ('1_family', 'Famiglia'),
        ('2_variant', 'Variante'),
        ('3_parent', 'Padre'),
        ('4_config', 'Configurazione'),
    ], default='1_family')

    # Step 1
    family_id = fields.Many2one('cf.initiative.family',
                                domain="[('active', '=', True)]")
    # Step 2
    variant_id = fields.Many2one('cf.initiative.variant',
                                 domain="[('family_id', '=', family_id)]")
    # Step 3
    parent_id = fields.Many2one('cf.initiative', string='Iniziativa Madre')
    # Step 4
    name = fields.Char(string='Nome Iniziativa')
    partner_id = fields.Many2one('res.partner', string='Cliente/Partner')
    user_id = fields.Many2one('res.users', string='Owner',
                              default=lambda self: self.env.user)
    date_start = fields.Date(string='Data Inizio',
                             default=fields.Date.context_today)
    date_end = fields.Date(string='Data Fine')
    budget = fields.Monetary()
    currency_id = fields.Many2one('res.currency',
                                  default=lambda self: self.env.company.currency_id)
    tag_ids = fields.Many2many('cf.initiative.tag', string='Tag aggiuntivi')

    def action_next(self):
        self.ensure_one()
        step_flow = {
            '1_family': '2_variant',
            '2_variant': '3_parent',
            '3_parent': '4_config',
        }
        if self.step in step_flow:
            self.step = step_flow[self.step]
        return self._reopen()

    def action_prev(self):
        self.ensure_one()
        step_flow = {
            '2_variant': '1_family',
            '3_parent': '2_variant',
            '4_config': '3_parent',
        }
        if self.step in step_flow:
            self.step = step_flow[self.step]
        return self._reopen()

    def action_create(self):
        self.ensure_one()
        # Collect tags: wizard tags + parent tags
        tag_ids = self.tag_ids.ids
        if self.parent_id and self.parent_id.tag_ids:
            tag_ids = list(set(tag_ids + self.parent_id.tag_ids.ids))

        initiative = self.env['cf.initiative'].create({
            'name': self.name or _('New'),
            'family_id': self.family_id.id,
            'variant_id': self.variant_id.id,
            'parent_id': self.parent_id.id if self.parent_id else False,
            'user_id': self.user_id.id,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'budget': self.budget,
            'tag_ids': [(6, 0, tag_ids)],
        })

        # Populate atom lines from template
        template = self.env['cf.initiative.template'].search([
            ('family_id', '=', self.family_id.id),
            ('variant_id', '=', self.variant_id.id),
        ], limit=1)

        if template and template.atom_ids:
            lines = []
            for seq, atom in enumerate(template.atom_ids, start=1):
                deadline = False
                if self.date_start and atom.default_duration_days:
                    deadline = self.date_start + timedelta(days=atom.default_duration_days)
                lines.append({
                    'initiative_id': initiative.id,
                    'atom_id': atom.id,
                    'user_id': atom.default_user_id.id if atom.default_user_id else False,
                    'date_deadline': deadline,
                    'sequence': seq * 10,
                    'state': 'todo',
                })
            self.env['cf.initiative.atom.line'].create(lines)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cf.initiative',
            'res_id': initiative.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cf.initiative.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
