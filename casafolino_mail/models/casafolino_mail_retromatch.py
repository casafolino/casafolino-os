import logging

from odoo import api, models, _

_logger = logging.getLogger(__name__)


def _emails_of(partner):
    """Email candidate del partner (email + email_normalized), lowercase, dedup."""
    out = []
    for e in (partner.email, partner.email_normalized):
        e = (e or '').strip().lower()
        if e and '@' in e and e not in out:
            out.append(e)
    return out


def _cf_clean_sender_email(vals):
    """Normalizza sender_email in-place: trim whitespace ai bordi (no lowercase, preserva display).
    Garantisce che il match esatto `=ilike` dei sibling/retro-link non venga rotto da spazi spurî."""
    se = vals.get('sender_email')
    if isinstance(se, str):
        stripped = se.strip()
        if stripped != se:
            vals['sender_email'] = stripped
    return vals


def _orphan_domain(emails):
    """Domain ORM: messaggi orfani (partner_id vuoto) con sender_email in `emails` (case-insensitive)."""
    leaves = [('sender_email', '=ilike', e) for e in emails]
    if not leaves:
        return None
    dom = [('partner_id', '=', False), ('sender_email', '!=', False)]
    if len(leaves) > 1:
        dom += ['|'] * (len(leaves) - 1)
    dom += leaves
    return dom


class ResPartnerMailRetroMatch(models.Model):
    """Fix Bug 1 — retro-link: quando un partner viene creato/modificato dopo l'ingestion,
    riaggancia i messaggi orfani con lo stesso mittente. Niente più mittenti orfani 'a vita'."""
    _inherit = 'res.partner'

    def _cf_retrolink_orphan_mails(self):
        """Per ogni partner con email, aggancia i casafolino.mail.message orfani con sender_email
        corrispondente (email o email_normalized). Ritorna n. messaggi agganciati."""
        Msg = self.env['casafolino.mail.message'].sudo()
        total = 0
        for p in self:
            emails = _emails_of(p)
            if not emails:
                continue
            dom = _orphan_domain(emails)
            orphans = Msg.search(dom) if dom else Msg.browse()
            if orphans:
                orphans.write({'partner_id': p.id})
                total += len(orphans)
                _logger.info('[retrolink] partner %s (%s): agganciati %s messaggi orfani',
                             p.id, emails[0], len(orphans))
        return total

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        try:
            partners.filtered(lambda r: r.email)._cf_retrolink_orphan_mails()
        except Exception as e:  # mai bloccare la create per il retro-link
            _logger.warning('[retrolink] create hook error: %s', e)
        return partners

    def write(self, vals):
        res = super().write(vals)
        if 'email' in vals or 'email_normalized' in vals:
            try:
                self.filtered(lambda r: r.email)._cf_retrolink_orphan_mails()
            except Exception as e:
                _logger.warning('[retrolink] write hook error: %s', e)
        return res


class CasafolinoMailMessageRetroMatch(models.Model):
    """Fix Bug 1 — backfill on-demand degli orfani + collegamento manuale a partner con
    aggancio dei siblings + timeline fallback per mittente."""
    _inherit = 'casafolino.mail.message'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            _cf_clean_sender_email(vals)
        return super().create(vals_list)

    def write(self, vals):
        _cf_clean_sender_email(vals)
        return super().write(vals)

    @api.model
    def action_backfill_orphan_partners(self):
        """Azione on-demand (menu Inbox): ripassa tutti i messaggi orfani e tenta il match per
        email/email_normalized (inclusi i contatti figli, via search standard). Logga il riepilogo."""
        Msg = self.sudo()
        Partner = self.env['res.partner'].sudo()
        orphans = Msg.search([('partner_id', '=', False), ('sender_email', '!=', False)])
        scanned = len(orphans)
        linked = 0
        cache = {}
        for m in orphans:
            e = (m.sender_email or '').strip().lower()
            if not e or '@' not in e:
                continue
            if e not in cache:
                p = Partner.search(['|', ('email', '=ilike', e),
                                    ('email_normalized', '=ilike', e)], limit=1)
                cache[e] = p.id if p else False
            if cache[e]:
                m.partner_id = cache[e]
                linked += 1
        _logger.info('[backfill] scanned %s, linked %s', scanned, linked)
        return {'scanned': scanned, 'linked': linked}

    def cf_link_partner(self, partner_id):
        """Collegamento manuale: aggancia QUESTO messaggio + tutti i siblings orfani con lo stesso
        sender_email al partner. Ritorna n. messaggi agganciati."""
        self.ensure_one()
        Partner = self.env['res.partner'].sudo()
        p = Partner.browse(int(partner_id))
        if not p.exists():
            return {'ok': False, 'error': _('Partner inesistente.')}
        e = (self.sender_email or '').strip().lower()
        targets = self
        if e:
            sibs = self.sudo().search([('partner_id', '=', False), ('sender_email', '=ilike', e)])
            targets = self | sibs
        targets.sudo().write({'partner_id': p.id})
        _logger.info('[link_partner] msg %s + siblings → partner %s: %s messaggi',
                     self.id, p.id, len(targets))
        return {'ok': True, 'partner_id': p.id, 'partner_name': p.name, 'linked': len(targets)}

    def cf_sibling_mails(self, limit=50):
        """Timeline fallback: messaggi correlati. Se il messaggio ha partner_id → per partner;
        altrimenti raggruppa per sender_email esatto (così l'orfano vede comunque i fratelli)."""
        self.ensure_one()
        Msg = self.sudo()
        if self.partner_id:
            domain = [('partner_id', '=', self.partner_id.id)]
            mode = 'partner'
        else:
            e = (self.sender_email or '').strip().lower()
            if not e:
                return {'mode': 'none', 'count': 0, 'items': []}
            domain = [('sender_email', '=ilike', e)]
            mode = 'sender'
        domain += [('state', 'not in', ['auto_discard'])]
        msgs = Msg.search(domain, order='email_date desc', limit=int(limit))
        items = [{
            'id': m.id, 'subject': m.subject or '', 'sender_name': m.sender_name or '',
            'sender_email': m.sender_email or '',
            'email_date': str(m.email_date) if m.email_date else '',
            'direction': m.direction or 'inbound',
            'partner_id': m.partner_id.id if m.partner_id else False,
        } for m in msgs]
        return {'mode': mode, 'count': len(items), 'items': items}
