"""
Standalone migration script: Outbound recipient match backfill.

This script re-triages existing mail messages where the sender is internal
(casafolino.com) but the partner was incorrectly matched on the sender
instead of the external recipient.

Usage: see migrations/README.md for execution instructions.

NOT auto-executed on module install/update. Must be run manually via odoo shell.
"""
import logging

_logger = logging.getLogger(__name__)


def run(env, dry_run=True):
    """Entry point for odoo shell execution.

    Args:
        env: Odoo environment (from shell context)
        dry_run: If True (default), only logs changes without writing.
    """
    Message = env['casafolino.mail.message']
    result = Message.migrate_outbound_match(dry_run=dry_run)
    _logger.info("Migration result: %s", result)
    return result
