from odoo.tests.common import TransactionCase


class TestMailV3Threading(TransactionCase):

    def test_thread_upsert_same_subject(self):
        """Two messages with same normalized subject go into the same thread."""
        account = self.env['casafolino.mail.account'].search([], limit=1)
        if not account:
            self.skipTest("No mail account available")

        msg1 = self.env['casafolino.mail.message'].create({
            'account_id': account.id,
            'subject': 'Test Thread Subject',
            'sender_email': 'buyer@example.com',
            'recipient_emails': 'us@casafolino.com',
            'email_date': '2026-04-20 10:00:00',
            'state': 'keep',
            'direction': 'inbound',
        })
        msg2 = self.env['casafolino.mail.message'].create({
            'account_id': account.id,
            'subject': 'Re: Test Thread Subject',
            'sender_email': 'us@casafolino.com',
            'recipient_emails': 'buyer@example.com',
            'email_date': '2026-04-20 11:00:00',
            'state': 'keep',
            'direction': 'outbound',
        })

        self.assertTrue(msg1.thread_id, "msg1 should have a thread")
        self.assertTrue(msg2.thread_id, "msg2 should have a thread")
        self.assertEqual(msg1.thread_id, msg2.thread_id,
                         "Both messages should be in the same thread")
        self.assertEqual(msg1.thread_id.message_count, 2)

    def test_thread_different_subjects(self):
        """Messages with different subjects create different threads."""
        account = self.env['casafolino.mail.account'].search([], limit=1)
        if not account:
            self.skipTest("No mail account available")

        msg1 = self.env['casafolino.mail.message'].create({
            'account_id': account.id,
            'subject': 'Subject Alpha',
            'sender_email': 'a@example.com',
            'recipient_emails': 'us@casafolino.com',
            'email_date': '2026-04-20 10:00:00',
            'state': 'keep',
            'direction': 'inbound',
        })
        msg2 = self.env['casafolino.mail.message'].create({
            'account_id': account.id,
            'subject': 'Subject Beta',
            'sender_email': 'b@example.com',
            'recipient_emails': 'us@casafolino.com',
            'email_date': '2026-04-20 11:00:00',
            'state': 'keep',
            'direction': 'inbound',
        })

        self.assertNotEqual(msg1.thread_id, msg2.thread_id)
