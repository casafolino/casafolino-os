from odoo import _, api, fields, models

ROLE_SELECTION = [
    ('commerciale', 'Commerciale'),
    ('backoffice', 'Backoffice'),
    ('produzione', 'Produzione'),
    ('logistica', 'Logistica'),
    ('etichette', 'Etichette'),
    ('amministrazione', 'Amministrazione'),
]


class CfInitiativeCreateWizard(models.TransientModel):
    _name = 'cf.initiative.create.wizard'
    _description = 'Crea progetto da template'

    partner_id = fields.Many2one('res.partner', required=True, string='Cliente')
    template_id = fields.Many2one('cf.initiative.template', required=True, string='Template')
    parent_id = fields.Many2one(
        'cf.initiative', string='Progetto padre',
        help='Solo per micro-progetti',
    )
    date_deadline = fields.Date(string='Scadenza')
    line_ids = fields.One2many('cf.initiative.create.wizard.line', 'wizard_id', string='Fasi')

    @api.onchange('template_id')
    def _onchange_template(self):
        lines = []
        for tpl_stage in self.template_id.stage_line_ids:
            lines.append((0, 0, {
                'sequence': tpl_stage.sequence,
                'name': tpl_stage.name,
                'role': tpl_stage.role,
                'user_id': tpl_stage.default_user_id.id,
                'include': True,
                'optional': tpl_stage.optional,
                'require_feedback': tpl_stage.require_feedback,
                'require_shipment': tpl_stage.require_shipment,
                'task_names': tpl_stage.task_names,
            }))
        self.line_ids = lines

    def action_confirm(self):
        self.ensure_one()
        initiative = self.env['cf.initiative'].create({
            'name': (self.template_id.name + ' — ' + self.partner_id.name),
            'partner_id': self.partner_id.id,
            'template_id': self.template_id.id,
            'parent_id': self.parent_id.id if self.parent_id else False,
            'date_deadline': self.date_deadline,
            'family_id': self._get_default_family(),
            'variant_id': self._get_default_variant(),
            'user_id': self.env.uid,
        })

        first_active = None
        for line in self.line_ids.sorted('sequence'):
            state = 'skipped' if not line.include else 'pending'
            stage = self.env['cf.initiative.stage'].create({
                'initiative_id': initiative.id,
                'sequence': line.sequence,
                'name': line.name,
                'role': line.role,
                'user_id': line.user_id.id if line.user_id else False,
                'state': state,
                'require_feedback': line.require_feedback,
                'optional': line.optional,
                'require_shipment': line.require_shipment,
            })
            if state == 'pending' and not first_active:
                first_active = stage

        if first_active:
            first_active.write({'state': 'active', 'date_start': fields.Datetime.now()})
            self._generate_tasks(first_active)
            self._send_notification(first_active, initiative)

        initiative.action_start()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cf.initiative',
            'res_id': initiative.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _get_default_family(self):
        fam = self.env['cf.initiative.family'].search([], limit=1)
        return fam.id if fam else False

    def _get_default_variant(self):
        fam_id = self._get_default_family()
        if fam_id:
            var = self.env['cf.initiative.variant'].search(
                [('family_id', '=', fam_id)], limit=1)
        else:
            var = self.env['cf.initiative.variant'].search([], limit=1)
        return var.id if var else False

    def _generate_tasks(self, stage):
        if not stage.task_names:
            return
        initiative = stage.initiative_id
        for line in stage.task_names.strip().split('\n'):
            name = line.strip()
            if not name:
                continue
            self.env['cf.todo'].create({
                'name': name,
                'initiative_id': initiative.id,
                'stage_id': stage.id,
                'assigned_user_id': stage.user_id.id if stage.user_id else False,
            })

    def _send_notification(self, stage, initiative):
        if not stage.user_id or not stage.user_id.email:
            return
        template = self.env.ref(
            'casafolino_initiative.mail_template_baton_handoff',
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(stage.id, force_send=False)


class CfInitiativeCreateWizardLine(models.TransientModel):
    _name = 'cf.initiative.create.wizard.line'
    _description = 'Riga Fasi Wizard Crea Progetto'
    _order = 'sequence'

    wizard_id = fields.Many2one('cf.initiative.create.wizard', ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, string='Fase')
    role = fields.Selection(ROLE_SELECTION, string='Ruolo')
    user_id = fields.Many2one('res.users', string='Assegnatario')
    include = fields.Boolean(default=True, string='Includi')
    optional = fields.Boolean(default=False)
    require_feedback = fields.Boolean(default=False, string='Feedback obbligatorio')
    require_shipment = fields.Boolean(default=False, string='Richiede spedizione')
    task_names = fields.Text(string='Task predefiniti')
