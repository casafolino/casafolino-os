# -*- coding: utf-8 -*-
from html import escape

from odoo import models, fields, api
from datetime import datetime

class CfRecallSession(models.Model):
    _name = "cf.recall.session"
    _description = "Sessione Mock Recall"
    _inherit = ["mail.thread"]
    _order = "date_start desc"
    _rec_name = "reference"

    reference = fields.Char(required=True, copy=False, readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("cf.recall.session") or "RECALL-NUOVO")
    session_type = fields.Selection([("mock","Mock Recall"),("real","Recall Reale"),("audit","Verifica Audit")], required=True, default="mock")
    lot_id = fields.Many2one("stock.lot", string="Lotto di Partenza", required=True)
    direction = fields.Selection([("forward","Avanti"),("backward","Indietro"),("both","Entrambe")], required=True, default="both")
    date_start = fields.Datetime(default=fields.Datetime.now)
    date_end = fields.Datetime(readonly=True)
    duration_seconds = fields.Float(readonly=True)
    state = fields.Selection([("draft","Bozza"),("running","In Corso"),("done","Completata")], default="draft", tracking=True)
    operator_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    result_summary = fields.Text(readonly=True)
    production_ids = fields.Many2many("mrp.production", string="MO Coinvolti")
    lot_ids = fields.Many2many("stock.lot", "cf_recall_lot_rel", "session_id", "lot_id", string="Lotti Tracciati")
    picking_ids = fields.Many2many("stock.picking", string="Spedizioni")
    partner_ids = fields.Many2many("res.partner", string="Partner Coinvolti")
    nodes_count = fields.Integer(readonly=True)
    traceability_pct = fields.Float(
        string="Tracciabilità %", compute="_compute_traceability_pct", store=True,
        help="Target BRC: ≥99%"
    )
    notes = fields.Text()
    customer_notice_subject = fields.Char(string="Oggetto Email Cliente")
    customer_notice_html = fields.Html(
        string="Email Ufficiale Richiamo",
        sanitize=False,
        readonly=True,
    )
    gdo_notice_html = fields.Html(
        string="Avviso Stampabile GDO",
        sanitize=False,
        readonly=True,
    )

    @api.depends("lot_ids", "picking_ids", "partner_ids", "state")
    def _compute_traceability_pct(self):
        for rec in self:
            if rec.state != "done" or not rec.lot_ids:
                rec.traceability_pct = 0.0
                continue
            total_lots = len(rec.lot_ids)
            traced = len(rec.picking_ids.filtered(lambda p: p.state == "done"))
            rec.traceability_pct = min(100.0, round(traced / total_lots * 100, 1)) if total_lots else 0.0

    def action_run(self):
        self.ensure_one()
        self.state = "running"
        start = datetime.now()
        lot = self.lot_id
        productions, lots, pickings, partners = set(), set(), set(), set()
        lots.add(lot.id)
        if self.direction in ("forward","both"):
            self._trace_forward(lot, productions, lots, pickings, partners)
        if self.direction in ("backward","both"):
            self._trace_backward(lot, productions, lots, pickings, partners)
        end = datetime.now()
        duration = (end - start).total_seconds()
        self.write({
            "state": "done",
            "date_end": end,
            "duration_seconds": duration,
            "production_ids": [(6,0,list(productions))],
            "lot_ids": [(6,0,list(lots))],
            "picking_ids": [(6,0,list(pickings))],
            "partner_ids": [(6,0,list(partners))],
            "nodes_count": len(productions) + len(lots) + len(pickings),
            "result_summary": f"Completato in {duration:.1f}s. MO: {len(productions)}, Lotti: {len(lots)}, Spedizioni: {len(pickings)}, Partner: {len(partners)}",
        })
        self.action_generate_customer_documents()

    def action_generate_customer_documents(self):
        for rec in self:
            subject, mail_html, print_html = rec._build_customer_recall_documents()
            rec.write({
                "customer_notice_subject": subject,
                "customer_notice_html": mail_html,
                "gdo_notice_html": print_html,
            })

    def action_print_customer_notice(self):
        self.ensure_one()
        if not self.gdo_notice_html:
            self.action_generate_customer_documents()
        return self.env.ref("casafolino_operations.action_report_cf_recall_customer_notice").report_action(self)

    def _build_customer_recall_documents(self):
        self.ensure_one()
        company = self.env.company
        affected_products = self.production_ids.mapped("product_id") | self.lot_ids.mapped("product_id")
        products_text = self._join_names(affected_products, "Prodotti in verifica")
        lots_text = self._join_names(self.lot_ids, "Lotti in verifica")
        pickings_text = self._join_names(self.picking_ids, "Documenti in verifica")
        partners_text = self._join_names(self.partner_ids, "Destinatari in verifica")
        start = fields.Datetime.to_string(self.date_start) if self.date_start else ""
        subject = "URGENTE - Richiamo/Ritiro lotto %s - %s" % (
            self.lot_id.name or self.reference,
            company.name or "CasaFolino",
        )

        mail_html = """
            <div class="cf-recall-doc">
                <p>Gentile Cliente,</p>
                <p>
                    con la presente %(company)s comunica l'apertura di una procedura di
                    <strong>richiamo/ritiro cautelativo</strong> relativa ai prodotti e lotti indicati
                    sotto. La comunicazione e predisposta secondo le buone pratiche di gestione
                    crisi, tracciabilita e comunicazione cliente previste dagli standard IFS/BRCGS.
                </p>
                %(summary)s
                <h3>Azione richiesta immediata</h3>
                <ol>
                    <li>Sospendere immediatamente vendita, utilizzo e ulteriore distribuzione dei lotti indicati.</li>
                    <li>Identificare e segregare fisicamente lo stock presente presso magazzini, punti vendita e piattaforme.</li>
                    <li>Comunicare entro 24 ore quantita ricevute, quantita vendute, quantita residue e ubicazioni.</li>
                    <li>Non distruggere o rendere il prodotto senza istruzioni scritte di %(company)s.</li>
                    <li>In caso di distribuzione a valle, inoltrare la presente comunicazione ai destinatari interessati.</li>
                </ol>
                <h3>Motivo della comunicazione</h3>
                <p>
                    Procedura aperta per verifica interna HACCP/qualita sul lotto di partenza
                    <strong>%(start_lot)s</strong>. Il motivo tecnico dettagliato deve essere confermato
                    dal Responsabile Qualita prima dell'invio definitivo al cliente.
                </p>
                <h3>Conferma richiesta</h3>
                <p>
                    Vi chiediamo di rispondere a questa email confermando presa in carico,
                    blocco dei lotti e quantita coinvolte. Conservare evidenza fotografica o documentale
                    della segregazione.
                </p>
                <p>Contatto qualita: %(operator)s</p>
                <p>Cordiali saluti,<br/>%(company)s</p>
            </div>
        """ % {
            "company": escape(company.name or "CasaFolino"),
            "summary": self._recall_summary_html(products_text, lots_text, pickings_text, partners_text, start),
            "start_lot": escape(self.lot_id.name or ""),
            "operator": escape(self.operator_id.display_name or ""),
        }

        print_html = """
            <div class="cf-recall-print">
                <h1>AVVISO DI RICHIAMO / RITIRO PRODOTTO</h1>
                <h2>Destinato a clienti, GDO, piattaforme logistiche e punti vendita</h2>
                <table>
                    <tr><th>Emittente</th><td>%(company)s</td></tr>
                    <tr><th>Riferimento recall</th><td>%(reference)s</td></tr>
                    <tr><th>Data apertura</th><td>%(start)s</td></tr>
                    <tr><th>Lotto di partenza</th><td>%(start_lot)s</td></tr>
                    <tr><th>Prodotti coinvolti</th><td>%(products)s</td></tr>
                    <tr><th>Lotti coinvolti</th><td>%(lots)s</td></tr>
                    <tr><th>Documenti vendita/spedizione</th><td>%(pickings)s</td></tr>
                    <tr><th>Clienti/Destinatari</th><td>%(partners)s</td></tr>
                </table>
                <h3>Istruzioni operative obbligatorie</h3>
                <ul>
                    <li>Bloccare immediatamente vendita, esposizione, preparazione e spedizione dei lotti indicati.</li>
                    <li>Segregare il prodotto in area identificata come "NON UTILIZZARE - RICHIAMO/RITIRO".</li>
                    <li>Registrare giacenze, ubicazioni, eventuali vendite gia effettuate e destinatari successivi.</li>
                    <li>Inviare conferma scritta a %(company)s entro 24 ore.</li>
                    <li>Attendere istruzioni scritte per reso, smaltimento o altra disposizione.</li>
                </ul>
                <h3>Spazio per compilazione cliente/GDO</h3>
                <table>
                    <tr><th>Quantita ricevuta</th><td></td></tr>
                    <tr><th>Quantita venduta/distribuita</th><td></td></tr>
                    <tr><th>Quantita bloccata</th><td></td></tr>
                    <tr><th>Ubicazione merce</th><td></td></tr>
                    <tr><th>Responsabile punto vendita/piattaforma</th><td></td></tr>
                    <tr><th>Data e firma</th><td></td></tr>
                </table>
                <p class="cf-recall-footer">
                    Documento generato da CasaFolino OS per gestione richiamo/ritiro secondo piano HACCP,
                    tracciabilita e prassi IFS/BRCGS. Verificare e completare il motivo tecnico prima dell'invio esterno.
                </p>
            </div>
        """ % {
            "company": escape(company.name or "CasaFolino"),
            "reference": escape(self.reference or ""),
            "start": escape(start),
            "start_lot": escape(self.lot_id.name or ""),
            "products": escape(products_text),
            "lots": escape(lots_text),
            "pickings": escape(pickings_text),
            "partners": escape(partners_text),
        }
        return subject, mail_html, print_html

    def _join_names(self, records, empty):
        names = [name for name in records.mapped("display_name") if name]
        return ", ".join(sorted(set(names))) or empty

    def _recall_summary_html(self, products, lots, pickings, partners, start):
        return """
            <table border="1" cellpadding="6" cellspacing="0">
                <tr><th>Riferimento</th><td>%s</td></tr>
                <tr><th>Data apertura</th><td>%s</td></tr>
                <tr><th>Prodotti</th><td>%s</td></tr>
                <tr><th>Lotti</th><td>%s</td></tr>
                <tr><th>Documenti</th><td>%s</td></tr>
                <tr><th>Destinatari</th><td>%s</td></tr>
            </table>
        """ % (
            escape(self.reference or ""),
            escape(start or ""),
            escape(products),
            escape(lots),
            escape(pickings),
            escape(partners),
        )

    def _trace_forward(self, lot, productions, lots, pickings, partners):
        mos = self.env["mrp.production"].search([("lot_producing_id","=",lot.id)])
        for mo in mos:
            productions.add(mo.id)
            for move_line in mo.move_finished_ids.mapped("move_line_ids"):
                if move_line.lot_id:
                    lots.add(move_line.lot_id.id)
        outgoing = self.env["stock.picking"].search([
            ("state","=","done"),("picking_type_code","=","outgoing"),
            ("move_line_ids.lot_id","=",lot.id)])
        for pick in outgoing:
            pickings.add(pick.id)
            if pick.partner_id: partners.add(pick.partner_id.id)

    def _trace_backward(self, lot, productions, lots, pickings, partners):
        move_lines = self.env["stock.move.line"].search([("lot_id","=",lot.id)])
        for ml in move_lines:
            if ml.production_id:
                productions.add(ml.production_id.id)
                for comp_line in ml.production_id.move_raw_ids.mapped("move_line_ids"):
                    if comp_line.lot_id: lots.add(comp_line.lot_id.id)
        incoming = self.env["stock.picking"].search([
            ("state","=","done"),("picking_type_code","=","incoming"),
            ("move_line_ids.lot_id","=",lot.id)])
        for pick in incoming:
            pickings.add(pick.id)
            if pick.partner_id: partners.add(pick.partner_id.id)
