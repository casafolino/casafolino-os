import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """v7.10.1 — fix compute fields on orphan SQL view (readonly, store=False).

    Idempotent: only logs, no schema changes needed.
    Compute fields are store=False so no columns exist to alter.
    """
    _logger.info(
        "casafolino_mail 7.10.1: orphan_partner compute fields "
        "set to store=False/readonly=True — no DB migration needed"
    )
