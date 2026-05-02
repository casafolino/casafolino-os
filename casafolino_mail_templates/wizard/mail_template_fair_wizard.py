from odoo import api, fields, models


LANG_SUBJECTS = {
    'en': 'Following up on our meeting at %(fair)s',
    'fr': 'Suite à notre rencontre au %(fair)s',
    'es': 'Seguimiento de nuestra reunión en %(fair)s',
    'it': 'A seguito del nostro incontro al %(fair)s',
}

LANG_BODIES = {
    'en': """<table cellpadding="0" cellspacing="0" border="0" width="100%%" style="padding:30px 10px; font-family:Arial,Helvetica,sans-serif">
<tr><td align="center">
<table cellpadding="0" cellspacing="0" border="0" width="600" style="background:#ffffff;border-radius:8px;">
<tr><td style="padding:30px;">
<p>Dear <t t-out="object.name or object.email or 'Sir/Madam'"/>,</p>
<p>It was a pleasure meeting you at <strong>%(fair)s</strong>. I am following up on our conversation about CasaFolino's artisan gourmet products from Calabria, Italy.</p>
<p>We would love to explore how we can work together. Please find our catalogue and company profile attached.</p>
<p>Looking forward to hearing from you.</p>
<p>Best regards,<br/>Antonio Folino<br/>CasaFolino Srls</p>
</td></tr></table>
</td></tr></table>""",
    'fr': """<table cellpadding="0" cellspacing="0" border="0" width="100%%" style="padding:30px 10px; font-family:Arial,Helvetica,sans-serif">
<tr><td align="center">
<table cellpadding="0" cellspacing="0" border="0" width="600" style="background:#ffffff;border-radius:8px;">
<tr><td style="padding:30px;">
<p>Cher(e) <t t-out="object.name or object.email or 'Monsieur/Madame'"/>,</p>
<p>Ce fut un plaisir de vous rencontrer au <strong>%(fair)s</strong>. Je fais suite à notre conversation concernant les produits artisanaux gourmet de CasaFolino, de Calabre, Italie.</p>
<p>Nous aimerions explorer comment nous pouvons travailler ensemble. Veuillez trouver notre catalogue et profil d'entreprise ci-joints.</p>
<p>Au plaisir de vous lire.</p>
<p>Cordialement,<br/>Antonio Folino<br/>CasaFolino Srls</p>
</td></tr></table>
</td></tr></table>""",
    'es': """<table cellpadding="0" cellspacing="0" border="0" width="100%%" style="padding:30px 10px; font-family:Arial,Helvetica,sans-serif">
<tr><td align="center">
<table cellpadding="0" cellspacing="0" border="0" width="600" style="background:#ffffff;border-radius:8px;">
<tr><td style="padding:30px;">
<p>Estimado/a <t t-out="object.name or object.email or 'Señor/Señora'"/>,</p>
<p>Fue un placer conocerle en <strong>%(fair)s</strong>. Le escribo para dar seguimiento a nuestra conversación sobre los productos artesanales gourmet de CasaFolino, de Calabria, Italia.</p>
<p>Nos encantaría explorar cómo podemos trabajar juntos. Adjunto encontrará nuestro catálogo y perfil de empresa.</p>
<p>Esperamos su respuesta.</p>
<p>Saludos cordiales,<br/>Antonio Folino<br/>CasaFolino Srls</p>
</td></tr></table>
</td></tr></table>""",
    'it': """<table cellpadding="0" cellspacing="0" border="0" width="100%%" style="padding:30px 10px; font-family:Arial,Helvetica,sans-serif">
<tr><td align="center">
<table cellpadding="0" cellspacing="0" border="0" width="600" style="background:#ffffff;border-radius:8px;">
<tr><td style="padding:30px;">
<p>Gentile <t t-out="object.name or object.email or 'Signore/Signora'"/>,</p>
<p>È stato un piacere incontrarLa al <strong>%(fair)s</strong>. Le scrivo per dare seguito alla nostra conversazione sui prodotti artigianali gourmet di CasaFolino, dalla Calabria.</p>
<p>Ci piacerebbe esplorare come poter collaborare. In allegato troverà il nostro catalogo e profilo aziendale.</p>
<p>In attesa di un Suo cortese riscontro.</p>
<p>Cordiali saluti,<br/>Antonio Folino<br/>CasaFolino Srls</p>
</td></tr></table>
</td></tr></table>""",
}

LANG_LABELS = {'en': 'EN', 'fr': 'FR', 'es': 'ES', 'it': 'IT'}


class MailTemplateFairWizard(models.TransientModel):
    _name = 'mail.template.fair.wizard'
    _description = 'Wizard creazione template fiera'

    fair_name = fields.Char(required=True, string='Nome Fiera',
                            help='Es. "PLMA Amsterdam 2026"')
    languages = fields.Selection([
        ('en', 'Solo EN'),
        ('en_fr', 'EN + FR'),
        ('en_fr_es', 'EN + FR + ES'),
        ('all', 'EN + FR + ES + IT'),
    ], required=True, default='en_fr', string='Lingue Template')
    cc_email = fields.Char(
        string='CC Email',
        default='josefina.lazzaro@casafolino.com')
    create_partner_category = fields.Boolean(
        string='Crea Categoria Partner', default=True)
    create_crm_tag = fields.Boolean(
        string='Crea Tag CRM', default=True)

    def action_create_templates(self):
        self.ensure_one()
        fair = self.fair_name

        # 1. Create template tag
        tag = self.env['casafolino.mail.template.tag'].create({
            'name': fair,
            'is_fair_tag': True,
            'color': 4,
            'description': 'Template per fiera %s' % fair,
        })

        # 2. Create partner category (idempotent)
        if self.create_partner_category:
            if not self.env['res.partner.category'].search(
                    [('name', '=', fair)], limit=1):
                self.env['res.partner.category'].create({
                    'name': fair, 'color': 4})

        # 3. Create CRM tag (idempotent)
        if self.create_crm_tag:
            if not self.env['crm.tag'].search(
                    [('name', '=', fair)], limit=1):
                self.env['crm.tag'].create({
                    'name': fair, 'color': 4})

        # 4. Create templates per language
        langs_map = {
            'en': ['en'],
            'en_fr': ['en', 'fr'],
            'en_fr_es': ['en', 'fr', 'es'],
            'all': ['en', 'fr', 'es', 'it'],
        }
        partner_model = self.env['ir.model']._get('res.partner')
        created_ids = []

        for lang in langs_map[self.languages]:
            label = LANG_LABELS[lang]
            subject_str = LANG_SUBJECTS[lang] % {'fair': fair}
            body = LANG_BODIES[lang] % {'fair': fair}

            tmpl = self.env['mail.template'].create({
                'name': '%s %s (Partner)' % (fair, label),
                'model_id': partner_model.id,
                'subject': subject_str,
                'body_html': body,
                'email_from': 'antonio@casafolino.com',
                'email_cc': self.cc_email or '',
                'cf_tag_ids': [(4, tag.id)],
                'cf_owner_id': self.env.uid,
            })
            created_ids.append(tmpl.id)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Template creati — %s' % fair,
            'res_model': 'mail.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_ids)],
        }
