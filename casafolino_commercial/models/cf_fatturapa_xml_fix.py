import base64
import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


_logger = logging.getLogger(__name__)


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
        root = etree.fromstring(xml_content)
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
            move._cf_validate_fatturapa_xml_amounts(parsed, post_message=True)
        return move

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

    def _cf_fix_fatturapa_xml_lines(self):
        fixed_count = 0
        for move in self:
            if not move._cf_is_europa_commerciale_partner(move.partner_id):
                continue
            if move.payment_state not in ("not_paid", "partial", "in_payment"):
                move.message_post(body=_("Riallineamento XML saltato: fattura gia' pagata o riconciliata."))
                continue

            xml_content = move._cf_get_fatturapa_xml_attachment_content()
            if not xml_content:
                move._cf_validate_fatturapa_xml_amounts()
                continue

            parsed = move._cf_parse_fatturapa_xml(xml_content)
            xml_lines = parsed.get("lines") or []
            product_lines = move.invoice_line_ids.filtered(lambda line: line.display_type == "product").sorted("sequence")
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

            if was_posted:
                move.action_post()

            move._cf_validate_fatturapa_xml_amounts(parsed=parsed)
            fixed_count += 1
            move.message_post(body=_(
                "Riallineamento XML Europa Commerciale completato: righe %(lines)s, totale precedente %(old).2f, totale attuale %(new).2f, totale XML %(xml).2f.",
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
