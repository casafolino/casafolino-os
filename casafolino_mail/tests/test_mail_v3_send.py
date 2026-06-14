from odoo.tests.common import TransactionCase


class TestMailV3Send(TransactionCase):

    def test_draft_create_and_autosave(self):
        """Draft can be created and autosaved."""
        account = self.env['casafolino.mail.account'].search([], limit=1)
        if not account:
            self.skipTest("No mail account available")

        draft = self.env['casafolino.mail.draft'].create({
            'account_id': account.id,
            'user_id': self.env.uid,
            'to_emails': 'test@example.com',
            'subject': 'Test Draft',
            'body_html': '<p>Hello</p>',
        })

        self.assertTrue(draft, "Draft should be created")
        draft.action_autosave()
        self.assertTrue(draft.auto_saved_at, "Should have autosave timestamp")

    def test_signature_default_constraint(self):
        """Only one default signature per account."""
        account = self.env['casafolino.mail.account'].search([], limit=1)
        if not account:
            self.skipTest("No mail account available")

        sig1 = self.env['casafolino.mail.signature'].create({
            'name': 'Sig 1',
            'account_id': account.id,
            'body_html': '<p>Sig 1</p>',
            'is_default': True,
        })

        with self.assertRaises(Exception):
            self.env['casafolino.mail.signature'].create({
                'name': 'Sig 2',
                'account_id': account.id,
                'body_html': '<p>Sig 2</p>',
                'is_default': True,
            })
