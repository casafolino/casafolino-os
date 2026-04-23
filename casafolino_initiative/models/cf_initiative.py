from odoo import _, api, fields, models


class CfInitiative(models.Model):
    _name = 'cf.initiative'
    _description = 'Iniziativa CasaFolino'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code desc'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(readonly=True, copy=False, default='New')

    # Classificazione
    family_id = fields.Many2one('cf.initiative.family', required=True, tracking=True)
    variant_id = fields.Many2one('cf.initiative.variant', required=True,
                                 domain="[('family_id', '=', family_id)]", tracking=True)

    # Gerarchia
    parent_id = fields.Many2one('cf.initiative', ondelete='set null', tracking=True,
                                string='Iniziativa Madre')
    child_ids = fields.One2many('cf.initiative', 'parent_id', string='Sotto-iniziative')
    child_count = fields.Integer(compute='_compute_child_count')

    # Persone
    user_id = fields.Many2one('res.users', string='Owner', required=True,
                              default=lambda self: self.env.user, tracking=True)
    collaborator_ids = fields.Many2many('res.users', 'cf_initiative_user_rel',
                                        string='Collaboratori')
    partner_id = fields.Many2one('res.partner', string='Cliente/Partner', tracking=True)

    # Tempi & budget
    date_start = fields.Date(string='Data Inizio', tracking=True)
    date_end = fields.Date(string='Data Fine', tracking=True)
    budget = fields.Monetary(tracking=True)
    currency_id = fields.Many2one('res.currency',
                                  default=lambda self: self.env.company.currency_id)

    # Stato
    state = fields.Selection([
        ('draft', 'Bozza'),
        ('in_progress', 'In Corso'),
        ('done', 'Completata'),
        ('cancelled', 'Annullata'),
    ], default='draft', tracking=True)

    # Tag & atomi
    tag_ids = fields.Many2many('cf.initiative.tag', string='Tag')
    atom_line_ids = fields.One2many('cf.initiative.atom.line', 'initiative_id', string='Atomi')
    atom_count = fields.Integer(compute='_compute_atom_count')

    # Content
    description = fields.Html()

    # Figli Odoo
    crm_lead_ids = fields.One2many('crm.lead', 'initiative_id', string='Lead')
    project_ids = fields.One2many('project.project', 'initiative_id', string='Progetti')
    sale_order_ids = fields.One2many('sale.order', 'initiative_id', string='Ordini')
    account_move_ids = fields.One2many('account.move', 'initiative_id', string='Fatture')
    stock_picking_ids = fields.One2many('stock.picking', 'initiative_id', string='Picking')
    mrp_production_ids = fields.One2many('mrp.production', 'initiative_id', string='Produzioni')

    # Conteggi smart button
    lead_count = fields.Integer(compute='_compute_object_counts')
    project_count = fields.Integer(compute='_compute_object_counts')
    sale_count = fields.Integer(compute='_compute_object_counts')
    move_count = fields.Integer(compute='_compute_object_counts')
    picking_count = fields.Integer(compute='_compute_object_counts')
    production_count = fields.Integer(compute='_compute_object_counts')

    @api.depends('child_ids')
    def _compute_child_count(self):
        for rec in self:
            rec.child_count = len(rec.child_ids)

    @api.depends('atom_line_ids')
    def _compute_atom_count(self):
        for rec in self:
            rec.atom_count = len(rec.atom_line_ids)

    @api.depends('crm_lead_ids', 'project_ids', 'sale_order_ids',
                 'account_move_ids', 'stock_picking_ids', 'mrp_production_ids')
    def _compute_object_counts(self):
        for rec in self:
            rec.lead_count = len(rec.crm_lead_ids)
            rec.project_count = len(rec.project_ids)
            rec.sale_count = len(rec.sale_order_ids)
            rec.move_count = len(rec.account_move_ids)
            rec.picking_count = len(rec.stock_picking_ids)
            rec.production_count = len(rec.mrp_production_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('cf.initiative') or 'New'
            # Eredita tag da parent
            if vals.get('parent_id') and not vals.get('tag_ids'):
                parent = self.env['cf.initiative'].browse(vals['parent_id'])
                if parent.tag_ids:
                    vals['tag_ids'] = [(6, 0, parent.tag_ids.ids)]
        return super().create(vals_list)

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_view_leads(self):
        return self._action_view_linked('crm.lead', self.crm_lead_ids)

    def action_view_projects(self):
        return self._action_view_linked('project.project', self.project_ids)

    def action_view_sales(self):
        return self._action_view_linked('sale.order', self.sale_order_ids)

    def action_view_moves(self):
        return self._action_view_linked('account.move', self.account_move_ids)

    def action_view_pickings(self):
        return self._action_view_linked('stock.picking', self.stock_picking_ids)

    def action_view_productions(self):
        return self._action_view_linked('mrp.production', self.mrp_production_ids)

    def action_view_children(self):
        return self._action_view_linked('cf.initiative', self.child_ids)

    def action_view_atoms(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Atomi'),
            'res_model': 'cf.initiative.atom.line',
            'view_mode': 'list',
            'domain': [('initiative_id', '=', self.id)],
        }

    def _action_view_linked(self, model, records):
        action = {
            'type': 'ir.actions.act_window',
            'res_model': model,
            'view_mode': 'list,form',
            'domain': [('id', 'in', records.ids)],
        }
        if len(records) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = records.id
        return action
