from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError

ROLE_SELECTION = [
    ('commerciale', 'Commerciale'),
    ('backoffice', 'Backoffice'),
    ('produzione', 'Produzione'),
    ('logistica', 'Logistica'),
    ('etichette', 'Etichette'),
    ('amministrazione', 'Amministrazione'),
]


class CfInitiativeStage(models.Model):
    _name = 'cf.initiative.stage'
    _description = 'Fase Staffetta Iniziativa'
    _order = 'sequence, id'

    initiative_id = fields.Many2one(
        'cf.initiative', ondelete='cascade', required=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    role = fields.Selection(ROLE_SELECTION, string='Ruolo')
    user_id = fields.Many2one('res.users', string='Owner')
    state = fields.Selection([
        ('pending', 'In attesa'),
        ('active', 'Attiva'),
        ('done', 'Completata'),
        ('skipped', 'Saltata'),
    ], default='pending', string='Stato')
    date_start = fields.Datetime(string='Inizio')
    date_done = fields.Datetime(string='Completata il')
    feedback = fields.Text(string='Feedback')
    require_feedback = fields.Boolean(default=False, string='Feedback obbligatorio')
    optional = fields.Boolean(default=False)
    require_shipment = fields.Boolean(default=False, string='Richiede spedizione')
    days_in_stage = fields.Integer(
        compute='_compute_days_in_stage', string='Giorni in fase',
    )

    def _compute_days_in_stage(self):
        now = datetime.now()
        for stage in self:
            if stage.state == 'active' and stage.date_start:
                stage.days_in_stage = (now - stage.date_start).days
            else:
                stage.days_in_stage = 0

    def action_complete_stage(self):
        self.ensure_one()
        if self.state != 'active':
            raise UserError(_('Solo la fase attiva può essere chiusa.'))

        open_tasks = self.env['cf.todo'].search([('stage_id', '=', self.id), ('done', '=', False)])
        if open_tasks:
            raise UserError(
                _('Impossibile chiudere la fase: %d task ancora aperti.\n%s') % (
                    len(open_tasks), '\n'.join('• ' + t.name for t in open_tasks))
            )

        if self.require_feedback and not (self.feedback or '').strip():
            raise UserError(
                _('Questa fase richiede un feedback prima di essere chiusa. '
                  'Compila il campo "Feedback".')
            )

        self.write({'state': 'done', 'date_done': fields.Datetime.now()})

        initiative = self.initiative_id
        next_stage = initiative.stage_ids.filtered(
            lambda s: s.state == 'pending' and s.sequence > self.sequence
        ).sorted('sequence')[:1]

        if next_stage:
            next_stage.write({'state': 'active', 'date_start': fields.Datetime.now()})
            # Genera task prossima fase dal template
            template_stage = initiative.template_id.stage_line_ids.filtered(
                lambda ts: ts.sequence == next_stage.sequence
            )[:1]
            if template_stage and template_stage.task_names:
                for line in template_stage.task_names.strip().split('\n'):
                    name = line.strip()
                    if name:
                        self.env['cf.todo'].create({
                            'name': name,
                            'initiative_id': initiative.id,
                            'stage_id': next_stage.id,
                            'assigned_user_id': next_stage.user_id.id if next_stage.user_id else False,
                        })
            self._send_baton_notification(next_stage)
            initiative.message_post(
                body=_('Testimone passato da <b>%s</b> a <b>%s</b> — fase: <b>%s</b>.%s') % (
                    self.user_id.name or '?',
                    next_stage.user_id.name or '?',
                    next_stage.name,
                    (' Feedback: ' + self.feedback) if self.feedback else '',
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
        else:
            initiative.action_done()
            initiative.message_post(
                body=_('Progetto completato. Ultima fase: <b>%s</b>.%s') % (
                    self.name,
                    (' Feedback: ' + self.feedback) if self.feedback else '',
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

    def action_skip_stage(self):
        self.ensure_one()
        if not self.optional:
            raise UserError(_('Solo le fasi opzionali possono essere saltate.'))
        if self.state not in ('pending',):
            raise UserError(_('Solo fasi in attesa possono essere saltate.'))
        self.write({'state': 'skipped'})
        self.initiative_id.message_post(
            body=_('Fase saltata: <b>%s</b>') % self.name,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

    def _send_baton_notification(self, stage):
        if not stage.user_id or not stage.user_id.email:
            return
        template = self.env.ref(
            'casafolino_initiative.mail_template_baton_handoff',
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(stage.id, force_send=False)
