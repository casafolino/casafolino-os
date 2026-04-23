from odoo.tests.common import TransactionCase


class TestInitiative(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.family_oc = cls.env.ref('casafolino_initiative.family_oc')
        cls.variant_oc_std = cls.env.ref('casafolino_initiative.variant_oc_standard')
        cls.template_oc = cls.env.ref('casafolino_initiative.template_oc_standard')
        cls.tag_sial = cls.env.ref('casafolino_initiative.tag_fair_sial_canada')
        cls.tag_anuga = cls.env.ref('casafolino_initiative.tag_fair_anuga')

    def test_create_initiative(self):
        """Create basic initiative, check code sequence and defaults."""
        ini = self.env['cf.initiative'].create({
            'name': 'Test OC',
            'family_id': self.family_oc.id,
            'variant_id': self.variant_oc_std.id,
        })
        self.assertTrue(ini.code.startswith('INI/'))
        self.assertEqual(ini.state, 'draft')
        self.assertEqual(ini.user_id, self.env.user)

    def test_wizard_flow(self):
        """Wizard creates initiative with atom lines from template."""
        wiz = self.env['cf.initiative.wizard'].create({
            'family_id': self.family_oc.id,
            'variant_id': self.variant_oc_std.id,
            'name': 'Test Wizard OC',
            'step': '4_config',
        })
        result = wiz.action_create()
        ini = self.env['cf.initiative'].browse(result['res_id'])
        self.assertEqual(len(ini.atom_line_ids), 9)
        atom_codes = ini.atom_line_ids.mapped('atom_id.code')
        for code in ['A11', 'A01', 'A02', 'A03', 'A04', 'A06', 'A05', 'A07', 'A12']:
            self.assertIn(code, atom_codes)

    def test_tag_propagation_lead(self):
        """Creating CRM lead with initiative_id propagates tags."""
        ini = self.env['cf.initiative'].create({
            'name': 'Test Tag Lead',
            'family_id': self.family_oc.id,
            'variant_id': self.variant_oc_std.id,
            'tag_ids': [(6, 0, [self.tag_sial.id])],
        })
        lead = self.env['crm.lead'].create({
            'name': 'Test Lead',
            'initiative_id': ini.id,
        })
        self.assertIn(self.tag_sial, lead.cf_tag_ids)

    def test_tag_propagation_hierarchy(self):
        """Child initiative inherits parent tags."""
        parent = self.env['cf.initiative'].create({
            'name': 'Parent Initiative',
            'family_id': self.family_oc.id,
            'variant_id': self.variant_oc_std.id,
            'tag_ids': [(6, 0, [self.tag_anuga.id])],
        })
        child = self.env['cf.initiative'].create({
            'name': 'Child Initiative',
            'family_id': self.family_oc.id,
            'variant_id': self.variant_oc_std.id,
            'parent_id': parent.id,
        })
        self.assertIn(self.tag_anuga, child.tag_ids)

    def test_record_rule_user_isolation(self):
        """Non-manager user sees only own initiatives."""
        user_a = self.env['res.users'].create({
            'name': 'User A',
            'login': 'user_a_test_ini',
            'groups_id': [(4, self.env.ref('casafolino_initiative.group_initiative_user').id)],
        })
        user_b = self.env['res.users'].create({
            'name': 'User B',
            'login': 'user_b_test_ini',
            'groups_id': [(4, self.env.ref('casafolino_initiative.group_initiative_user').id)],
        })
        ini_a = self.env['cf.initiative'].with_user(user_a).create({
            'name': 'Ini A',
            'family_id': self.family_oc.id,
            'variant_id': self.variant_oc_std.id,
        })
        ini_b = self.env['cf.initiative'].with_user(user_b).create({
            'name': 'Ini B',
            'family_id': self.family_oc.id,
            'variant_id': self.variant_oc_std.id,
        })
        visible_b = self.env['cf.initiative'].with_user(user_b).search([])
        self.assertIn(ini_b, visible_b)
        self.assertNotIn(ini_a, visible_b)
