from odoo import fields
from odoo.tests.common import TransactionCase


class TestAtomGeneration(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.family_oc = cls.env.ref('casafolino_initiative.family_oc')
        cls.variant_oc_std = cls.env.ref('casafolino_initiative.variant_oc_standard')
        cls.tag_sial = cls.env.ref('casafolino_initiative.tag_fair_sial_canada')
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner F2'})

        # Ensure atom configs for tests
        cls.atom_a11 = cls.env['cf.initiative.atom'].search([('code', '=', 'A11')], limit=1)
        cls.atom_a11.write({
            'generate_on_create': True,
            'subject_template': 'Brief avvio — {{object.initiative_id.name}}',
        })
        cls.atom_a01 = cls.env['cf.initiative.atom'].search([('code', '=', 'A01')], limit=1)
        cls.atom_a01.write({'generate_on_create': False})
        cls.atom_a05 = cls.env['cf.initiative.atom'].search([('code', '=', 'A05')], limit=1)
        cls.atom_a05.write({
            'generate_on_create': True,
            'subject_template': 'Offerta {{object.initiative_id.partner_id.name}}',
        })
        cls.atom_a02 = cls.env['cf.initiative.atom'].search([('code', '=', 'A02')], limit=1)
        cls.atom_a02.write({
            'generate_on_create': True,
            'subject_template': 'Invio listino a {{object.initiative_id.partner_id.name}}',
        })

    def _create_initiative_via_wizard(self, name='Test F2', partner=None, tag_ids=None):
        """Create initiative via wizard to get atom_lines populated from template."""
        partner = partner if partner is not None else self.partner
        if tag_ids is None:
            tag_ids = [(6, 0, [self.tag_sial.id])]
        wiz_vals = {
            'family_id': self.family_oc.id,
            'variant_id': self.variant_oc_std.id,
            'name': name,
            'partner_id': partner.id if partner else False,
            'step': '4_config',
            'date_start': fields.Date.today(),
            'tag_ids': tag_ids,
        }
        wiz = self.env['cf.initiative.wizard'].create(wiz_vals)
        result = wiz.action_create()
        return self.env['cf.initiative'].browse(result['res_id'])

    def test_generate_project_task(self):
        """A11 (project_task) generates a task linked to initiative project."""
        ini = self._create_initiative_via_wizard('Task Gen Test')
        ini.action_start()
        line_a11 = ini.atom_line_ids.filtered(lambda l: l.atom_id.code == 'A11')
        self.assertEqual(line_a11.generation_state, 'generated')
        self.assertEqual(line_a11.generated_model, 'project.task')
        self.assertTrue(line_a11.generated_res_id)
        task = self.env['project.task'].browse(line_a11.generated_res_id)
        self.assertTrue(task.exists())
        self.assertEqual(task.project_id, ini.project_id)
        self.assertEqual(task.initiative_id, ini)

    def test_generate_mail_activity(self):
        """A02 (mail_activity) generates an activity on the initiative."""
        ini = self._create_initiative_via_wizard('Activity Gen Test')
        ini.action_start()
        line_a02 = ini.atom_line_ids.filtered(lambda l: l.atom_id.code == 'A02')
        self.assertEqual(line_a02.generation_state, 'generated')
        self.assertEqual(line_a02.generated_model, 'mail.activity')
        activity = self.env['mail.activity'].browse(line_a02.generated_res_id)
        self.assertTrue(activity.exists())
        self.assertEqual(activity.res_id, ini.id)

    def test_generate_sale_order(self):
        """A05 (sale_order) generates a draft SO with partner and tags."""
        ini = self._create_initiative_via_wizard('SO Gen Test')
        ini.action_start()
        line_a05 = ini.atom_line_ids.filtered(lambda l: l.atom_id.code == 'A05')
        self.assertEqual(line_a05.generation_state, 'generated')
        so = self.env['sale.order'].browse(line_a05.generated_res_id)
        self.assertTrue(so.exists())
        self.assertEqual(so.partner_id, self.partner)
        self.assertEqual(so.initiative_id, ini)
        self.assertIn(self.tag_sial, so.cf_tag_ids)

    def test_bidirectional_sync_task(self):
        """Closing/reopening a generated task syncs atom_line state."""
        ini = self._create_initiative_via_wizard('Sync Test')
        ini.action_start()
        line_a11 = ini.atom_line_ids.filtered(lambda l: l.atom_id.code == 'A11')
        task = self.env['project.task'].browse(line_a11.generated_res_id)
        # Close task
        task.write({'state': '1_done'})
        self.assertEqual(line_a11.state, 'done')
        # Reopen task
        task.write({'state': '01_in_progress'})
        self.assertEqual(line_a11.state, 'in_progress')

    def test_template_rendering(self):
        """Subject template renders with initiative context."""
        ini = self._create_initiative_via_wizard('Render Test')
        ini.action_start()
        line_a11 = ini.atom_line_ids.filtered(lambda l: l.atom_id.code == 'A11')
        task = self.env['project.task'].browse(line_a11.generated_res_id)
        self.assertIn('Render Test', task.name)

    def test_error_handling(self):
        """Atom generation error does not block other atoms."""
        # Create without partner via direct create + manual atom lines
        ini = self.env['cf.initiative'].create({
            'name': 'Error Test',
            'family_id': self.family_oc.id,
            'variant_id': self.variant_oc_std.id,
            'partner_id': False,
            'date_start': fields.Date.today(),
        })
        # Manually add A05 (sale_order, needs partner) and A11 (project_task, no partner needed)
        self.env['cf.initiative.atom.line'].create([
            {
                'initiative_id': ini.id,
                'atom_id': self.atom_a05.id,
                'sequence': 10,
            },
            {
                'initiative_id': ini.id,
                'atom_id': self.atom_a11.id,
                'sequence': 20,
            },
        ])
        ini.action_start()
        line_a05 = ini.atom_line_ids.filtered(lambda l: l.atom_id.code == 'A05')
        self.assertEqual(line_a05.generation_state, 'error')
        self.assertTrue(line_a05.generation_error)
        line_a11 = ini.atom_line_ids.filtered(lambda l: l.atom_id.code == 'A11')
        self.assertEqual(line_a11.generation_state, 'generated')

    def test_auto_create_project(self):
        """action_start auto-creates project.project for initiative."""
        ini = self._create_initiative_via_wizard('Project Auto Test')
        self.assertFalse(ini.project_id)
        ini.action_start()
        self.assertTrue(ini.project_id)
        self.assertEqual(ini.project_id.initiative_id, ini)

    def test_generate_on_start(self):
        """Wizard creates atom_lines in pending; action_start triggers generation."""
        ini = self._create_initiative_via_wizard('Start Test')
        # All should be pending in draft
        self.assertTrue(all(
            l.generation_state == 'pending' for l in ini.atom_line_ids
        ))
        ini.action_start()
        generated = ini.atom_line_ids.filtered(
            lambda l: l.generation_state == 'generated'
        )
        manual = ini.atom_line_ids.filtered(
            lambda l: l.generation_state == 'manual'
        )
        self.assertTrue(len(generated) > 0)
        self.assertTrue(len(manual) > 0)
