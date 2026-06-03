# -*- coding: utf-8 -*-
from odoo import models, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class CFHomeKpi(models.AbstractModel):
    _name = 'cf.home.kpi'
    _description = 'CasaFolino Home KPI helper'

    @api.model
    def cf_get_kpi_commerciale(self):
        result = {}

        # Mail in attesa di posizionamento
        try:
            result['mail_pending'] = self.env['casafolino.mail.message'].search_count([
                ('cf_project_id', '=', False),
                ('partner_id', '!=', False),
            ])
        except Exception as e:
            _logger.warning("HOME KPI mail_pending failed: %s", e)
            result['mail_pending'] = None

        # Lead aperti
        try:
            result['lead_aperti'] = self.env['crm.lead'].search_count([
                ('type', '=', 'lead'),
                ('active', '=', True),
                ('probability', '<', 100),
            ])
        except Exception as e:
            _logger.warning("HOME KPI lead_aperti failed: %s", e)
            result['lead_aperti'] = None

        # Lead caldi (probability >= 70%)
        try:
            result['lead_caldi'] = self.env['crm.lead'].search_count([
                ('type', '=', 'lead'),
                ('active', '=', True),
                ('probability', '>=', 70),
            ])
        except Exception:
            result['lead_caldi'] = None

        # Progetti/dossier attivi
        try:
            result['progetti_attivi'] = self.env['project.project'].search_count([
                ('cf_status_dossier', '!=', False),
                ('active', '=', True),
            ])
        except Exception:
            result['progetti_attivi'] = None

        # SLA buyer in scadenza (mail tracked senza risposta > 48h)
        try:
            sla_threshold = datetime.now() - timedelta(hours=48)
            result['sla_scadenza'] = self.env['casafolino.mail.message'].search_count([
                ('cf_project_id', '!=', False),
                ('email_date', '<=', sla_threshold),
            ])
        except Exception:
            result['sla_scadenza'] = None

        # Fatturato mese corrente
        try:
            month_start = datetime.now().replace(day=1).date()
            invoices = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', month_start),
            ])
            result['fatturato_mese'] = sum(invoices.mapped('amount_total'))
            result['currency'] = invoices[0].currency_id.symbol if invoices else '€'
        except Exception as e:
            _logger.warning("HOME KPI fatturato failed: %s", e)
            result['fatturato_mese'] = None
            result['currency'] = '€'

        return result

    @api.model
    def cf_get_kpi_operativa(self):
        result = {}

        # Lotti in produzione
        try:
            Lot = self.env.get('stock.lot')
            if Lot is not None:
                result['lotti_produzione'] = Lot.search_count([])
            else:
                result['lotti_produzione'] = None
        except Exception:
            result['lotti_produzione'] = None

        # HACCP scadenze < 7gg
        try:
            Reminder = self.env.get('cf.haccp.reminder')
            if Reminder is not None:
                threshold = (datetime.now() + timedelta(days=7)).date()
                result['haccp_scadenze'] = Reminder.search_count([
                    ('next_date', '<=', threshold),
                    ('active', '=', True),
                ])
            else:
                result['haccp_scadenze'] = None
        except Exception:
            result['haccp_scadenze'] = None

        # NC aperte
        try:
            NC = self.env.get('cf.haccp.nc')
            if NC is not None:
                result['nc_aperte'] = NC.search_count([
                    ('state', 'not in', ['closed', 'done']),
                ])
            else:
                result['nc_aperte'] = None
        except Exception:
            result['nc_aperte'] = None

        # Produzioni attive
        try:
            Job = self.env.get('cf.production.job')
            if Job is not None:
                result['produzioni_attive'] = Job.search_count([
                    ('state', 'not in', ['done', 'cancel']),
                ])
            else:
                result['produzioni_attive'] = None
        except Exception:
            result['produzioni_attive'] = None

        # Lotti in scadenza < 30gg
        try:
            Lot = self.env.get('stock.lot')
            if Lot is not None:
                today = datetime.now().date()
                threshold = (datetime.now() + timedelta(days=30)).date()
                result['lotti_scadenza'] = Lot.search_count([
                    ('expiration_date', '<=', threshold),
                    ('expiration_date', '>=', today),
                ])
            else:
                result['lotti_scadenza'] = None
        except Exception:
            result['lotti_scadenza'] = None

        return result

    @api.model
    def cf_get_kpi_admin(self):
        result = {'currency': '€'}

        # Casse (journal balance)
        for label, journal_id in [('cassa_qonto', 6), ('cassa_revolut', 13), ('cassa_bcc', 22)]:
            try:
                journal = self.env['account.journal'].browse(journal_id)
                if journal.exists():
                    result[label] = self._get_journal_balance(journal)
                else:
                    result[label] = None
            except Exception as e:
                _logger.warning("HOME KPI %s failed: %s", label, e)
                result[label] = None

        # Fatture aperte
        try:
            result['fatture_aperte'] = self.env['account.move'].search_count([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
            ])
        except Exception:
            result['fatture_aperte'] = None

        # Prossima fiera
        try:
            Fair = self.env.get('cf.export.fair')
            if Fair is not None:
                upcoming = Fair.search([
                    ('date_start', '>=', datetime.now().date()),
                ], order='date_start asc', limit=1)
                if not upcoming:
                    upcoming = Fair.search([], order='date_start desc', limit=1)
                result['prossima_fiera'] = upcoming.name[:30] if upcoming and upcoming.name else 'nessuna'
            else:
                events = self.env['calendar.event'].search([
                    ('start', '>=', datetime.now()),
                    '|', '|', '|',
                    ('name', 'ilike', 'fiera'), ('name', 'ilike', 'SIAL'),
                    ('name', 'ilike', 'Anuga'), ('name', 'ilike', 'Tuttofood'),
                ], order='start asc', limit=1)
                result['prossima_fiera'] = events.name[:30] if events else 'nessuna'
        except Exception:
            result['prossima_fiera'] = None

        return result

    def _get_journal_balance(self, journal):
        if not journal.default_account_id:
            return 0.0
        self.env.cr.execute("""
            SELECT COALESCE(SUM(balance), 0)
            FROM account_move_line
            WHERE account_id = %s
              AND parent_state = 'posted'
        """, (journal.default_account_id.id,))
        row = self.env.cr.fetchone()
        return row[0] if row else 0.0

    @api.model
    def cf_get_kpi_haccp(self):
        result = {}

        # HACCP scadenze < 7gg
        try:
            Reminder = self.env.get('cf.haccp.reminder')
            if Reminder is not None:
                threshold = (datetime.now() + timedelta(days=7)).date()
                result['haccp_scadenze'] = Reminder.search_count([
                    ('next_date', '<=', threshold),
                    ('active', '=', True),
                ])
            else:
                result['haccp_scadenze'] = None
        except Exception:
            result['haccp_scadenze'] = None

        # NC aperte
        try:
            NC = self.env.get('cf.haccp.nc')
            if NC is not None:
                result['nc_aperte'] = NC.search_count([
                    ('state', 'not in', ['closed', 'done']),
                ])
            else:
                result['nc_aperte'] = None
        except Exception:
            result['nc_aperte'] = None

        # Calibrazioni in scadenza < 30gg
        try:
            Cal = self.env.get('cf.haccp.calibration')
            if Cal is not None:
                threshold = (datetime.now() + timedelta(days=30)).date()
                result['calibrazioni_scadenza'] = Cal.search_count([
                    ('next_calibration', '<=', threshold),
                    ('active', '=', True),
                ])
            else:
                result['calibrazioni_scadenza'] = None
        except Exception:
            result['calibrazioni_scadenza'] = None

        # Quarantena attivi
        try:
            Quar = self.env.get('cf.haccp.quarantine')
            if Quar is not None:
                result['quarantena_attivi'] = Quar.search_count([
                    ('state', 'not in', ['released', 'destroyed']),
                ])
            else:
                result['quarantena_attivi'] = None
        except Exception:
            result['quarantena_attivi'] = None

        return result

    @api.model
    def cf_get_kpi_all(self):
        return {
            'commerciale': self.cf_get_kpi_commerciale(),
            'operativa': self.cf_get_kpi_operativa(),
            'haccp': self.cf_get_kpi_haccp(),
            'admin': self.cf_get_kpi_admin(),
        }

    @api.model
    def cf_cleanup_legacy_model_declarations(self):
        legacy_models = (
            'casafolino.task',
            'casafolino.b2b.approve.wizard',
            'casafolino.fair.report.wizard',
        )
        self.env.cr.execute(
            """
            DELETE FROM ir_model_data
             WHERE (model = 'ir.model.fields' AND res_id IN (
                       SELECT id FROM ir_model_fields WHERE model = ANY(%s)
                   ))
                OR (model = 'ir.model' AND res_id IN (
                       SELECT id FROM ir_model WHERE model = ANY(%s)
                   ))
            """,
            (list(legacy_models), list(legacy_models)),
        )
        self.env.cr.execute(
            "DELETE FROM ir_model_fields WHERE model = ANY(%s)",
            (list(legacy_models),),
        )
        self.env.cr.execute(
            "DELETE FROM ir_model WHERE model = ANY(%s)",
            (list(legacy_models),),
        )
        _logger.info("Cleaned stale legacy model declarations: %s", ", ".join(legacy_models))
