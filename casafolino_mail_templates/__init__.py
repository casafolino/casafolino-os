from . import models
from . import wizard


def _post_init_hook(env):
    """Assign SIAL Montreal tag to existing templates."""
    Tag = env['casafolino.mail.template.tag']

    # Assign SIAL Montreal 2026 tag to existing SIAL templates
    sial_tag = Tag.search([('name', '=', 'SIAL Montreal 2026')], limit=1)
    if sial_tag:
        templates = env['mail.template'].search([('name', 'ilike', 'SIAL Montreal')])
        for t in templates:
            t.cf_tag_ids = [(4, sial_tag.id)]

    env.cr.commit()
