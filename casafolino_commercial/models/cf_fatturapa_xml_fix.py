import base64
import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


_logger = logging.getLogger(__name__)
CF_XML_ROUNDING_LINE_NAME = "Arrotondamento XML FatturaPA"


class AccountMove(models.Model):
    _inherit = "account.move"

    cf_fatturapa_xml_amount_total = fields.Monetary(
        string="Totale XML FatturaPA",
        readonly=True,
        copy=False,
    )
    cf_fatturapa_xml_check_state = fields.Selection(
        [
            ("not_checked", "Non verificato"),
            ("matched", "Corrisponde"),
            ("mismatch", "Differenza XML"),
            ("missing_xml", "XML non trovato"),
        ],
        string="Controllo XML FatturaPA",
        default="not_checked",
        readonly=True,
        copy=False,
    )
    cf_fatturapa_xml_check_message = fields.Text(
        string="Esito controllo XML FatturaPA",
        readonly=True,
        copy=False,
    )

    @api.model
    def _cf_decimal(self, value, default=None):
        if value in (None, False, ""):
            return default
        try:
            return Decimal(str(value).strip())
        except (InvalidOperation, ValueError):
            return default

    @api.model
    def _cf_xml_text(self, element, xpath):
        found = element.xpath(xpath)
        if not found:
            return False
        text = found[0].text
        return text.strip() if text else False

    @api.model
    def _cf_money_round(self, amount):
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @api.model
    def _cf_balance_line_vals(self, amount):
        amount = float(amount)
        return {
            "debit": amount if amount > 0 else 0.0,
            "credit": -amount if amount < 0 else 0.0,
            "amount_currency": amount,
        }

    @api.model
    def _cf_is_europa_commerciale_partner(self, partner):
        partner = partner.commercial_partner_id
        return partner.vat == "IT03201710799" or partner.l10n_it_codice_fiscale == "03201710799"

    def _cf_get_fatturapa_xml_attachment_content(self):
        self.ensure_one()
        attachment = self.env["ir.attachment"].search([
            ("res_model", "=", "account.move"),
            ("res_id", "=", self.id),
            "|",
            ("mimetype", "=", "text/xml"),
            ("name", "ilike", ".xml"),
        ], order="create_date desc, id desc", limit=1)
        if not attachment:
            return False
        if attachment.db_datas:
            return base64.b64decode(attachment.db_datas)
        if attachment.store_fname:
            return attachment._file_read(attachment.store_fname)
        return False

    @api.model
    def _cf_parse_fatturapa_xml(self, xml_content):
        if not xml_content:
            return {}
        try:
            root = etree.fromstring(xml_content)
        except etree.XMLSyntaxError:
            _logger.warning("CF FatturaPA XML: allegato XML non parsabile.")
            return {}
        body = root.xpath(".//*[local-name()='FatturaElettronicaBody']")
        body = body[0] if body else root

        lines = []
        for element in body.xpath(".//*[local-name()='DettaglioLinee']"):
            quantity = self._cf_decimal(self._cf_xml_text(element, ".//*[local-name()='Quantita']"), Decimal("1"))
            price_total = self._cf_decimal(self._cf_xml_text(element, ".//*[local-name()='PrezzoTotale']"))
            tax_rate = self._cf_decimal(self._cf_xml_text(element, ".//*[local-name()='AliquotaIVA']"))
            sequence = self._cf_decimal(self._cf_xml_text(element, ".//*[local-name()='NumeroLinea']"))
            lines.append({
                "sequence": int(sequence) if sequence is not None else len(lines) + 1,
                "name": " ".join((self._cf_xml_text(element, ".//*[local-name()='Descrizione']") or "").split()),
                "quantity": quantity,
                "price_total": price_total,
                "tax_rate": tax_rate,
            })

        summaries = []
        for element in body.xpath(".//*[local-name()='DatiRiepilogo']"):
            summaries.append({
                "tax_rate": self._cf_decimal(self._cf_xml_text(element, ".//*[local-name()='AliquotaIVA']")),
                "base": self._cf_decimal(self._cf_xml_text(element, ".//*[local-name()='ImponibileImporto']")),
                "tax": self._cf_decimal(self._cf_xml_text(element, ".//*[local-name()='Imposta']")),
            })

        total = self._cf_decimal(self._cf_xml_text(body, ".//*[local-name()='ImportoTotaleDocumento']"))
        return {
            "lines": lines,
            "summaries": summaries,
            "amount_total": total,
        }

    @api.model
    def _cf_tax_name_text(self, tax):
        name = tax.name
        if isinstance(name, dict):
            return " ".join(value for value in name.values() if value)
        return name or ""

    @api.model
    def _cf_preferred_fatturapa_vat_tax(self, company, percentage, tax_use="purchase", l10n_it_exempt_reason=False):
        percentage = float(percentage)
        domain = [
            *self.env["account.tax"]._check_company_domain(company),
            ("active", "=", True),
            ("amount_type", "=", "percent"),
            ("amount", "=", percentage),
            ("type_tax_use", "=", tax_use),
            ("l10n_it_exempt_reason", "=", l10n_it_exempt_reason or False),
        ]
        Tax = self.env["account.tax"]
        if "l10n_it_withholding_type" in Tax._fields:
            domain.append(("l10n_it_withholding_type", "=", False))
        if "l10n_it_pension_fund_type" in Tax._fields:
            domain.append(("l10n_it_pension_fund_type", "=", False))

        taxes = Tax.search(domain).filtered(
            lambda tax: all(line.factor_percent >= 0 for line in tax.invoice_repartition_line_ids)
        )
        if not taxes:
            return Tax

        def score(tax):
            name = self._cf_tax_name_text(tax).lower()
            value = 0
            if tax.tax_scope == "consu":
                value += 100
            if " g" in name or " m" in name:
                value += 20
            if "deposito" in name or " d" in name:
                value -= 40
            if " rc" in name or " ic" in name:
                value -= 80
            if "cassa" in name or "inps" in name or "f.pens" in name:
                value -= 100
            return value

        return taxes.sorted(lambda tax: (-score(tax), tax.sequence, tax.id))[:1]

    def _l10n_it_edi_search_tax_for_import(
        self,
        company,
        percentage,
        extra_domain=None,
        vat_only=True,
        l10n_it_exempt_reason=None,
    ):
        taxes = super()._l10n_it_edi_search_tax_for_import(
            company,
            percentage,
            extra_domain=extra_domain,
            vat_only=vat_only,
            l10n_it_exempt_reason=l10n_it_exempt_reason,
        )
        if not vat_only:
            return taxes
        if len(taxes) == 1:
            return taxes

        tax_use = "purchase"
        for item in extra_domain or []:
            if len(item) >= 3 and item[0] == "type_tax_use" and item[1] == "=":
                tax_use = item[2]
                break

        fallback = self._cf_preferred_fatturapa_vat_tax(
            company,
            percentage,
            tax_use=tax_use,
            l10n_it_exempt_reason=l10n_it_exempt_reason,
        )
        return fallback or taxes

    def _l10n_it_edi_import_line(self, element, move_line, extra_info=None):
        messages = super()._l10n_it_edi_import_line(element, move_line, extra_info=extra_info)
        extra_info = extra_info or {}
        if extra_info.get("simplified"):
            return messages

        quantity = self._cf_decimal(self._cf_xml_text(element, ".//*[local-name()='Quantita']"), Decimal("1"))
        price_total = self._cf_decimal(self._cf_xml_text(element, ".//*[local-name()='PrezzoTotale']"))
        tax_rate = self._cf_decimal(self._cf_xml_text(element, ".//*[local-name()='AliquotaIVA']"))
        line_quantity = self._cf_decimal(move_line.quantity, quantity)
        if line_quantity and price_total is not None:
            move_line.with_context(check_move_validity=False).write({
                "price_unit": float(price_total / line_quantity),
                "discount": 0.0,
                "cf_fatturapa_xml_price_total": float(price_total),
            })
        if tax_rate is not None:
            tax = self._cf_preferred_fatturapa_vat_tax(
                move_line.company_id,
                tax_rate,
                tax_use="purchase",
                l10n_it_exempt_reason=(self._cf_xml_text(element, ".//*[local-name()='Natura']") or "").upper() or False,
            )
            if tax:
                move_line.tax_ids = [(6, 0, tax.ids)]
            move_line.cf_fatturapa_xml_tax_rate = float(tax_rate)
        return messages

    def _l10n_it_edi_import_invoice(self, invoice, data, is_new):
        move = super()._l10n_it_edi_import_invoice(invoice, data, is_new)
        if move.move_type in ("in_invoice", "in_refund") and data.get("xml_tree") is not None:
            parsed = move._cf_parse_fatturapa_xml(etree.tostring(data["xml_tree"]))
            move._cf_align_fatturapa_xml_bases(parsed)
            move._cf_align_fatturapa_xml_summaries(parsed)
            move._cf_apply_fatturapa_xml_total_rounding(parsed)
            move._cf_validate_fatturapa_xml_amounts(parsed, post_message=True)
        return move

    def _cf_align_fatturapa_xml_bases(self, parsed):
        self.ensure_one()
        summaries = parsed.get("summaries") or []
        for summary in summaries:
            tax_rate = summary.get("tax_rate")
            expected_base = summary.get("base")
            if tax_rate is None or expected_base is None:
                continue

            lines = self.invoice_line_ids.filtered(
                lambda line: line.display_type == "product"
                and self._cf_decimal(line.cf_fatturapa_xml_tax_rate) == tax_rate
            ).sorted("sequence")
            if not lines:
                continue

            target = lines.filtered(lambda line: not float_is_zero(line.quantity, precision_digits=12))[-1:]
            if not target:
                continue

            for _attempt in range(5):
                current_base = self._cf_decimal(sum(lines.mapped("price_subtotal")), Decimal("0.00"))
                diff = expected_base - current_base
                if abs(diff) < Decimal("0.005"):
                    break
                quantity = self._cf_decimal(target.quantity, Decimal("1.0"))
                target.with_context(check_move_validity=False).write({
                    "price_unit": target.price_unit + float(diff / quantity),
                })
                lines.invalidate_recordset(["price_subtotal", "price_total"])
        return True

    def _cf_align_fatturapa_xml_summaries(self, parsed):
        self.ensure_one()
        summaries = parsed.get("summaries") or []
        if not summaries:
            return False

        direction = 1 if self.move_type == "in_invoice" else -1
        for summary in summaries:
            tax_rate = summary.get("tax_rate")
            tax_amount = summary.get("tax")
            if tax_rate is None or tax_amount is None:
                continue

            tax_lines = self.line_ids.filtered(
                lambda line: line.display_type == "tax"
                and line.tax_line_id
                and self._cf_decimal(line.tax_line_id.amount) == tax_rate
            )
            if len(tax_lines) != 1:
                continue

            tax_lines.with_context(check_move_validity=False).write(
                self._cf_balance_line_vals(direction * tax_amount)
            )

        term_lines = self.line_ids.filtered(lambda line: line.display_type == "payment_term")
        if len(term_lines) == 1:
            counterpart = -sum(self.line_ids.filtered(lambda line: line not in term_lines).mapped("balance"))
            term_lines.with_context(check_move_validity=False).write(
                self._cf_balance_line_vals(counterpart)
            )
        return True

    def _cf_apply_fatturapa_xml_total_rounding(self, parsed):
        self.ensure_one()
        xml_total = parsed.get("amount_total")
        if xml_total is None:
            return False

        direction = 1 if self.move_type == "in_invoice" else -1
        non_term_lines = self.line_ids.filtered(
            lambda line: line.display_type != "payment_term" and line.name != CF_XML_ROUNDING_LINE_NAME
        )
        current_total = self._cf_decimal(direction * sum(non_term_lines.mapped("balance")), Decimal("0.00"))
        diff = xml_total - current_total

        rounding_lines = self.invoice_line_ids.filtered(lambda line: line.name == CF_XML_ROUNDING_LINE_NAME)
        if abs(diff) < Decimal("0.005"):
            if rounding_lines:
                rounding_lines.with_context(check_move_validity=False).unlink()
            return True

        rounding_line = rounding_lines[:1]
        extra_rounding_lines = rounding_lines - rounding_line
        if extra_rounding_lines:
            extra_rounding_lines.with_context(check_move_validity=False).unlink()

        account = self.invoice_line_ids.filtered(
            lambda line: line.display_type == "product"
            and line.name != CF_XML_ROUNDING_LINE_NAME
            and line.account_id
        )[:1].account_id
        if not account:
            return False

        vals = {
            "name": CF_XML_ROUNDING_LINE_NAME,
            "display_type": "product",
            "account_id": account.id,
            "quantity": 1.0,
            "price_unit": float(diff),
            "discount": 0.0,
            "tax_ids": [(6, 0, [])],
            "cf_fatturapa_xml_price_total": float(diff),
            "cf_fatturapa_xml_tax_rate": 0.0,
            "sequence": max(self.invoice_line_ids.mapped("sequence") or [0]) + 1,
        }
        if rounding_line:
            rounding_line.with_context(check_move_validity=False).write(vals)
        else:
            vals["move_id"] = self.id
            self.env["account.move.line"].with_context(check_move_validity=False).create(vals)
        return True

    def _cf_validate_fatturapa_xml_amounts(self, parsed=None, post_message=False):
        for move in self:
            if not parsed:
                xml_content = move._cf_get_fatturapa_xml_attachment_content()
                if not xml_content:
                    move.write({
                        "cf_fatturapa_xml_check_state": "missing_xml",
                        "cf_fatturapa_xml_check_message": _("XML FatturaPA non trovato tra gli allegati."),
                    })
                    continue
                parsed = move._cf_parse_fatturapa_xml(xml_content)

            xml_total = parsed.get("amount_total")
            if xml_total is None:
                move.write({
                    "cf_fatturapa_xml_check_state": "missing_xml",
                    "cf_fatturapa_xml_check_message": _("ImportoTotaleDocumento non trovato nell'XML FatturaPA."),
                })
                continue

            compare = float_compare(
                move.amount_total,
                float(xml_total),
                precision_rounding=move.currency_id.rounding,
            )
            state = "matched" if compare == 0 else "mismatch"
            message = _("Totale XML: %(xml).2f; totale Odoo: %(odoo).2f.", xml=float(xml_total), odoo=move.amount_total)
            move.write({
                "cf_fatturapa_xml_amount_total": float(xml_total),
                "cf_fatturapa_xml_check_state": state,
                "cf_fatturapa_xml_check_message": message,
            })
            if post_message and state == "mismatch":
                move.message_post(body=_("Controllo FatturaPA CasaFolino: %s", message))
        return True

    def cf_action_fix_europa_commerciale_fatturapa_xml(self):
        moves = self.filtered(lambda move:
            move.move_type in ("in_invoice", "in_refund")
            and move.partner_id
            and move._cf_is_europa_commerciale_partner(move.partner_id)
        )
        if not moves:
            raise UserError(_("Seleziona fatture fornitore di EUROPA COMMERCIALE SRL."))

        fixed = moves._cf_fix_fatturapa_xml_lines()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Riallineamento XML Europa Commerciale"),
                "message": _("Fatture elaborate: %s", fixed),
                "sticky": False,
                "type": "success",
            },
        }

    def cf_action_fix_purchase_fatturapa_xml(self):
        invalid_moves = self.filtered(lambda move: move.move_type not in ("in_invoice", "in_refund"))
        if invalid_moves:
            raise UserError(_("Questa azione e' disponibile solo per fatture e note di credito fornitore."))

        moves = self.filtered(lambda move: move.move_type in ("in_invoice", "in_refund"))
        if not moves:
            raise UserError(_("Seleziona almeno una fattura fornitore."))

        fixed = moves._cf_fix_fatturapa_xml_lines(restrict_europa=False)
        skipped = len(moves) - fixed
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Ricalcolo XML acquisti"),
                "message": _("Fatture riallineate: %(fixed)s. Saltate/non modificabili: %(skipped)s.", fixed=fixed, skipped=skipped),
                "sticky": True,
                "type": "success" if fixed else "warning",
            },
        }

    def _cf_fix_fatturapa_xml_lines(self, restrict_europa=True):
        fixed_count = 0
        for move in self:
            if restrict_europa and not move._cf_is_europa_commerciale_partner(move.partner_id):
                continue
            if move.payment_state not in ("not_paid", "partial", "in_payment"):
                move.message_post(body=_("Riallineamento XML saltato: fattura gia' pagata o riconciliata."))
                continue

            xml_content = move._cf_get_fatturapa_xml_attachment_content()
            if not xml_content:
                move._cf_validate_fatturapa_xml_amounts()
                continue

            parsed = move._cf_parse_fatturapa_xml(xml_content)
            if not parsed.get("lines") and parsed.get("amount_total") is None:
                move.write({
                    "cf_fatturapa_xml_check_state": "missing_xml",
                    "cf_fatturapa_xml_check_message": _("XML FatturaPA non parsabile o vuoto."),
                })
                move.message_post(body=_("Riallineamento XML saltato: XML FatturaPA non parsabile o vuoto."))
                continue
            xml_lines = parsed.get("lines") or []
            product_lines = move.invoice_line_ids.filtered(
                lambda line: line.display_type == "product" and line.name != CF_XML_ROUNDING_LINE_NAME
            ).sorted("sequence")
            if len(xml_lines) != len(product_lines):
                move.message_post(body=_(
                    "Riallineamento XML saltato: righe XML %(xml)s, righe Odoo %(odoo)s.",
                    xml=len(xml_lines),
                    odoo=len(product_lines),
                ))
                continue

            was_posted = move.state == "posted"
            old_total = move.amount_total
            if was_posted:
                move.button_draft()

            touched = 0
            for xml_line, line in zip(xml_lines, product_lines):
                quantity = self._cf_decimal(line.quantity, xml_line["quantity"] or Decimal("1"))
                price_total = xml_line["price_total"]
                tax_rate = xml_line["tax_rate"]
                vals = {}
                if price_total is not None and not float_is_zero(float(quantity), precision_digits=12):
                    vals.update({
                        "price_unit": float(price_total / quantity),
                        "discount": 0.0,
                        "cf_fatturapa_xml_price_total": float(price_total),
                    })
                if tax_rate is not None:
                    tax = self._cf_preferred_fatturapa_vat_tax(
                        line.company_id,
                        tax_rate,
                        tax_use="purchase",
                    )
                    if tax:
                        vals["tax_ids"] = [(6, 0, tax.ids)]
                    vals["cf_fatturapa_xml_tax_rate"] = float(tax_rate)
                if vals:
                    line.with_context(check_move_validity=False).write(vals)
                    touched += 1

            move._cf_align_fatturapa_xml_bases(parsed)
            move._cf_align_fatturapa_xml_summaries(parsed)
            move._cf_apply_fatturapa_xml_total_rounding(parsed)
            if was_posted:
                move.action_post()
                move._cf_align_fatturapa_xml_bases(parsed)
                move._cf_align_fatturapa_xml_summaries(parsed)
                move._cf_apply_fatturapa_xml_total_rounding(parsed)

            move._cf_validate_fatturapa_xml_amounts(parsed=parsed)
            fixed_count += 1
            move.message_post(body=_(
                "Riallineamento XML FatturaPA completato: righe %(lines)s, totale precedente %(old).2f, totale attuale %(new).2f, totale XML %(xml).2f.",
                lines=touched,
                old=old_total,
                new=move.amount_total,
                xml=float(parsed.get("amount_total") or 0),
            ))
        return fixed_count


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    cf_fatturapa_xml_price_total = fields.Float(
        string="Totale riga XML FatturaPA",
        digits=(16, 6),
        readonly=True,
        copy=False,
    )
    cf_fatturapa_xml_tax_rate = fields.Float(
        string="Aliquota XML FatturaPA",
        digits=(16, 2),
        readonly=True,
        copy=False,
    )
