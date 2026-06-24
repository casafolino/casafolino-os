import logging
from datetime import timedelta

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

REPORT_PARAM = 'casafolino.bo_report_recipients_extra'  # email extra (Antonio) opz.
ANTONIO_USER_ID = 2  # res.users Antonio


class CfTaskReport(models.Model):
    _inherit = 'cf.task'

    @api.model
    def _bo_today_bounds(self):
        now = fields.Datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return fields.Datetime.to_string(start), fields.Datetime.to_string(now)

    @api.model
    def _bo_person_summary(self, emp):
        """Riepilogo giornaliero di un'operativa."""
        start, _now = self._bo_today_bounds()
        done = self.search([('bo_operatore_id', '=', emp.id), ('state', '=', 'chiuso'),
                            ('bo_firma_at', '>=', start)])
        by_kind = {}
        for t in done:
            by_kind[t.bo_kind or 'generico'] = by_kind.get(t.bo_kind or 'generico', 0) + 1
        worked = sum(done.mapped('bo_worked_seconds'))
        # ore giornata
        wds = self.env['bo.workday'].search([
            ('employee_id', '=', emp.id), ('check_in', '>=', start)])
        day_hours = sum(wds.mapped('worked_hours'))
        day_open = any(not w.check_out for w in wds)
        # fasi produzione fatte
        phases = self.env['cf.task.phase'].search([
            ('operatore_id', '=', emp.id), ('state', '=', 'fatta'),
            ('ended_at', '>=', start)])
        return {
            'employee': emp, 'done_count': len(done), 'by_kind': by_kind,
            'worked_h': worked / 3600.0, 'day_hours': day_hours, 'day_open': day_open,
            'phases': len(phases),
        }

    @api.model
    def _bo_person_html(self, s):
        rows = "".join("<li>%s: <b>%s</b></li>" % (k.capitalize(), v) for k, v in s['by_kind'].items())
        return _(
            "<p>Ciao %s, ecco la tua giornata 👏</p>"
            "<ul>"
            "<li>Task completate: <b>%s</b></li>"
            "%s"
            "<li>Fasi produzione fatte: <b>%s</b></li>"
            "<li>Tempo lavorato sulle task: <b>%.1f h</b></li>"
            "<li>Ore giornata: <b>%.1f h</b>%s</li>"
            "</ul>"
            "<p>Grazie per il lavoro di oggi!</p>"
        ) % (s['employee'].name, s['done_count'], rows or '', s['phases'],
             s['worked_h'], s['day_hours'], _(" (giornata ancora aperta)") if s['day_open'] else '')

    @api.model
    def _bo_send_mail(self, email_to, subject, body_html):
        if not email_to:
            return
        self.env['mail.mail'].sudo().create({
            'subject': subject, 'body_html': body_html,
            'email_to': email_to, 'auto_delete': True,
        })  # inviata dalla coda mail di Odoo via ir.mail_server

    @api.model
    def _cron_bo_report(self):
        """Report operatività serale: a ogni operativa il suo, ad Antonio il consolidato."""
        start, _now = self._bo_today_bounds()
        emps = self.env['hr.employee'].browse([9, 6, 3, 10]).exists()
        consolidated = []
        for emp in emps:
            s = self._bo_person_summary(emp)
            consolidated.append(s)
            email = emp.work_email or (emp.user_id.email if emp.user_id else False)
            if email:
                self._bo_send_mail(email, _("BackOperation — la tua giornata"),
                                   self._bo_person_html(s))
        # consolidato Antonio
        tot_done = sum(s['done_count'] for s in consolidated)
        # ordini preparati / tracking mancanti
        orders_today = self.search([('bo_kind', 'in', ['ordine', 'campionatura']),
                                    ('bo_firma_at', '>=', start), ('state', '=', 'chiuso')])
        missing_track = 0
        for t in orders_today:
            so = t.bo_sale_order_id
            if so:
                pk = so.picking_ids.filtered(lambda p: p.picking_type_id.code == 'outgoing')[:1]
                if pk and not pk.carrier_tracking_ref:
                    missing_track += 1
        body = "<p>Report operatività BackOperation — %s</p><ul>" % fields.Date.context_today(self)
        for s in consolidated:
            body += _("<li><b>%s</b>: %s task, %.1f h lavorate, giornata %.1f h%s</li>") % (
                s['employee'].name, s['done_count'], s['worked_h'], s['day_hours'],
                _(" (aperta)") if s['day_open'] else '')
        body += "</ul><p>Totale task: <b>%s</b> · Ordini/campionature chiusi: <b>%s</b> · Tracking mancanti: <b>%s</b></p>" % (
            tot_done, len(orders_today), missing_track)
        antonio = self.env['res.users'].browse(ANTONIO_USER_ID)
        extra = self.env['ir.config_parameter'].sudo().get_param(REPORT_PARAM, '')
        email_ant = (antonio.email if antonio.exists() else '') or extra
        if email_ant:
            self._bo_send_mail(email_ant, _("BackOperation — consolidato giornaliero"), body)
        _logger.info("BO report inviato: %s persone, %s task, %s tracking mancanti",
                     len(consolidated), tot_done, missing_track)
        return True


def _bo_setup_cron(env):
    """Crea (idempotente) la scheduled action report 18:00, via ORM (no XML)."""
    Cron = env['ir.cron'].sudo()
    existing = Cron.search([('name', '=', 'BackOperation: report 18:00')], limit=1)
    if existing:
        return
    model = env['ir.model'].sudo().search([('model', '=', 'cf.task')], limit=1)
    now = fields.Datetime.now()
    nextcall = now.replace(hour=18, minute=0, second=0, microsecond=0)
    if nextcall < now:
        nextcall = nextcall + timedelta(days=1)
    Cron.create({
        'name': 'BackOperation: report 18:00',
        'model_id': model.id,
        'state': 'code',
        'code': "model._cron_bo_report()",
        'interval_number': 1,
        'interval_type': 'days',
        'nextcall': fields.Datetime.to_string(nextcall),
        'active': True,
    })
    _logger.info("Cron BackOperation report 18:00 creato (nextcall %s)", nextcall)


def post_init_hook(env):
    _bo_setup_cron(env)
