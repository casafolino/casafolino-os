import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info(
        "casafolino_commercial %s: post-init migration — "
        "casafolino.fiera model + GDPR cron added via XML data files",
        version,
    )
