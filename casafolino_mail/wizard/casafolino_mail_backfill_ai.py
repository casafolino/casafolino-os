import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

# Groq pricing (llama-3.3-70b-versatile, as of 2025)
_GROQ_PRICE_INPUT_PER_M = 0.59   # USD per 1M input tokens
_GROQ_PRICE_OUTPUT_PER_M = 0.79  # USD per 1M output tokens
_AVG_INPUT_TOKENS = 600   # average per email (subject + 2000 chars body)
_AVG_OUTPUT_TOKENS = 80   # JSON output ~80 tokens


class CasafolinoMailBackfillAiWizard(models.TransientModel):
    _name = 'casafolino.mail.backfill.ai.wizard'
    _description = 'Backfill AI Classification Wizard'

    date_from = fields.Date('Da data')
    date_to = fields.Date('A data')
    account_ids = fields.Many2many('casafolino.mail.account', string='Account')
    max_messages = fields.Integer('Max messaggi', default=500)
    estimated_count = fields.Integer('Messaggi stimati', readonly=True)
    estimated_cost_eur = fields.Float('Costo stimato (EUR)', readonly=True, digits=(10, 2))
    state = fields.Selection([
        ('draft', 'Configurazione'),
        ('estimated', 'Stimato'),
        ('running', 'In esecuzione'),
        ('done', 'Completato'),
    ], default='draft')
    result_message = fields.Text('Risultato', readonly=True)

    def _build_domain(self):
        domain = [
            ('ai_classified_at', '=', False),
            ('ai_error', 'in', [False, '', 'Rate limit 429']),
            ('body_downloaded', '=', True),
            '|', ('body_html', '!=', False), ('body_plain', '!=', False),
        ]
        if self.date_from:
            domain.append(('email_date', '>=', fields.Datetime.to_datetime(self.date_from)))
        if self.date_to:
            domain.append(('email_date', '<=', fields.Datetime.to_datetime(self.date_to)))
        if self.account_ids:
            domain.append(('account_id', 'in', self.account_ids.ids))
        return domain

    def action_estimate(self):
        self.ensure_one()
        domain = self._build_domain()
        count = self.env['casafolino.mail.message'].search_count(domain)
        if self.max_messages and count > self.max_messages:
            count = self.max_messages

        # Cost estimate in USD then convert to EUR (~0.92)
        input_cost = (count * _AVG_INPUT_TOKENS / 1_000_000) * _GROQ_PRICE_INPUT_PER_M
        output_cost = (count * _AVG_OUTPUT_TOKENS / 1_000_000) * _GROQ_PRICE_OUTPUT_PER_M
        total_usd = input_cost + output_cost
        total_eur = total_usd * 0.92

        self.write({
            'estimated_count': count,
            'estimated_cost_eur': round(total_eur, 2),
            'state': 'estimated',
        })
        return self._reopen()

    def action_run_backfill(self):
        self.ensure_one()
        domain = self._build_domain()
        limit = self.max_messages or 500
        messages = self.env['casafolino.mail.message'].search(
            domain, limit=limit, order='id desc')

        if not messages:
            self.write({
                'state': 'done',
                'result_message': 'Nessun messaggio da classificare.',
            })
            return self._reopen()

        import time
        success = 0
        failed = 0
        for idx, msg in enumerate(messages):
            try:
                msg._classify_with_groq()
                if msg.ai_classified_at:
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                _logger.warning("[backfill_ai wizard] error msg %s: %s", msg.id, e)
                failed += 1
            self.env.cr.commit()
            if idx < len(messages) - 1:
                time.sleep(0.2)

        self.write({
            'state': 'done',
            'result_message': 'Completato: %d/%d classificati, %d errori.' % (
                success, len(messages), failed),
        })
        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
