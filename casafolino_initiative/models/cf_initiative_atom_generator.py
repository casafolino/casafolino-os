import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class CfAtomGenerator(models.AbstractModel):
    _name = 'cf.initiative.atom.generator'
    _description = 'Atom to Odoo Object Generator'

    def generate(self, atom_line):
        """Dispatch generation based on atom.odoo_object_type."""
        obj_type = atom_line.atom_id.odoo_object_type
        if not obj_type or obj_type == 'none':
            atom_line.write({'generation_state': 'manual'})
            return False

        method = getattr(self, f'_generate_{obj_type}', None)
        if not method:
            atom_line.write({
                'generation_state': 'error',
                'generation_error': _('No generator for type %s', obj_type),
            })
            return False

        try:
            record = method(atom_line)
            if record:
                atom_line.write({
                    'generated_model': record._name,
                    'generated_res_id': record.id,
                    'generation_state': 'generated',
                    'generated_at': fields.Datetime.now(),
                    'generation_error': False,
                    'state': 'in_progress',
                })
            return record
        except Exception as e:
            atom_line.write({
                'generation_state': 'error',
                'generation_error': str(e),
            })
            _logger.exception('Atom generation failed: %s', atom_line.atom_id.code)
            return False

    def _render_subject(self, atom_line):
        template = atom_line.atom_id.subject_template
        if not template:
            return atom_line.atom_id.name
        try:
            rendered = self.env['mail.render.mixin']._render_template(
                template, 'cf.initiative.atom.line', [atom_line.id],
                engine='inline_template',
            )
            return rendered.get(atom_line.id, atom_line.atom_id.name) or atom_line.atom_id.name
        except Exception:
            return atom_line.atom_id.name

    def _render_body(self, atom_line):
        template = atom_line.atom_id.body_template
        if not template:
            return ''
        try:
            rendered = self.env['mail.render.mixin']._render_template(
                template, 'cf.initiative.atom.line', [atom_line.id],
                engine='inline_template',
            )
            return rendered.get(atom_line.id, '') or ''
        except Exception:
            return ''

    def _common_vals(self, atom_line):
        ini = atom_line.initiative_id
        vals = {
            'initiative_id': ini.id,
        }
        if ini.tag_ids:
            vals['cf_tag_ids'] = [(6, 0, ini.tag_ids.ids)]
        return vals

    def _generate_project_task(self, atom_line):
        ini = atom_line.initiative_id
        if not ini.project_id:
            ini.project_id = self.env['project.project'].create({
                'name': f'{ini.code} — {ini.name}',
                'initiative_id': ini.id,
                'user_id': ini.user_id.id,
                'partner_id': ini.partner_id.id if ini.partner_id else False,
            })
        vals = {
            **self._common_vals(atom_line),
            'name': self._render_subject(atom_line),
            'project_id': ini.project_id.id,
            'user_ids': [(4, atom_line.user_id.id or ini.user_id.id)],
            'date_deadline': atom_line.date_deadline,
            'description': self._render_body(atom_line),
            'source_atom_line_id': atom_line.id,
        }
        if atom_line.atom_id.task_stage_default:
            vals['stage_id'] = atom_line.atom_id.task_stage_default.id
        return self.env['project.task'].create(vals)

    def _generate_mail_activity(self, atom_line):
        ini = atom_line.initiative_id
        activity_type = atom_line.atom_id.activity_type_id
        if not activity_type:
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        vals = {
            'res_model_id': self.env['ir.model']._get_id('cf.initiative'),
            'res_id': ini.id,
            'activity_type_id': activity_type.id if activity_type else False,
            'summary': self._render_subject(atom_line),
            'note': self._render_body(atom_line),
            'date_deadline': atom_line.date_deadline or fields.Date.context_today(self),
            'user_id': atom_line.user_id.id or ini.user_id.id,
        }
        return self.env['mail.activity'].create(vals)

    def _generate_sale_order(self, atom_line):
        ini = atom_line.initiative_id
        if not ini.partner_id:
            raise ValueError(_('Initiative %s has no partner for sale order generation', ini.code))
        vals = {
            **self._common_vals(atom_line),
            'partner_id': ini.partner_id.id,
            'user_id': atom_line.user_id.id or ini.user_id.id,
            'origin': ini.code,
            'source_atom_line_id': atom_line.id,
        }
        return self.env['sale.order'].create(vals)

    def _generate_stock_picking(self, atom_line):
        ini = atom_line.initiative_id
        picking_type = atom_line.atom_id.picking_type_id
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search(
                [('code', '=', 'outgoing')], limit=1,
            )
        vals = {
            **self._common_vals(atom_line),
            'partner_id': ini.partner_id.id if ini.partner_id else False,
            'picking_type_id': picking_type.id,
            'scheduled_date': atom_line.date_deadline or fields.Datetime.now(),
            'origin': ini.code,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
        }
        vals['source_atom_line_id'] = atom_line.id
        picking = self.env['stock.picking'].create(vals)
        if atom_line.atom_id.sample_product_ids:
            for product in atom_line.atom_id.sample_product_ids:
                self.env['stock.move'].create({
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'product_uom': product.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                })
        return picking

    def _generate_account_move(self, atom_line):
        ini = atom_line.initiative_id
        if not ini.partner_id:
            raise ValueError(_('Initiative %s has no partner for invoice generation', ini.code))
        vals = {
            **self._common_vals(atom_line),
            'move_type': 'out_invoice',
            'partner_id': ini.partner_id.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_user_id': atom_line.user_id.id or ini.user_id.id,
        }
        vals['source_atom_line_id'] = atom_line.id
        if atom_line.atom_id.journal_id:
            vals['journal_id'] = atom_line.atom_id.journal_id.id
        return self.env['account.move'].create(vals)

    def _generate_mrp_production(self, atom_line):
        ini = atom_line.initiative_id
        vals = {
            **self._common_vals(atom_line),
            'origin': ini.code,
            'user_id': atom_line.user_id.id or ini.user_id.id,
            'source_atom_line_id': atom_line.id,
        }
        return self.env['mrp.production'].create(vals)

    def _generate_crm_lead(self, atom_line):
        ini = atom_line.initiative_id
        vals = {
            **self._common_vals(atom_line),
            'name': self._render_subject(atom_line),
            'partner_id': ini.partner_id.id if ini.partner_id else False,
            'user_id': atom_line.user_id.id or ini.user_id.id,
            'source_atom_line_id': atom_line.id,
        }
        return self.env['crm.lead'].create(vals)
