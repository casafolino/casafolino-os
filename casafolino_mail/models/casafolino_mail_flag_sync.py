import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CasafolinoMailFlagSync(models.AbstractModel):
    _name = 'casafolino.mail.flag.sync'
    _description = 'IMAP Flag Sync (bidirectional read/unread)'

    @api.model
    def _cron_push_flags(self):
        """Push \Seen flags to IMAP for messages marked read in Odoo."""
        enabled = self.env['ir.config_parameter'].sudo().get_param(
            'casafolino.mail.v3_sync_flags_enabled', 'False')
        if enabled not in ('True', '1', 'true'):
            return

        accounts = self.env['casafolino.mail.account'].search([
            ('state', '=', 'connected'), ('active', '=', True),
        ])

        total_pushed = 0
        for account in accounts:
            try:
                pushed = self._push_seen_for_account(account)
                total_pushed += pushed
            except Exception as e:
                _logger.error("[flag_sync] Push error %s: %s", account.email_address, e)

        if total_pushed:
            _logger.info("[flag_sync] Pushed \\Seen for %d messages", total_pushed)

    def _push_seen_for_account(self, account):
        """Push \Seen for read messages on a single account."""
        Message = self.env['casafolino.mail.message']

        # Find messages marked read in Odoo but not yet synced to IMAP
        # We use a convention: is_read=True + imap_flags_synced=False
        messages = Message.search([
            ('account_id', '=', account.id),
            ('is_read', '=', True),
            ('imap_flags_synced', '=', False),
            ('imap_uid', '!=', False),
            ('imap_folder', '!=', False),
        ], limit=200)

        if not messages:
            return 0

        imap = account._get_imap_connection()
        pushed = 0

        try:
            # Group by folder
            by_folder = {}
            for msg in messages:
                folder = msg.imap_folder
                if folder not in by_folder:
                    by_folder[folder] = []
                by_folder[folder].append(msg)

            for folder, msgs in by_folder.items():
                status, _ = imap.select('"%s"' % folder)
                if status != 'OK':
                    continue

                for msg in msgs:
                    try:
                        uid_bytes = msg.imap_uid.encode() if isinstance(msg.imap_uid, str) else msg.imap_uid
                        status, _ = imap.store(uid_bytes, '+FLAGS', '\\Seen')
                        if status == 'OK':
                            msg.write({'imap_flags_synced': True})
                            pushed += 1
                    except Exception as e:
                        _logger.warning("[flag_sync] Store error uid %s: %s", msg.imap_uid, e)

            self.env.cr.commit()
        finally:
            try:
                imap.logout()
            except Exception:
                pass

        return pushed

    @api.model
    def _cron_pull_flags(self):
        """Pull flag changes from IMAP (mark read/unread in Odoo)."""
        enabled = self.env['ir.config_parameter'].sudo().get_param(
            'casafolino.mail.v3_sync_flags_enabled', 'False')
        if enabled not in ('True', '1', 'true'):
            return

        accounts = self.env['casafolino.mail.account'].search([
            ('state', '=', 'connected'), ('active', '=', True),
        ])

        total_pulled = 0
        for account in accounts:
            try:
                pulled = self._pull_flags_for_account(account)
                total_pulled += pulled
            except Exception as e:
                _logger.error("[flag_sync] Pull error %s: %s", account.email_address, e)

        if total_pulled:
            _logger.info("[flag_sync] Pulled flag changes for %d messages", total_pulled)

    def _pull_flags_for_account(self, account):
        """Pull \Seen flag state from IMAP for recent messages."""
        Message = self.env['casafolino.mail.message']

        # Only sync messages from last 7 days that have IMAP UIDs
        messages = Message.search([
            ('account_id', '=', account.id),
            ('imap_uid', '!=', False),
            ('imap_folder', '!=', False),
            ('state', 'in', ('keep', 'auto_keep')),
            ('email_date', '>=', fields.Datetime.subtract(fields.Datetime.now(), days=7)),
        ], limit=500)

        if not messages:
            return 0

        imap = account._get_imap_connection()
        pulled = 0

        try:
            by_folder = {}
            for msg in messages:
                folder = msg.imap_folder
                if folder not in by_folder:
                    by_folder[folder] = []
                by_folder[folder].append(msg)

            for folder, msgs in by_folder.items():
                status, _ = imap.select('"%s"' % folder, readonly=True)
                if status != 'OK':
                    continue

                for msg in msgs:
                    try:
                        uid_bytes = msg.imap_uid.encode() if isinstance(msg.imap_uid, str) else msg.imap_uid
                        status, flag_data = imap.fetch(uid_bytes, '(FLAGS)')
                        if status != 'OK':
                            continue

                        # Parse flags
                        raw = flag_data[0] if flag_data else b''
                        if isinstance(raw, bytes):
                            raw = raw.decode('utf-8', errors='ignore')

                        is_seen = '\\Seen' in raw

                        if is_seen and not msg.is_read:
                            msg.write({'is_read': True, 'imap_flags_synced': True})
                            pulled += 1
                        elif not is_seen and msg.is_read:
                            msg.write({'is_read': False, 'imap_flags_synced': True})
                            pulled += 1
                    except Exception as e:
                        _logger.warning("[flag_sync] Fetch flags error uid %s: %s", msg.imap_uid, e)

            self.env.cr.commit()
        finally:
            try:
                imap.logout()
            except Exception:
                pass

        return pulled
