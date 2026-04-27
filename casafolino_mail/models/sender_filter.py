import logging
import re

from odoo import models

_logger = logging.getLogger(__name__)

# ~150 public/free email domains — exact match only for these
PUBLIC_DOMAINS_BLACKLIST = {
    # Global
    'gmail.com', 'googlemail.com', 'outlook.com', 'hotmail.com', 'hotmail.co.uk',
    'live.com', 'live.it', 'msn.com', 'yahoo.com', 'yahoo.it', 'yahoo.co.uk',
    'yahoo.de', 'yahoo.fr', 'yahoo.es', 'yahoo.co.jp', 'ymail.com',
    'aol.com', 'aol.de', 'protonmail.com', 'protonmail.ch', 'proton.me',
    'pm.me', 'tutanota.com', 'tutamail.com', 'tuta.io',
    'icloud.com', 'me.com', 'mac.com',
    'zoho.com', 'zohomail.eu', 'zohomail.com',
    'mail.com', 'email.com', 'usa.com', 'post.com',
    'gmx.com', 'gmx.net', 'gmx.de', 'gmx.at', 'gmx.ch',
    'yandex.com', 'yandex.ru', 'ya.ru',
    'mail.ru', 'inbox.ru', 'list.ru', 'bk.ru',
    'rambler.ru', 'autorambler.ru',
    'fastmail.com', 'fastmail.fm',
    'hushmail.com', 'runbox.com', 'posteo.de', 'posteo.net',
    'mailbox.org', 'disroot.org', 'riseup.net',
    'cock.li', 'airmail.cc', 'guerrillamail.com',
    'sharklasers.com', 'guerrillamailblock.com', 'grr.la',
    'tempmail.com', 'throwaway.email', 'temp-mail.org',
    'mailinator.com', 'maildrop.cc', 'yopmail.com',
    # Italy
    'libero.it', 'virgilio.it', 'alice.it', 'tin.it', 'tim.it',
    'tiscali.it', 'fastweb.it', 'fastwebnet.it', 'wind.it',
    'tre.it', 'vodafone.it', 'poste.it',
    'pec.it', 'legalmail.it', 'arubapec.it', 'postecert.it',
    'pec.libero.it', 'pec.giottocell.it',
    'inwind.it', 'iol.it', 'supereva.it', 'kataweb.it',
    'email.it', 'tele2.it', 'katamail.com',
    # Germany / Austria / Switzerland
    'web.de', 't-online.de', 'freenet.de', 'arcor.de',
    'gmx.de', 'gmx.at', 'gmx.ch',
    'bluewin.ch', 'sunrise.ch',
    'aon.at', 'chello.at', 'a1.net',
    '1und1.de', 'ionos.de', 'online.de',
    'posteo.de', 'mailbox.org',
    # France
    'orange.fr', 'wanadoo.fr', 'free.fr', 'laposte.net',
    'sfr.fr', 'neuf.fr', 'bbox.fr', 'numericable.fr',
    # Spain
    'telefonica.net', 'movistar.es', 'terra.es', 'ono.com',
    'ya.com', 'jazztel.es',
    # UK
    'btinternet.com', 'btopenworld.com', 'sky.com',
    'virginmedia.com', 'talktalk.net', 'ntlworld.com',
    # US / Canada
    'comcast.net', 'verizon.net', 'att.net', 'sbcglobal.net',
    'charter.net', 'cox.net', 'earthlink.net', 'juno.com',
    'bellsouth.net', 'optonline.net', 'rogers.com', 'shaw.ca',
    # Japan
    'docomo.ne.jp', 'ezweb.ne.jp', 'softbank.ne.jp',
    'i.softbank.jp', 'nifty.com', 'biglobe.ne.jp',
    # Brazil
    'bol.com.br', 'uol.com.br', 'terra.com.br', 'ig.com.br',
    # Others
    'rediffmail.com', '163.com', 'qq.com', '126.com', 'sina.com',
    'naver.com', 'daum.net', 'hanmail.net',
    'outlook.de', 'outlook.fr', 'outlook.it', 'outlook.es',
    'hotmail.de', 'hotmail.fr', 'hotmail.it', 'hotmail.es',
}

# Valid domain pattern
_DOMAIN_RE = re.compile(r'^[a-z0-9]([a-z0-9\-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]*[a-z0-9])?)+$')


class SenderFilterMixin(models.AbstractModel):
    _name = 'casafolino.mail.sender.filter'
    _description = 'Sender Whitelist Filter (CRM-based)'

    def is_sender_allowed(self, sender_email):
        """Check if sender is in CRM whitelist.

        Returns:
            tuple: (allowed: bool, partner_id: int or False, match_type: str or None)
            match_type: 'exact' | 'domain' | 'extra_domain' | None
        """
        if not sender_email:
            return (False, False, None)

        email_addr = sender_email.strip().lower()
        if '@' not in email_addr:
            return (False, False, None)

        domain = email_addr.split('@')[-1]
        if not domain:
            return (False, False, None)

        Partner = self.env['res.partner'].sudo()

        # 1. Exact email match (always valid, even on public domains)
        partner = Partner.search([('email', '=ilike', email_addr)], limit=1)
        if partner:
            return (True, partner.id, 'exact')

        # 2. Public domain → STOP here (no domain match for gmail etc.)
        if domain in PUBLIC_DOMAINS_BLACKLIST:
            return (False, False, None)

        # 3. Domain match from company partner email field
        partner = Partner.search([
            ('is_company', '=', True),
            ('email', '=ilike', '%@' + domain),
        ], limit=1)
        if partner:
            # Auto-create child contact
            name_part = email_addr.split('@')[0]
            display_name = name_part.replace('.', ' ').replace('_', ' ').title()
            child = Partner.create({
                'name': display_name,
                'email': email_addr,
                'parent_id': partner.id,
                'type': 'contact',
            })
            return (True, child.id, 'domain')

        # 4. Match via email_domains_extra field
        partners_extra = Partner.search([
            ('is_company', '=', True),
            ('email_domains_extra', '!=', False),
        ])
        for p in partners_extra:
            extra_domains = [
                d.strip().lower()
                for d in (p.email_domains_extra or '').split(',')
                if d.strip()
            ]
            if domain in extra_domains:
                name_part = email_addr.split('@')[0]
                display_name = name_part.replace('.', ' ').replace('_', ' ').title()
                child = Partner.create({
                    'name': display_name,
                    'email': email_addr,
                    'parent_id': p.id,
                    'type': 'contact',
                })
                return (True, child.id, 'extra_domain')

        # 5. No match
        return (False, False, None)
