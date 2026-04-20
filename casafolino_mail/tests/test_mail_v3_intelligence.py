from odoo.tests.common import TransactionCase


class TestMailV3Intelligence(TransactionCase):

    def test_compute_for_partner_no_error(self):
        """Intelligence compute runs without errors for any partner."""
        partner = self.env['res.partner'].search([
            ('email', '!=', False),
        ], limit=1)
        if not partner:
            self.skipTest("No partner with email")

        Intel = self.env['casafolino.partner.intelligence']
        intel = Intel._compute_for_partner(partner.id)

        self.assertTrue(intel, "Should return intelligence record")
        self.assertGreaterEqual(intel.hotness_score, 0)
        self.assertLessEqual(intel.hotness_score, 100)
        self.assertTrue(intel.hotness_tier, "Should have a tier")
        self.assertTrue(intel.last_rebuild_at, "Should have rebuild timestamp")

    def test_hotness_tier_boundaries(self):
        """Hotness tier computed correctly from score."""
        Intel = self.env['casafolino.partner.intelligence']
        partner = self.env['res.partner'].create({
            'name': 'Test Intelligence Partner',
            'email': 'test_intel@example.com',
        })

        intel = Intel.create({
            'partner_id': partner.id,
            'hotness_score': 85,
        })
        self.assertEqual(intel.hotness_tier, 'hot')

        intel.hotness_score = 65
        self.assertEqual(intel.hotness_tier, 'warm')

        intel.hotness_score = 45
        self.assertEqual(intel.hotness_tier, 'active')

        intel.hotness_score = 25
        self.assertEqual(intel.hotness_tier, 'cold')

        intel.hotness_score = 10
        self.assertEqual(intel.hotness_tier, 'dormant')
