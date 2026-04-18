from . import models
from . import wizards


def _pre_init_sale_templates(env):
    """Reset noupdate flag on native sale email templates so our XML override applies."""
    env.cr.execute("""
        UPDATE ir_model_data SET noupdate = false
        WHERE module = 'sale'
          AND name IN ('email_template_edi_sale', 'mail_template_sale_confirmation')
    """)
