"""
Multi-user isolation tests for casafolino_mail V16.

NOT run in CI — present for manual testing and documentation.
Run manually: odoo -d test_db --test-tags casafolino_mail -u casafolino_mail --stop-after-init --no-http
"""
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestMultiUserIsolation(TransactionCase):
    """Verify that record rules enforce per-user mail isolation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create two test users
        cls.user_a = cls.env['res.users'].create({
            'name': 'Test User A',
            'login': 'test_user_a@test.com',
            'email': 'test_user_a@test.com',
            'groups_id': [(4, cls.env.ref('base.group_user').id)],
        })
        cls.user_b = cls.env['res.users'].create({
            'name': 'Test User B',
            'login': 'test_user_b@test.com',
            'email': 'test_user_b@test.com',
            'groups_id': [(4, cls.env.ref('base.group_user').id)],
        })

        # Create accounts linked to each user
        Account = cls.env['casafolino.mail.account'].sudo()
        cls.account_a = Account.create({
            'name': 'Account A',
            'email': 'test_user_a@test.com',
            'responsible_user_id': cls.user_a.id,
            'imap_host': 'localhost',
            'imap_user': 'test_a',
            'imap_password': 'test',
            'smtp_host': 'localhost',
            'smtp_user': 'test_a',
            'smtp_password': 'test',
        })
        cls.account_b = Account.create({
            'name': 'Account B',
            'email': 'test_user_b@test.com',
            'responsible_user_id': cls.user_b.id,
            'imap_host': 'localhost',
            'imap_user': 'test_b',
            'imap_password': 'test',
            'smtp_host': 'localhost',
            'smtp_user': 'test_b',
            'smtp_password': 'test',
        })

        # Create threads for each account
        Thread = cls.env['casafolino.mail.thread'].sudo()
        cls.thread_a = Thread.create({
            'account_id': cls.account_a.id,
            'subject': 'Thread A',
        })
        cls.thread_b = Thread.create({
            'account_id': cls.account_b.id,
            'subject': 'Thread B',
        })

        # Create folders for each account
        Folder = cls.env['casafolino.mail.folder'].sudo()
        cls.folder_a = Folder.create({
            'name': 'Test Folder A',
            'account_id': cls.account_a.id,
            'system_code': False,
        })
        cls.folder_b = Folder.create({
            'name': 'Test Folder B',
            'account_id': cls.account_b.id,
            'system_code': False,
        })

    def test_user_a_sees_only_own_account(self):
        """User A sees only their own account."""
        accounts = self.env['casafolino.mail.account'].with_user(self.user_a).search([])
        self.assertIn(self.account_a, accounts)
        self.assertNotIn(self.account_b, accounts)

    def test_user_b_sees_only_own_account(self):
        """User B sees only their own account."""
        accounts = self.env['casafolino.mail.account'].with_user(self.user_b).search([])
        self.assertIn(self.account_b, accounts)
        self.assertNotIn(self.account_a, accounts)

    def test_user_a_cannot_read_thread_b(self):
        """User A cannot access threads from User B's account."""
        threads = self.env['casafolino.mail.thread'].with_user(self.user_a).search([])
        self.assertIn(self.thread_a, threads)
        self.assertNotIn(self.thread_b, threads)

    def test_user_a_cannot_read_folder_b(self):
        """User A cannot see User B's folders."""
        folders = self.env['casafolino.mail.folder'].with_user(self.user_a).search([])
        self.assertIn(self.folder_a, folders)
        self.assertNotIn(self.folder_b, folders)

    def test_user_a_cannot_write_thread_b(self):
        """User A cannot modify User B's threads."""
        with self.assertRaises(AccessError):
            self.thread_b.with_user(self.user_a).write({'subject': 'Hacked'})

    def test_admin_sees_all(self):
        """Admin (SUPERUSER) sees all accounts and threads."""
        accounts = self.env['casafolino.mail.account'].sudo().search([])
        self.assertIn(self.account_a, accounts)
        self.assertIn(self.account_b, accounts)

    def test_cron_fetch_all_accounts_as_admin(self):
        """Cron (runs as admin) can access all accounts for IMAP fetch."""
        Account = self.env['casafolino.mail.account'].sudo()
        all_accounts = Account.search([])
        # Cron with sudo should see all accounts
        self.assertTrue(len(all_accounts) >= 2,
                        "Cron (sudo) must see all accounts for IMAP fetch")
