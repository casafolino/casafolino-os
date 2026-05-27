from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CfExportSampleStage(models.Model):
    _name = 'cf.export.sample.stage'
    _description = 'Stage Campionatura'
    _order = 'sequence asc'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(default=False)
    is_closed = fields.Boolean(default=False)


class CfExportSample(models.Model):
    _name = 'cf.export.sample'
    _description = 'Campionatura Export'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'reference'

    reference = fields.Char(
        string='Riferimento',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('cf.export.sample') or 'CAMP-NEW',
    )
    lead_id = fields.Many2one('crm.lead', string='Trattativa', ondelete='set null', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True, tracking=True, index=True)
    project_id = fields.Many2one('project.project', string='Dossier', tracking=True, index=True)
    user_id = fields.Many2one(
        'res.users',
        string='Responsabile',
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
    )
    stage_id = fields.Many2one(
        'cf.export.sample.stage',
        string='Stage',
        default=lambda self: self.env['cf.export.sample.stage'].search([], limit=1),
        tracking=True,
        group_expand='_read_group_stage_ids',
    )
    state = fields.Selection([
        ('draft', 'Da Preparare'),
        ('prepared', 'Preparata'),
        ('sent', 'Spedita'),
        ('received', 'Ricevuta'),
        ('feedback_ok', 'Feedback Positivo'),
        ('feedback_ko', 'Feedback Negativo'),
        ('no_feedback', 'Nessun Feedback'),
    ], string='Stato', default='draft', tracking=True)
    priority = fields.Selection([
        ('0', 'Normale'),
        ('1', 'Alta'),
        ('2', 'Urgente'),
    ], string='Priorità', default='0', tracking=True)
    requested_by = fields.Char(string='Richiesta da')
    request_date = fields.Date(string='Data richiesta', default=fields.Date.context_today, tracking=True)
    promised_date = fields.Date(string='Data promessa', tracking=True)
    preparation_deadline = fields.Date(string='Deadline preparazione', tracking=True)
    product_ids = fields.Many2many('product.template', string='Prodotti')
    line_ids = fields.One2many('cf.export.sample.line', 'sample_id', string='Righe campionatura')
    line_count = fields.Integer(compute='_compute_line_metrics', string='Righe')
    total_quantity = fields.Float(compute='_compute_line_metrics', string='Quantità totale')
    product_summary = fields.Char(compute='_compute_line_metrics', string='Sintesi prodotti')
    prepared_by_id = fields.Many2one('res.users', string='Preparata da', tracking=True)
    prepared_date = fields.Date(string='Data preparazione', tracking=True)
    carrier_name = fields.Char(string='Corriere', tracking=True)
    date_sent = fields.Date(string='Data Spedizione', tracking=True)
    date_delivered = fields.Date(string='Data consegna', tracking=True)
    date_feedback_expected = fields.Date(string='Feedback Atteso')
    tracking_number = fields.Char(string='Tracking')
    shipping_cost = fields.Monetary(string='Costo spedizione')
    currency_id = fields.Many2one(
        'res.currency',
        string='Valuta',
        default=lambda self: self.env.company.currency_id,
    )
    commercial_goal = fields.Selection([
        ('first_contact', 'Primo assaggio'),
        ('assortment', 'Scelta assortimento'),
        ('private_label', 'Private label'),
        ('quality_check', 'Controllo qualita cliente'),
        ('repeat', 'Secondo invio / integrazione'),
    ], string='Obiettivo commerciale', tracking=True)
    customer_requirements = fields.Text(string='Richieste cliente')
    preparation_notes = fields.Text(string='Note preparazione/logistica')
    sale_order_id = fields.Many2one('sale.order', string='Ordine campionatura', copy=False, tracking=True)
    sale_order_state = fields.Selection(related='sale_order_id.state', string='Stato ordine')
    picking_count = fields.Integer(compute='_compute_order_metrics', string='Delivery')
    feedback_notes = fields.Text(string='Note Feedback')
    feedback_score = fields.Selection([
        ('1', '⭐'),
        ('2', '⭐⭐'),
        ('3', '⭐⭐⭐'),
        ('4', '⭐⭐⭐⭐'),
        ('5', '⭐⭐⭐⭐⭐'),
    ], string='Valutazione')

    @api.depends('line_ids', 'line_ids.quantity', 'line_ids.product_tmpl_id', 'product_ids')
    def _compute_line_metrics(self):
        for sample in self:
            sample.line_count = len(sample.line_ids)
            sample.total_quantity = sum(sample.line_ids.mapped('quantity'))
            products = sample.line_ids.mapped('product_tmpl_id') or sample.product_ids
            sample.product_summary = ', '.join(products[:3].mapped('name'))
            if len(products) > 3:
                sample.product_summary = _('%s + altri %s') % (
                    sample.product_summary,
                    len(products) - 3,
                )

    @api.depends('sale_order_id')
    def _compute_order_metrics(self):
        for sample in self:
            if sample.sale_order_id and 'picking_ids' in sample.sale_order_id._fields:
                sample.picking_count = len(sample.sale_order_id.picking_ids)
            else:
                sample.picking_count = 0

    @api.constrains('promised_date', 'request_date', 'date_sent', 'date_delivered')
    def _check_sample_dates(self):
        for sample in self:
            if sample.promised_date and sample.request_date and sample.promised_date < sample.request_date:
                raise ValidationError(_('La data promessa non puo essere precedente alla richiesta.'))
            if sample.date_delivered and sample.date_sent and sample.date_delivered < sample.date_sent:
                raise ValidationError(_('La data consegna non puo essere precedente alla spedizione.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            lead_id = vals.get('lead_id')
            if lead_id and not vals.get('partner_id'):
                lead = self.env['crm.lead'].browse(lead_id)
                vals['partner_id'] = lead.partner_id.id
            if lead_id and not vals.get('project_id'):
                lead = self.env['crm.lead'].browse(lead_id)
                vals['project_id'] = lead.cf_project_id.id if getattr(lead, 'cf_project_id', False) else False
            if not vals.get('partner_id') and vals.get('project_id'):
                project = self.env['project.project'].browse(vals['project_id'])
                vals['partner_id'] = project.partner_id.id
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('lead_id') and not vals.get('partner_id'):
            lead = self.env['crm.lead'].browse(vals['lead_id'])
            vals = dict(vals, partner_id=lead.partner_id.id)
        return super().write(vals)

    def _stage(self, xmlid):
        return self.env.ref('casafolino_crm_export.%s' % xmlid, raise_if_not_found=False)

    def _set_stage(self, state, xmlid):
        stage = self._stage(xmlid)
        values = {'state': state}
        if stage:
            values['stage_id'] = stage.id
        self.write(values)

    def _require_content(self):
        for sample in self:
            if not sample.line_ids and not sample.product_ids:
                raise UserError(_('Aggiungi almeno un prodotto o una riga campione prima di avanzare.'))

    def _prepare_sale_order_lines(self):
        self.ensure_one()
        commands = []
        for line in self.line_ids:
            product = line.product_id or line.product_tmpl_id.product_variant_id
            if not product:
                raise UserError(_('Il prodotto %s non ha una variante vendibile.') % line.product_tmpl_id.display_name)
            description = line.notes or product.display_name
            if line.format_note:
                description = '%s\nFormato: %s' % (description, line.format_note)
            if line.lot_note:
                description = '%s\nLotto/shelf-life: %s' % (description, line.lot_note)
            commands.append((0, 0, {
                'product_id': product.id,
                'name': description,
                'product_uom_qty': line.quantity or 1.0,
                'product_uom': (line.uom_id or product.uom_id).id,
                'price_unit': 0.0,
            }))
        if not commands:
            for product_tmpl in self.product_ids:
                product = product_tmpl.product_variant_id
                if not product:
                    raise UserError(_('Il prodotto %s non ha una variante vendibile.') % product_tmpl.display_name)
                commands.append((0, 0, {
                    'product_id': product.id,
                    'name': product.display_name,
                    'product_uom_qty': 1.0,
                    'product_uom': product.uom_id.id,
                    'price_unit': 0.0,
                }))
        return commands

    def action_create_sample_order(self):
        self.ensure_one()
        self._require_content()
        if self.sale_order_id:
            return self.action_view_sale_order()
        order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'user_id': self.user_id.id or self.env.user.id,
            'origin': self.reference,
            'client_order_ref': self.requested_by or self.reference,
            'note': self.customer_requirements or self.preparation_notes or False,
            'cf_project_id': self.project_id.id if self.project_id else False,
            'cf_is_sample_order': True,
            'cf_sample_id': self.id,
            'order_line': self._prepare_sale_order_lines(),
        })
        self.sale_order_id = order.id
        self.message_post(body=_('Creato ordine campionatura %s.') % order.display_name)
        return self.action_view_sale_order()

    def action_send_to_warehouse(self):
        for sample in self:
            if not sample.sale_order_id:
                sample.action_create_sample_order()
            if sample.sale_order_id.state in ('draft', 'sent'):
                sample.sale_order_id.action_confirm()
            sample.write({
                'state': 'prepared',
                'prepared_by_id': sample.prepared_by_id.id or self.env.user.id,
                'prepared_date': sample.prepared_date or fields.Date.context_today(sample),
            })
            stage = sample._stage('sample_stage_preparation')
            if stage:
                sample.stage_id = stage.id

    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            return self.action_create_sample_order()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ordine campionatura'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_pickings(self):
        self.ensure_one()
        if not self.sale_order_id or 'picking_ids' not in self.sale_order_id._fields:
            return False
        pickings = self.sale_order_id.picking_ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Delivery campionatura'),
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', pickings.ids)],
        }

    def action_prepare(self):
        self._require_content()
        self.write({
            'state': 'prepared',
            'prepared_by_id': self.env.user.id,
            'prepared_date': fields.Date.context_today(self),
            'stage_id': self._stage('sample_stage_preparation').id if self._stage('sample_stage_preparation') else False,
        })

    def action_send(self):
        self._require_content()
        for sample in self:
            if not sample.date_sent:
                sample.date_sent = fields.Date.context_today(sample)
            if not sample.tracking_number:
                raise UserError(_('Inserisci il tracking prima di segnare la campionatura come spedita.'))
            sample._set_stage('sent', 'sample_stage_sent')

    def action_mark_delivered(self):
        for sample in self:
            sample.write({'date_delivered': sample.date_delivered or fields.Date.context_today(sample)})
            sample._set_stage('received', 'sample_stage_delivered')

    def action_feedback_ok(self):
        for sample in self:
            if not sample.feedback_score:
                raise UserError(_('Inserisci una valutazione prima di chiudere con feedback positivo.'))
            sample._set_stage('feedback_ok', 'sample_stage_ok')

    def action_feedback_ko(self):
        for sample in self:
            if not sample.feedback_notes:
                raise UserError(_('Inserisci le note feedback prima di chiudere con feedback negativo.'))
            sample._set_stage('feedback_ko', 'sample_stage_ko')

    def action_no_feedback(self):
        self._set_stage('no_feedback', 'sample_stage_ko')

    def action_reset_draft(self):
        self._set_stage('draft', 'sample_stage_request')

    def action_schedule_feedback_activity(self):
        todo_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for sample in self:
            if not todo_type:
                continue
            sample.activity_schedule(
                todo_type.id,
                date_deadline=sample.date_feedback_expected or fields.Date.context_today(sample),
                user_id=sample.user_id.id or self.env.user.id,
                summary=_('Richiamare cliente per feedback campionatura'),
                note=sample.reference,
            )

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        return self.env['cf.export.sample.stage'].search([])


class CfExportSampleLine(models.Model):
    _name = 'cf.export.sample.line'
    _description = 'Riga Campionatura Export'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    sample_id = fields.Many2one('cf.export.sample', required=True, ondelete='cascade')
    product_tmpl_id = fields.Many2one('product.template', string='Prodotto', required=True)
    product_id = fields.Many2one(
        'product.product',
        string='Variante',
        domain="[('product_tmpl_id', '=', product_tmpl_id)]",
    )
    quantity = fields.Float(string='Quantità', default=1.0, required=True)
    uom_id = fields.Many2one('uom.uom', string='Unita di misura')
    format_note = fields.Char(string='Formato / packaging')
    lot_note = fields.Char(string='Lotto / shelf life')
    notes = fields.Char(string='Note')

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        for line in self:
            if line.product_tmpl_id:
                line.uom_id = line.product_tmpl_id.uom_id
