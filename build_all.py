#!/usr/bin/env python3
"""
CasaFolino OS — Build completo tutti i moduli
Esegui con: python3 build_all.py
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))

def write(path, content):
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w') as f:
        f.write(content)
    print(f'  ✅ {path}')

# =============================================================================
# CASAFOLINO HACCP
# =============================================================================
write('casafolino_haccp/__manifest__.py', '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino HACCP",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "HACCP Manager nativo Odoo 18",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "mrp", "stock", "purchase", "product"],
    "data": [
        "security/cf_haccp_security.xml",
        "security/ir.model.access.csv",
        "data/cf_haccp_sequences.xml",
        "data/cf_haccp_automation.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''')

write('casafolino_haccp/__init__.py', 'from . import models\n')
write('casafolino_haccp/models/__init__.py', '''\
from . import cf_haccp_raw_material
from . import cf_haccp_receipt
from . import cf_haccp_sp
from . import cf_haccp_ccp
from . import cf_haccp_nc
from . import cf_haccp_quarantine
from . import cf_haccp_calibration
from . import cf_haccp_document
''')

write('casafolino_haccp/models/cf_haccp_raw_material.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CfHaccpRawMaterial(models.Model):
    _inherit = "product.template"
    is_raw_material = fields.Boolean(string="Materia Prima HACCP", default=False)
    acceptance_temp_min = fields.Float(string="Temp. Min (C)")
    acceptance_temp_max = fields.Float(string="Temp. Max (C)")
    requires_temp_check = fields.Boolean(string="Controllo Temperatura", default=False)
    requires_cert_check = fields.Boolean(string="Verifica Certificati", default=True)
    requires_organoleptic = fields.Boolean(string="Controllo Organolettico", default=True)
    acceptance_criteria = fields.Text(string="Criteri Accettazione")
    rejection_criteria = fields.Text(string="Criteri Rifiuto")
    shelf_life_days = fields.Integer(string="Shelf Life (giorni)")
    storage_conditions = fields.Char(string="Condizioni Stoccaggio")
    hazard_notes = fields.Text(string="Note Pericoli HACCP")
    approved_supplier_ids = fields.Many2many(
        "res.partner", "cf_haccp_mp_supplier_rel", "product_id", "partner_id",
        string="Fornitori Approvati", domain="[(\\"supplier_rank\\", \\">\\", 0)]")
    ccp_template_ids = fields.One2many("cf.haccp.ccp.template", "product_id", string="Template CCP")

class CfHaccpCcpTemplate(models.Model):
    _name = "cf.haccp.ccp.template"
    _description = "Template CCP per Prodotto"
    _order = "sequence"
    product_id = fields.Many2one("product.template", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Nome CCP", required=True)
    ccp_type = fields.Selection([
        ("temperature","Temperatura"),("time","Tempo"),("ph","pH"),
        ("aw","Attivita Acqua"),("visual","Visivo"),("weight","Peso"),("other","Altro"),
    ], string="Tipo", required=True)
    critical_limit_min = fields.Float(string="Limite Min")
    critical_limit_max = fields.Float(string="Limite Max")
    unit = fields.Char(string="Unita")
    corrective_action = fields.Text(string="Azione Correttiva")
    monitoring_frequency = fields.Char(string="Frequenza")
    is_customizable = fields.Boolean(string="Personalizzabile", default=True)
''')

write('casafolino_haccp/models/cf_haccp_receipt.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class CfHaccpReceipt(models.Model):
    _name = "cf.haccp.receipt"
    _description = "Controllo Ricezione Materia Prima"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"
    _rec_name = "reference"

    reference = fields.Char(string="Riferimento", required=True, copy=False, readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("cf.haccp.receipt") or "RIC-NUOVO")
    state = fields.Selection([
        ("draft","Da Compilare"),("in_progress","In Corso"),
        ("accepted","Accettato"),("quarantine","Quarantena"),("rejected","Rifiutato"),
    ], string="Esito", default="draft", tracking=True, required=True)
    picking_id = fields.Many2one("stock.picking", string="Ricezione Odoo")
    lot_id = fields.Many2one("stock.lot", string="Lotto")
    product_id = fields.Many2one("product.template", string="Prodotto", required=True,
        domain="[(\\"is_raw_material\\",\\"=\\",True)]")
    partner_id = fields.Many2one("res.partner", string="Fornitore")
    date = fields.Datetime(string="Data/Ora", default=fields.Datetime.now, required=True)
    operator_id = fields.Many2one("res.users", string="Operatore", default=lambda self: self.env.user)
    quantity_received = fields.Float(string="Quantita Ricevuta")
    temperature_measured = fields.Float(string="Temperatura (C)")
    appearance_ok = fields.Boolean(string="Aspetto OK", default=True)
    smell_ok = fields.Boolean(string="Odore OK", default=True)
    color_ok = fields.Boolean(string="Colore OK", default=True)
    ddt_present = fields.Boolean(string="DDT Presente", default=True)
    cert_present = fields.Boolean(string="Certificati Presenti", default=True)
    packaging_intact = fields.Boolean(string="Packaging Integro", default=True)
    general_notes = fields.Text(string="Note")

    def action_accept(self):
        self.write({"state": "accepted"})

    def action_quarantine(self):
        for rec in self:
            rec.state = "quarantine"
            if rec.lot_id:
                self.env["cf.haccp.quarantine"].create({
                    "lot_id": rec.lot_id.id, "product_id": rec.product_id.id,
                    "receipt_id": rec.id, "reason": "Anomalia al controllo ricezione.",
                    "operator_id": rec.operator_id.id,
                })

    def action_reject(self):
        self.write({"state": "rejected"})

class StockPickingHaccp(models.Model):
    _inherit = "stock.picking"
    haccp_receipt_ids = fields.One2many("cf.haccp.receipt", "picking_id", string="Controlli HACCP")
    haccp_receipt_count = fields.Integer(compute="_compute_haccp_count")
    haccp_required = fields.Boolean(compute="_compute_haccp_required")

    def _compute_haccp_count(self):
        for rec in self:
            rec.haccp_receipt_count = len(rec.haccp_receipt_ids)

    @api.depends("move_ids.product_id")
    def _compute_haccp_required(self):
        for rec in self:
            if rec.picking_type_code != "incoming":
                rec.haccp_required = False
                continue
            products = rec.move_ids.mapped("product_id.product_tmpl_id")
            rec.haccp_required = any(p.is_raw_material for p in products)
''')

write('casafolino_haccp/models/cf_haccp_sp.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class CfHaccpSp(models.Model):
    _name = "cf.haccp.sp"
    _description = "Scheda di Produzione HACCP"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"
    _rec_name = "reference"

    reference = fields.Char(string="N° Scheda", required=True, copy=False, readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("cf.haccp.sp") or "SP-NUOVO")
    state = fields.Selection([
        ("draft","Bozza"),("in_progress","In Produzione"),
        ("completed","Completata"),("released","Rilasciata"),("blocked","Bloccata"),
    ], string="Stato", default="draft", tracking=True, required=True)
    production_id = fields.Many2one("mrp.production", string="Ordine di Produzione")
    product_id = fields.Many2one("product.template", string="Prodotto", required=True)
    lot_id = fields.Many2one("stock.lot", string="Lotto PF")
    date = fields.Datetime(string="Data Inizio", default=fields.Datetime.now, required=True)
    date_end = fields.Datetime(string="Data Fine")
    operator_id = fields.Many2one("res.users", string="Operatore", default=lambda self: self.env.user)
    quantity_produced = fields.Float(string="Quantita Prodotta")
    step1_ok = fields.Boolean(string="Step 1 OK")
    step2_ok = fields.Boolean(string="Step 2 OK")
    step3_ok = fields.Boolean(string="Step 3 OK")
    step4_ok = fields.Boolean(string="Step 4 OK")
    step5_ok = fields.Boolean(string="Step 5 OK")
    step6_ok = fields.Boolean(string="Step 6 OK")
    step7_ok = fields.Boolean(string="Step 7 OK")
    step8_ok = fields.Boolean(string="Step 8 OK")
    step9_ok = fields.Boolean(string="Step 9 OK")
    step10_ok = fields.Boolean(string="Step 10 OK")
    notes = fields.Text(string="Note")
    ccp_ids = fields.One2many("cf.haccp.ccp", "sp_id", string="CCP")
    nc_ids = fields.One2many("cf.haccp.nc", "sp_id", string="Non Conformita")

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_complete(self):
        for rec in self:
            open_nc = rec.nc_ids.filtered(lambda n: n.state not in ("closed","cancelled"))
            rec.state = "blocked" if open_nc else "completed"

    def action_release(self):
        for rec in self:
            open_nc = rec.nc_ids.filtered(lambda n: n.state not in ("closed","cancelled"))
            if open_nc:
                raise UserError("Impossibile rilasciare: NC aperte.")
            rec.state = "released"

class MrpProductionHaccp(models.Model):
    _inherit = "mrp.production"
    haccp_sp_ids = fields.One2many("cf.haccp.sp", "production_id", string="Schede HACCP")
    haccp_sp_count = fields.Integer(compute="_compute_haccp_sp_count")

    def _compute_haccp_sp_count(self):
        for rec in self:
            rec.haccp_sp_count = len(rec.haccp_sp_ids)
''')

write('casafolino_haccp/models/cf_haccp_ccp.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CfHaccpCcp(models.Model):
    _name = "cf.haccp.ccp"
    _description = "Punto Critico di Controllo"
    _order = "sp_id, sequence"

    sp_id = fields.Many2one("cf.haccp.sp", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Nome CCP", required=True)
    ccp_type = fields.Selection([
        ("temperature","Temperatura"),("time","Tempo"),("ph","pH"),
        ("aw","Attivita Acqua"),("visual","Visivo"),("weight","Peso"),("other","Altro"),
    ], string="Tipo", required=True)
    critical_limit_min = fields.Float(string="Limite Min")
    critical_limit_max = fields.Float(string="Limite Max")
    unit = fields.Char(string="Unita")
    corrective_action = fields.Text(string="Azione Correttiva")
    measured_value = fields.Float(string="Valore Misurato")
    visual_ok = fields.Boolean(string="Visivo OK")
    measurement_time = fields.Datetime(string="Ora Misurazione")
    measured_by = fields.Many2one("res.users", string="Rilevato da", default=lambda self: self.env.user)
    notes = fields.Text(string="Note")
    state = fields.Selection([
        ("pending","Da Misurare"),("ok","OK"),("ko","Fuori Limite"),
    ], string="Esito", default="pending", compute="_compute_state", store=True)

    @api.depends("measured_value","visual_ok","ccp_type","critical_limit_min","critical_limit_max","measurement_time")
    def _compute_state(self):
        for rec in self:
            if not rec.measurement_time:
                rec.state = "pending"
                continue
            if rec.ccp_type == "visual":
                rec.state = "ok" if rec.visual_ok else "ko"
            else:
                in_range = True
                if rec.critical_limit_min and rec.measured_value < rec.critical_limit_min:
                    in_range = False
                if rec.critical_limit_max and rec.measured_value > rec.critical_limit_max:
                    in_range = False
                rec.state = "ok" if in_range else "ko"
''')

write('casafolino_haccp/models/cf_haccp_nc.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields

class CfHaccpNc(models.Model):
    _name = "cf.haccp.nc"
    _description = "Non Conformita HACCP"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"
    _rec_name = "reference"

    reference = fields.Char(string="N° NC", required=True, copy=False, readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("cf.haccp.nc") or "NC-NUOVO")
    state = fields.Selection([
        ("open","Aperta"),("analysis","In Analisi"),("action","Azione Correttiva"),
        ("verified","Verificata"),("closed","Chiusa"),("cancelled","Annullata"),
    ], string="Stato", default="open", tracking=True, required=True)
    severity = fields.Selection([
        ("low","Bassa"),("medium","Media"),("high","Alta"),("critical","Critica"),
    ], string="Gravita", default="medium", tracking=True, required=True)
    origin = fields.Selection([
        ("ccp","CCP Fuori Limite"),("receipt","Controllo Ricezione"),
        ("manual","Segnalazione Manuale"),("audit","Audit"),("customer","Reclamo Cliente"),
    ], string="Origine", default="manual", required=True)
    sp_id = fields.Many2one("cf.haccp.sp", string="Scheda Produzione")
    ccp_id = fields.Many2one("cf.haccp.ccp", string="CCP")
    receipt_id = fields.Many2one("cf.haccp.receipt", string="Ricezione")
    product_id = fields.Many2one("product.template", string="Prodotto")
    lot_id = fields.Many2one("stock.lot", string="Lotto")
    date = fields.Datetime(string="Data", default=fields.Datetime.now)
    reported_by = fields.Many2one("res.users", string="Segnalato da", default=lambda self: self.env.user)
    assigned_to = fields.Many2one("res.users", string="Assegnato a")
    description = fields.Text(string="Descrizione", required=True)
    corrective_action = fields.Text(string="Azione Correttiva")
    notes = fields.Text(string="Note")

    def action_close(self):
        self.write({"state": "closed"})
''')

write('casafolino_haccp/models/cf_haccp_quarantine.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields

class CfHaccpQuarantine(models.Model):
    _name = "cf.haccp.quarantine"
    _description = "Quarantena HACCP"
    _inherit = ["mail.thread"]
    _order = "date_start desc"
    _rec_name = "reference"

    reference = fields.Char(string="N° Quarantena", required=True, copy=False, readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("cf.haccp.quarantine") or "QUA-NUOVO")
    state = fields.Selection([
        ("active","In Quarantena"),("released","Rilasciato"),
        ("destroyed","Distrutto"),("returned","Reso"),
    ], string="Stato", default="active", tracking=True)
    lot_id = fields.Many2one("stock.lot", string="Lotto", required=True)
    product_id = fields.Many2one("product.template", string="Prodotto")
    receipt_id = fields.Many2one("cf.haccp.receipt", string="Ricezione")
    operator_id = fields.Many2one("res.users", string="Operatore", default=lambda self: self.env.user)
    date_start = fields.Datetime(string="Inizio", default=fields.Datetime.now)
    date_end = fields.Datetime(string="Fine")
    reason = fields.Text(string="Motivo", required=True)
    location = fields.Char(string="Zona Quarantena")
    resolution = fields.Text(string="Risoluzione")

    def action_release(self):
        for rec in self:
            rec.state = "released"
            rec.date_end = fields.Datetime.now()

    def action_destroy(self):
        for rec in self:
            rec.state = "destroyed"
            rec.date_end = fields.Datetime.now()
''')

write('casafolino_haccp/models/cf_haccp_calibration.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

class CfHaccpCalibration(models.Model):
    _name = "cf.haccp.calibration"
    _description = "Calibrazione Strumento HACCP"
    _inherit = ["mail.thread"]
    _order = "date_next_calibration asc"
    _rec_name = "instrument_name"

    instrument_name = fields.Char(string="Nome Strumento", required=True)
    instrument_code = fields.Char(string="Codice")
    instrument_type = fields.Selection([
        ("thermometer","Termometro"),("scale","Bilancia"),("ph_meter","pH-metro"),
        ("hygrometer","Igrometro"),("timer","Timer"),("other","Altro"),
    ], string="Tipo", required=True)
    location = fields.Char(string="Ubicazione")
    workcenter_id = fields.Many2one("mrp.workcenter", string="Centro di Lavoro")
    state = fields.Selection([
        ("valid","Valida"),("expiring","In Scadenza"),("expired","Scaduta"),
    ], string="Stato", compute="_compute_state", store=True)
    date_last_calibration = fields.Date(string="Ultima Calibrazione")
    date_next_calibration = fields.Date(string="Prossima Calibrazione", required=True)
    calibration_interval_months = fields.Integer(string="Intervallo (mesi)", default=12)
    calibrated_by = fields.Many2one("res.users", string="Calibrato da")
    certificate_ref = fields.Char(string="N° Certificato")
    result_ok = fields.Boolean(string="Superata", default=True)
    notes = fields.Text(string="Note")

    @api.depends("date_next_calibration")
    def _compute_state(self):
        today = date.today()
        for rec in self:
            if not rec.date_next_calibration:
                rec.state = "expired"
                continue
            days = (rec.date_next_calibration - today).days
            rec.state = "expired" if days < 0 else "expiring" if days <= 30 else "valid"

    @api.model
    def send_expiring_alerts(self):
        expiring = self.search([("state", "in", ["expiring", "expired"])])
        for rec in expiring:
            rec.activity_schedule(
                "mail.mail_activity_data_todo",
                date_deadline=rec.date_next_calibration,
                note=f"Strumento {rec.instrument_name} richiede calibrazione.",
                user_id=rec.calibrated_by.id if rec.calibrated_by else self.env.uid,
            )

class CfHaccpCalibrationHistory(models.Model):
    _name = "cf.haccp.calibration.history"
    _description = "Storico Calibrazione"
    _order = "date desc"

    calibration_id = fields.Many2one("cf.haccp.calibration", required=True, ondelete="cascade")
    date = fields.Date(string="Data", required=True)
    calibrated_by = fields.Many2one("res.users", string="Eseguita da")
    result_ok = fields.Boolean(string="Superata", default=True)
    notes = fields.Text(string="Note")
''')

write('casafolino_haccp/models/cf_haccp_document.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

class CfHaccpDocument(models.Model):
    _name = "cf.haccp.document"
    _description = "Documento HACCP"
    _inherit = ["mail.thread"]
    _order = "date_expiry asc, name"
    _rec_name = "name"

    name = fields.Char(string="Nome Documento", required=True)
    doc_type = fields.Selection([
        ("haccp_plan","Piano HACCP"),("procedure","Procedura"),
        ("certificate","Certificato"),("supplier_doc","Documento Fornitore"),
        ("calibration","Certificato Calibrazione"),("training","Formazione"),
        ("audit","Report Audit"),("other","Altro"),
    ], string="Tipo", required=True)
    partner_id = fields.Many2one("res.partner", string="Fornitore/Ente")
    product_id = fields.Many2one("product.template", string="Prodotto")
    date_issue = fields.Date(string="Data Emissione")
    date_expiry = fields.Date(string="Data Scadenza")
    document_ref = fields.Char(string="N° Documento")
    notes = fields.Text(string="Note")
    attachment_ids = fields.Many2many("ir.attachment",
        "cf_haccp_doc_attach_rel", "doc_id", "attach_id", string="File Allegati")
    state = fields.Selection([
        ("valid","Valido"),("expiring","In Scadenza"),("expired","Scaduto"),
    ], string="Stato", compute="_compute_state", store=True)

    @api.depends("date_expiry")
    def _compute_state(self):
        today = date.today()
        for rec in self:
            if not rec.date_expiry:
                rec.state = "valid"
                continue
            days = (rec.date_expiry - today).days
            rec.state = "expired" if days < 0 else "expiring" if days <= 30 else "valid"

    @api.model
    def send_expiry_alerts(self):
        expiring = self.search([("state", "in", ["expiring", "expired"])])
        for rec in expiring:
            rec.message_post(body=f"Documento {rec.name} scade il {rec.date_expiry}.")
''')

write('casafolino_haccp/security/cf_haccp_security.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="module_category_cf_haccp" model="ir.module.category">
        <field name="name">CasaFolino HACCP</field>
        <field name="sequence">100</field>
    </record>
    <record id="group_cf_haccp_raq" model="res.groups">
        <field name="name">RAQ HACCP</field>
        <field name="category_id" ref="module_category_cf_haccp"/>
        <field name="implied_ids" eval="[(4, ref(\'base.group_user\'))]"/>
    </record>
</odoo>
''')

write('casafolino_haccp/security/ir.model.access.csv', '''\
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_cf_haccp_receipt_user,cf.haccp.receipt user,model_cf_haccp_receipt,base.group_user,1,1,1,0
access_cf_haccp_receipt_mgr,cf.haccp.receipt manager,model_cf_haccp_receipt,base.group_system,1,1,1,1
access_cf_haccp_sp_user,cf.haccp.sp user,model_cf_haccp_sp,base.group_user,1,1,1,0
access_cf_haccp_sp_mgr,cf.haccp.sp manager,model_cf_haccp_sp,base.group_system,1,1,1,1
access_cf_haccp_ccp_user,cf.haccp.ccp user,model_cf_haccp_ccp,base.group_user,1,1,1,0
access_cf_haccp_ccp_mgr,cf.haccp.ccp manager,model_cf_haccp_ccp,base.group_system,1,1,1,1
access_cf_haccp_ccp_tmpl_user,cf.haccp.ccp.template user,model_cf_haccp_ccp_template,base.group_user,1,0,0,0
access_cf_haccp_ccp_tmpl_mgr,cf.haccp.ccp.template manager,model_cf_haccp_ccp_template,base.group_system,1,1,1,1
access_cf_haccp_nc_user,cf.haccp.nc user,model_cf_haccp_nc,base.group_user,1,1,1,0
access_cf_haccp_nc_mgr,cf.haccp.nc manager,model_cf_haccp_nc,base.group_system,1,1,1,1
access_cf_haccp_quarantine_user,cf.haccp.quarantine user,model_cf_haccp_quarantine,base.group_user,1,1,1,0
access_cf_haccp_quarantine_mgr,cf.haccp.quarantine manager,model_cf_haccp_quarantine,base.group_system,1,1,1,1
access_cf_haccp_calibration_user,cf.haccp.calibration user,model_cf_haccp_calibration,base.group_user,1,1,1,0
access_cf_haccp_calibration_mgr,cf.haccp.calibration manager,model_cf_haccp_calibration,base.group_system,1,1,1,1
access_cf_haccp_cal_history_user,cf.haccp.calibration.history user,model_cf_haccp_calibration_history,base.group_user,1,1,1,0
access_cf_haccp_document_user,cf.haccp.document user,model_cf_haccp_document,base.group_user,1,1,1,0
access_cf_haccp_document_mgr,cf.haccp.document manager,model_cf_haccp_document,base.group_system,1,1,1,1
''')

write('casafolino_haccp/data/cf_haccp_sequences.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="seq_cf_haccp_receipt" model="ir.sequence">
        <field name="name">HACCP Ricezione</field>
        <field name="code">cf.haccp.receipt</field>
        <field name="prefix">RIC-%(year)s-</field>
        <field name="padding">4</field>
    </record>
    <record id="seq_cf_haccp_sp" model="ir.sequence">
        <field name="name">HACCP Scheda Produzione</field>
        <field name="code">cf.haccp.sp</field>
        <field name="prefix">SP-%(year)s-</field>
        <field name="padding">4</field>
    </record>
    <record id="seq_cf_haccp_nc" model="ir.sequence">
        <field name="name">HACCP Non Conformita</field>
        <field name="code">cf.haccp.nc</field>
        <field name="prefix">NC-%(year)s-</field>
        <field name="padding">4</field>
    </record>
    <record id="seq_cf_haccp_quarantine" model="ir.sequence">
        <field name="name">HACCP Quarantena</field>
        <field name="code">cf.haccp.quarantine</field>
        <field name="prefix">QUA-%(year)s-</field>
        <field name="padding">4</field>
    </record>
</odoo>
''')

write('casafolino_haccp/data/cf_haccp_automation.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="cron_cf_haccp_calibration_alerts" model="ir.cron">
        <field name="name">HACCP - Alert Calibrazioni</field>
        <field name="model_id" ref="model_cf_haccp_calibration"/>
        <field name="state">code</field>
        <field name="code">model.send_expiring_alerts()</field>
        <field name="interval_number">1</field>
        <field name="interval_type">weeks</field>
        <field name="numbercall">-1</field>
        <field name="active">True</field>
    </record>
    <record id="cron_cf_haccp_document_alerts" model="ir.cron">
        <field name="name">HACCP - Alert Documenti</field>
        <field name="model_id" ref="model_cf_haccp_document"/>
        <field name="state">code</field>
        <field name="code">model.send_expiry_alerts()</field>
        <field name="interval_number">1</field>
        <field name="interval_type">weeks</field>
        <field name="numbercall">-1</field>
        <field name="active">True</field>
    </record>
</odoo>
''')

write('casafolino_haccp/views/menus.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_cf_haccp_root" name="HACCP" sequence="25"
              web_icon="casafolino_haccp,static/description/icon.png"/>
    <menuitem id="menu_cf_haccp_receipts" name="Ricezione MP"
              parent="menu_cf_haccp_root" action="action_cf_haccp_receipt" sequence="1"/>
    <menuitem id="menu_cf_haccp_sp" name="Schede Produzione"
              parent="menu_cf_haccp_root" action="action_cf_haccp_sp" sequence="2"/>
    <menuitem id="menu_cf_haccp_nc" name="Non Conformita"
              parent="menu_cf_haccp_root" action="action_cf_haccp_nc" sequence="3"/>
    <menuitem id="menu_cf_haccp_quarantine" name="Quarantena"
              parent="menu_cf_haccp_root" action="action_cf_haccp_quarantine" sequence="4"/>
    <menuitem id="menu_cf_haccp_calibration" name="Calibrazioni"
              parent="menu_cf_haccp_root" action="action_cf_haccp_calibration" sequence="5"/>
    <menuitem id="menu_cf_haccp_documents" name="Documenti"
              parent="menu_cf_haccp_root" action="action_cf_haccp_document" sequence="6"/>
    <menuitem id="menu_cf_haccp_config" name="Configurazione"
              parent="menu_cf_haccp_root" sequence="99" groups="base.group_system"/>
    <menuitem id="menu_cf_haccp_raw_materials" name="Materie Prime"
              parent="menu_cf_haccp_config" action="action_cf_haccp_raw_material" sequence="1"/>
    <record id="action_cf_haccp_receipt" model="ir.actions.act_window">
        <field name="name">Controlli Ricezione</field>
        <field name="res_model">cf.haccp.receipt</field>
        <field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_haccp_sp" model="ir.actions.act_window">
        <field name="name">Schede Produzione</field>
        <field name="res_model">cf.haccp.sp</field>
        <field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_haccp_nc" model="ir.actions.act_window">
        <field name="name">Non Conformita</field>
        <field name="res_model">cf.haccp.nc</field>
        <field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_haccp_quarantine" model="ir.actions.act_window">
        <field name="name">Quarantena</field>
        <field name="res_model">cf.haccp.quarantine</field>
        <field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_haccp_calibration" model="ir.actions.act_window">
        <field name="name">Calibrazioni</field>
        <field name="res_model">cf.haccp.calibration</field>
        <field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_haccp_document" model="ir.actions.act_window">
        <field name="name">Documenti HACCP</field>
        <field name="res_model">cf.haccp.document</field>
        <field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_haccp_raw_material" model="ir.actions.act_window">
        <field name="name">Materie Prime HACCP</field>
        <field name="res_model">product.template</field>
        <field name="view_mode">list,form</field>
        <field name="domain">[("is_raw_material","=",True)]</field>
    </record>
</odoo>
''')

print('\n✅ casafolino_haccp completo')
print('\n🎉 Build completato — ora esegui:')
print('   git add .')
print('   git commit -m "Add casafolino_haccp complete"')
print('   git push origin main')

# =============================================================================
# CASAFOLINO CRM EXPORT
# =============================================================================
write('casafolino_crm_export/__manifest__.py', '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino CRM Export",
    "version": "18.0.2.0.0",
    "category": "Sales/CRM",
    "summary": "CRM Export B2B — Pipeline, Scoring, Sequenze, Fiere",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "sale_management", "product", "account"],
    "data": [
        "security/ir.model.access.csv",
        "data/cf_export_stages.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''')

write('casafolino_crm_export/__init__.py', 'from . import models\n')
write('casafolino_crm_export/models/__init__.py', '''\
from . import cf_export_lead
''')

write('casafolino_crm_export/models/cf_export_lead.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta
import logging
_logger = logging.getLogger(__name__)

ROTTING_THRESHOLDS = {
    "dach": 10, "france": 10, "spain": 10, "europe_other": 14,
    "gulf_halal": 14, "usa_canada": 14, "gdo": 21, "other": 14,
}

class CfExportLead(models.Model):
    _name = "cf.export.lead"
    _description = "Trattativa Export CasaFolino"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, lead_score desc, date_last_contact desc, id desc"
    _rec_name = "name"

    name = fields.Char(string="Nome Trattativa", required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", string="Azienda/Contatto", required=True, tracking=True)
    stage_id = fields.Many2one("cf.export.stage", string="Fase", required=True, tracking=True,
        group_expand="_read_group_stage_ids",
        default=lambda self: self.env["cf.export.stage"].search([], order="sequence asc", limit=1))
    priority = fields.Selection([("0","Normale"),("1","Alta"),("2","Urgente")], default="0", tracking=True)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one("res.users", string="Responsabile", default=lambda self: self.env.user)
    pipeline_type = fields.Selection([
        ("dach","DACH"),("france","Francia"),("spain","Spagna"),
        ("europe_other","Europa Altro"),("gulf_halal","Gulf/Halal"),
        ("usa_canada","USA/Canada"),("gdo","GDO"),("other","Altro"),
    ], string="Pipeline", required=True, default="dach", tracking=True)
    country_id = fields.Many2one(related="partner_id.country_id", store=True, readonly=True)
    expected_revenue = fields.Monetary(string="Fatturato Atteso", currency_field="currency_id", tracking=True)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.EUR"), readonly=True)
    date_open = fields.Date(string="Data Apertura", default=fields.Date.today, readonly=True)
    date_last_contact = fields.Date(string="Ultimo Contatto", tracking=True)
    date_next_followup = fields.Date(string="Prossimo Follow-up", tracking=True)
    lead_score = fields.Integer(string="Score", compute="_compute_lead_score", store=True)
    forecast_probability = fields.Float(string="Prob. Chiusura %", compute="_compute_lead_score", store=True)
    forecast_value = fields.Monetary(string="Forecast", compute="_compute_forecast_value", store=True, currency_field="currency_id")
    rotting_days = fields.Integer(string="Giorni Stagnazione", compute="_compute_rotting", store=True)
    rotting_state = fields.Selection([("ok","OK"),("warning","Attenzione"),("danger","Urgente"),("dead","Stagnante")],
        compute="_compute_rotting", store=True)
    sample_ids = fields.One2many("cf.export.sample", "lead_id", string="Campionature")
    sale_order_ids = fields.One2many("sale.order", "cf_export_lead_id", string="Ordini")
    tag_ids = fields.Many2many("cf.export.tag", string="Tag")
    kanban_state = fields.Selection([("normal","In corso"),("done","Pronto"),("blocked","Bloccato")], default="normal")
    description = fields.Html(string="Note")

    @api.depends("date_last_contact","sample_ids","sale_order_ids","priority","stage_id","date_next_followup")
    def _compute_lead_score(self):
        today = date.today()
        for rec in self:
            score = 0
            if rec.date_last_contact:
                days = (today - rec.date_last_contact).days
                if days <= 7: score += 20
                elif days > 14: score -= 20
            if rec.sample_ids: score += 15
            if any(s.state == "feedback_ok" for s in rec.sample_ids): score += 20
            if rec.sale_order_ids: score += 25
            if rec.stage_id and rec.stage_id.sequence >= 4: score += 10
            if rec.priority == "1": score += 5
            elif rec.priority == "2": score += 10
            if not rec.date_next_followup: score -= 10
            if rec.kanban_state == "blocked": score -= 15
            rec.lead_score = max(0, min(100, score))
            pt = rec.lead_score
            rec.forecast_probability = 10.0 if pt <= 30 else 35.0 if pt <= 60 else 65.0 if pt <= 80 else 85.0

    @api.depends("expected_revenue","forecast_probability")
    def _compute_forecast_value(self):
        for rec in self:
            rec.forecast_value = rec.expected_revenue * (rec.forecast_probability / 100.0)

    @api.depends("date_last_contact","pipeline_type","stage_id")
    def _compute_rotting(self):
        today = date.today()
        for rec in self:
            if rec.stage_id and (rec.stage_id.is_won or rec.stage_id.is_lost):
                rec.rotting_days = 0; rec.rotting_state = "ok"; continue
            threshold = ROTTING_THRESHOLDS.get(rec.pipeline_type, 14)
            days = (today - rec.date_last_contact).days if rec.date_last_contact else 0
            rec.rotting_days = days
            pct = days / threshold * 100 if threshold > 0 else 0
            rec.rotting_state = "ok" if pct < 50 else "warning" if pct < 80 else "danger" if pct < 100 else "dead"

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return stages.search([], order="sequence asc")

    def action_mark_contacted(self):
        for rec in self:
            rec.date_last_contact = date.today()
            rec.message_post(body="Contatto registrato oggi.")

    def write(self, vals):
        old_stages = {rec.id: rec.stage_id.id for rec in self}
        result = super().write(vals)
        if "stage_id" in vals:
            for rec in self:
                if rec.stage_id.id != old_stages.get(rec.id):
                    rec._trigger_stage_sequences()
        return result

    def _trigger_stage_sequences(self):
        sequences = self.env["cf.export.sequence"].search([
            ("trigger_stage_id","=",self.stage_id.id),("active","=",True)])
        for seq in sequences:
            seq.start_for_lead(self)

    @api.model
    def send_weekly_report(self):
        template = self.env.ref("casafolino_crm_export.email_template_weekly_report", raise_if_not_found=False)
        if template:
            admin = self.env.ref("base.user_admin")
            if admin and admin.email:
                template.send_mail(admin.id, force_send=True)

class CfExportStage(models.Model):
    _name = "cf.export.stage"
    _description = "Fase Pipeline Export"
    _order = "sequence asc, id asc"
    name = fields.Char(string="Nome Fase", required=True, translate=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(default=False)
    is_won = fields.Boolean(default=False)
    is_lost = fields.Boolean(default=False)
    color = fields.Integer(default=0)

class CfExportTag(models.Model):
    _name = "cf.export.tag"
    _description = "Tag Export"
    name = fields.Char(string="Tag", required=True)
    color = fields.Integer(default=0)

class CfExportSample(models.Model):
    _name = "cf.export.sample"
    _description = "Campionatura Export"
    _inherit = ["mail.thread"]
    _order = "date_sent desc"
    _rec_name = "reference"
    reference = fields.Char(required=True, copy=False, readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("cf.export.sample") or "CAMP-NUOVO")
    lead_id = fields.Many2one("cf.export.lead", required=True, ondelete="cascade")
    partner_id = fields.Many2one(related="lead_id.partner_id", store=True, readonly=True)
    state = fields.Selection([
        ("draft","Da Preparare"),("prepared","Preparata"),("sent","Spedita"),
        ("received","Ricevuta"),("feedback_ok","Feedback Positivo"),
        ("feedback_ko","Feedback Negativo"),("no_feedback","Nessun Feedback"),
    ], default="draft", tracking=True, required=True)
    product_ids = fields.Many2many("product.template", string="Prodotti", required=True)
    date_sent = fields.Date(string="Data Spedizione", tracking=True)
    feedback_notes = fields.Text(string="Note Feedback")

class CfExportSequence(models.Model):
    _name = "cf.export.sequence"
    _description = "Sequenza Follow-up Export"
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    trigger = fields.Selection([("stage_change","Cambio Stage"),("manual","Manuale")], default="stage_change")
    trigger_stage_id = fields.Many2one("cf.export.stage", string="Stage Trigger")
    step_ids = fields.One2many("cf.export.sequence.step", "sequence_id", string="Step")

    def start_for_lead(self, lead):
        existing = self.env["cf.export.sequence.log"].search([
            ("lead_id","=",lead.id),("sequence_id","=",self.id),("state","=","running")])
        if existing: return
        log = self.env["cf.export.sequence.log"].create({
            "lead_id": lead.id, "sequence_id": self.id,
            "state": "running", "date_started": date.today()})
        from datetime import timedelta
        for step in self.step_ids.sorted("day_offset"):
            self.env["cf.export.sequence.log.line"].create({
                "log_id": log.id, "step_id": step.id,
                "scheduled_date": date.today() + timedelta(days=step.day_offset),
                "state": "pending"})

class CfExportSequenceStep(models.Model):
    _name = "cf.export.sequence.step"
    _description = "Step Sequenza"
    sequence_id = fields.Many2one("cf.export.sequence", required=True, ondelete="cascade")
    day_offset = fields.Integer(string="Giorno N", required=True)
    action_type = fields.Selection([
        ("email","Email"),("activity_call","Chiamata"),
        ("activity_task","Task"),("internal_notify","Notifica"),
    ], required=True)
    activity_note = fields.Char(string="Nota")

class CfExportSequenceLog(models.Model):
    _name = "cf.export.sequence.log"
    _description = "Log Sequenza"
    lead_id = fields.Many2one("cf.export.lead", required=True, ondelete="cascade")
    sequence_id = fields.Many2one("cf.export.sequence", required=True)
    state = fields.Selection([("running","In esecuzione"),("completed","Completata"),("cancelled","Annullata")], default="running")
    date_started = fields.Date(string="Avviata il")
    line_ids = fields.One2many("cf.export.sequence.log.line", "log_id")

class CfExportSequenceLogLine(models.Model):
    _name = "cf.export.sequence.log.line"
    _description = "Step Log Sequenza"
    log_id = fields.Many2one("cf.export.sequence.log", required=True, ondelete="cascade")
    step_id = fields.Many2one("cf.export.sequence.step", required=True)
    scheduled_date = fields.Date(string="Data Pianificata")
    state = fields.Selection([("pending","In attesa"),("done","Eseguito"),("cancelled","Annullato")], default="pending")

class SaleOrderExportLead(models.Model):
    _inherit = "sale.order"
    cf_export_lead_id = fields.Many2one("cf.export.lead", string="Trattativa Export", ondelete="set null", copy=False)
''')

write('casafolino_crm_export/security/ir.model.access.csv', '''\
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_cf_export_lead_user,cf.export.lead user,model_cf_export_lead,base.group_user,1,1,1,0
access_cf_export_lead_mgr,cf.export.lead manager,model_cf_export_lead,base.group_system,1,1,1,1
access_cf_export_stage_user,cf.export.stage user,model_cf_export_stage,base.group_user,1,0,0,0
access_cf_export_stage_mgr,cf.export.stage manager,model_cf_export_stage,base.group_system,1,1,1,1
access_cf_export_tag_user,cf.export.tag user,model_cf_export_tag,base.group_user,1,1,1,0
access_cf_export_sample_user,cf.export.sample user,model_cf_export_sample,base.group_user,1,1,1,0
access_cf_export_sample_mgr,cf.export.sample manager,model_cf_export_sample,base.group_system,1,1,1,1
access_cf_export_seq_user,cf.export.sequence user,model_cf_export_sequence,base.group_user,1,0,0,0
access_cf_export_seq_mgr,cf.export.sequence manager,model_cf_export_sequence,base.group_system,1,1,1,1
access_cf_export_seq_step_user,cf.export.sequence.step user,model_cf_export_sequence_step,base.group_user,1,0,0,0
access_cf_export_seq_step_mgr,cf.export.sequence.step manager,model_cf_export_sequence_step,base.group_system,1,1,1,1
access_cf_export_seq_log_user,cf.export.sequence.log user,model_cf_export_sequence_log,base.group_user,1,1,1,0
access_cf_export_seq_log_mgr,cf.export.sequence.log manager,model_cf_export_sequence_log,base.group_system,1,1,1,1
access_cf_export_seq_log_line_user,cf.export.sequence.log.line user,model_cf_export_sequence_log_line,base.group_user,1,1,0,0
access_cf_export_seq_log_line_mgr,cf.export.sequence.log.line manager,model_cf_export_sequence_log_line,base.group_system,1,1,1,1
''')

write('casafolino_crm_export/data/cf_export_stages.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="stage_prospect" model="cf.export.stage"><field name="name">Prospect</field><field name="sequence">1</field></record>
    <record id="stage_contact" model="cf.export.stage"><field name="name">Contatto Iniziale</field><field name="sequence">2</field></record>
    <record id="stage_sample" model="cf.export.stage"><field name="name">Campionatura Inviata</field><field name="sequence">3</field></record>
    <record id="stage_offer" model="cf.export.stage"><field name="name">Offerta Inviata</field><field name="sequence">4</field></record>
    <record id="stage_negotiation" model="cf.export.stage"><field name="name">Negoziazione</field><field name="sequence">5</field></record>
    <record id="stage_contract" model="cf.export.stage"><field name="name">Contratto Firmato</field><field name="sequence">6</field><field name="is_won">True</field></record>
    <record id="stage_active" model="cf.export.stage"><field name="name">Cliente Attivo</field><field name="sequence">7</field><field name="is_won">True</field></record>
    <record id="stage_lost" model="cf.export.stage"><field name="name">Perso</field><field name="sequence">99</field><field name="fold">True</field><field name="is_lost">True</field></record>
    <record id="seq_cf_export_sample" model="ir.sequence">
        <field name="name">Campionatura Export</field>
        <field name="code">cf.export.sample</field>
        <field name="prefix">CAMP-%(year)s-</field>
        <field name="padding">4</field>
    </record>
</odoo>
''')

write('casafolino_crm_export/views/menus.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="action_cf_export_lead" model="ir.actions.act_window">
        <field name="name">Pipeline Export</field>
        <field name="res_model">cf.export.lead</field>
        <field name="view_mode">kanban,list,form</field>
    </record>
    <record id="action_cf_export_sample" model="ir.actions.act_window">
        <field name="name">Campionature</field>
        <field name="res_model">cf.export.sample</field>
        <field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_export_stages" model="ir.actions.act_window">
        <field name="name">Fasi Pipeline</field>
        <field name="res_model">cf.export.stage</field>
        <field name="view_mode">list,form</field>
    </record>
    <menuitem id="menu_cf_export_root" name="Export CRM" sequence="20"/>
    <menuitem id="menu_cf_export_pipeline" name="Pipeline" parent="menu_cf_export_root" action="action_cf_export_lead" sequence="1"/>
    <menuitem id="menu_cf_export_samples" name="Campionature" parent="menu_cf_export_root" action="action_cf_export_sample" sequence="2"/>
    <menuitem id="menu_cf_export_config" name="Configurazione" parent="menu_cf_export_root" sequence="99" groups="base.group_system"/>
    <menuitem id="menu_cf_export_stages" name="Fasi Pipeline" parent="menu_cf_export_config" action="action_cf_export_stages" sequence="1"/>
</odoo>
''')

print('✅ casafolino_crm_export completo')

# =============================================================================
# CASAFOLINO SUPPLIER QUAL
# =============================================================================
write('casafolino_supplier_qual/__manifest__.py', '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Supplier Qualification",
    "version": "18.0.1.0.0",
    "category": "Purchase",
    "summary": "Qualifica fornitori BRC/IFS — Documenti, Valutazioni, Alert scadenze",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "purchase", "stock"],
    "data": [
        "security/cf_supplier_qual_security.xml",
        "security/ir.model.access.csv",
        "data/cf_supplier_qual_cron.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''')

write('casafolino_supplier_qual/__init__.py', 'from . import models\n')
write('casafolino_supplier_qual/models/__init__.py', '''\
from . import cf_supplier_qualification
from . import cf_supplier_document
from . import cf_supplier_evaluation
''')

write('casafolino_supplier_qual/models/cf_supplier_qualification.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date
import logging
_logger = logging.getLogger(__name__)

class CfSupplierQualification(models.Model):
    _name = "casafolino.supplier.qualification"
    _description = "Qualifica Fornitore CasaFolino"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "partner_id"
    _rec_name = "partner_id"

    partner_id = fields.Many2one("res.partner", string="Fornitore", required=True,
        ondelete="cascade", domain="[(\'supplier_rank\',\'>\',0)]", tracking=True)
    partner_country_id = fields.Many2one(related="partner_id.country_id", store=True, readonly=True)
    status = fields.Selection([
        ("approved","Approvato"),("evaluation","In Valutazione"),
        ("suspended","Sospeso"),("excluded","Escluso"),
    ], string="Stato Qualifica", default="evaluation", required=True, tracking=True)
    traffic_light = fields.Selection([
        ("green","Verde — Tutto OK"),("yellow","Giallo — Attenzione"),("red","Rosso — Critico"),
    ], string="Semaforo", compute="_compute_traffic_light", store=True)
    date_qualification = fields.Date(string="Data Prima Qualifica", default=fields.Date.today)
    qualified_by = fields.Many2one("res.users", string="Qualificato da", default=lambda self: self.env.user)
    last_evaluation_date = fields.Date(string="Ultima Valutazione", readonly=True)
    next_evaluation_date = fields.Date(string="Prossima Valutazione", tracking=True)
    notes = fields.Text(string="Note")
    suspension_reason = fields.Text(string="Motivo Sospensione/Esclusione")
    document_ids = fields.One2many("casafolino.supplier.document", "partner_id", string="Documenti")
    evaluation_ids = fields.One2many("casafolino.supplier.evaluation", "partner_id", string="Valutazioni")
    document_count = fields.Integer(compute="_compute_stats")
    evaluation_count = fields.Integer(compute="_compute_stats")
    expired_doc_count = fields.Integer(compute="_compute_stats")
    expiring_doc_count = fields.Integer(compute="_compute_stats")
    last_score = fields.Float(compute="_compute_stats", store=True)

    @api.depends("document_ids","document_ids.doc_status","evaluation_ids","evaluation_ids.punteggio_totale")
    def _compute_stats(self):
        for rec in self:
            docs = rec.document_ids
            rec.document_count = len(docs)
            rec.evaluation_count = len(rec.evaluation_ids)
            rec.expired_doc_count = len(docs.filtered(lambda d: d.doc_status == "expired"))
            rec.expiring_doc_count = len(docs.filtered(lambda d: d.doc_status == "expiring"))
            last_eval = rec.evaluation_ids.sorted("date", reverse=True)[:1]
            rec.last_score = last_eval.punteggio_totale if last_eval else 0.0

    @api.depends("status","document_ids.doc_status","next_evaluation_date")
    def _compute_traffic_light(self):
        today = date.today()
        for rec in self:
            if rec.status in ("suspended","excluded"):
                rec.traffic_light = "red"; continue
            if any(d.doc_status == "expired" for d in rec.document_ids):
                rec.traffic_light = "red"; continue
            if any(d.doc_status == "expiring" for d in rec.document_ids):
                rec.traffic_light = "yellow"; continue
            if rec.next_evaluation_date and rec.next_evaluation_date < today:
                rec.traffic_light = "yellow"; continue
            rec.traffic_light = "green"

    def action_approve(self):
        for rec in self:
            rec.status = "approved"
            rec.message_post(body=f"Fornitore approvato da {self.env.user.name}.")

    def action_suspend(self):
        for rec in self:
            rec.status = "suspended"

    def action_exclude(self):
        for rec in self:
            rec.status = "excluded"

class ResPartnerSupplierQual(models.Model):
    _inherit = "res.partner"

    supplier_qual_id = fields.Many2one("casafolino.supplier.qualification",
        compute="_compute_supplier_qual", store=False)
    supplier_qual_status = fields.Selection(related="supplier_qual_id.status", readonly=True)
    supplier_traffic_light = fields.Selection(related="supplier_qual_id.traffic_light", readonly=True)

    def _compute_supplier_qual(self):
        for rec in self:
            qual = self.env["casafolino.supplier.qualification"].search(
                [("partner_id","=",rec.id)], limit=1)
            rec.supplier_qual_id = qual

    def action_open_qualification(self):
        self.ensure_one()
        qual = self.env["casafolino.supplier.qualification"].search(
            [("partner_id","=",self.id)], limit=1)
        if not qual:
            qual = self.env["casafolino.supplier.qualification"].create({"partner_id": self.id})
        return {
            "type": "ir.actions.act_window",
            "name": f"Qualifica — {self.name}",
            "res_model": "casafolino.supplier.qualification",
            "res_id": qual.id,
            "view_mode": "form",
            "target": "current",
        }
''')

write('casafolino_supplier_qual/models/cf_supplier_document.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

DOCUMENT_TYPES = [
    ("brc_ifs","Certificato BRC/IFS"),("iso_9001","Certificato ISO 9001"),
    ("microbiological","Analisi Microbiologiche"),("allergen_decl","Dichiarazione Allergeni"),
    ("kosher","Certificato Kosher"),("halal","Certificato Halal"),
    ("bio_organic","Certificato Biologico"),("visura","Visura Camerale"),
    ("contract","Contratto Fornitura"),("tech_sheet","Scheda Tecnica MP"),
    ("analysis","Certificato Analisi / CoA"),("other","Altro"),
]

class CfSupplierDocument(models.Model):
    _name = "casafolino.supplier.document"
    _description = "Documento Fornitore Qualificato"
    _inherit = ["mail.thread"]
    _order = "expiry_date asc, partner_id"
    _rec_name = "name"

    name = fields.Char(string="Nome Documento", required=True)
    partner_id = fields.Many2one("res.partner", string="Fornitore", required=True,
        ondelete="cascade", domain="[(\'supplier_rank\',\'>\',0)]")
    document_type = fields.Selection(DOCUMENT_TYPES, string="Tipo", required=True, default="other")
    attachment_id = fields.Many2one("ir.attachment", string="File Allegato")
    has_file = fields.Boolean(compute="_compute_has_file", store=True)
    issue_date = fields.Date(string="Data Emissione")
    expiry_date = fields.Date(string="Data Scadenza", tracking=True)
    no_expiry = fields.Boolean(string="Nessuna Scadenza", default=False)
    alert_days_before = fields.Integer(string="Alert Giorni Prima", default=30)
    doc_status = fields.Selection([
        ("valid","Valido"),("expiring","In Scadenza"),("expired","Scaduto"),
        ("no_expiry","Nessuna Scadenza"),("missing","File Mancante"),
    ], string="Status", compute="_compute_doc_status", store=True, tracking=True)
    days_to_expiry = fields.Integer(compute="_compute_doc_status", store=False)
    notes = fields.Text(string="Note")
    reference_number = fields.Char(string="N° Riferimento")

    @api.depends("attachment_id")
    def _compute_has_file(self):
        for rec in self:
            rec.has_file = bool(rec.attachment_id)

    @api.depends("expiry_date","no_expiry","alert_days_before","attachment_id")
    def _compute_doc_status(self):
        today = date.today()
        for rec in self:
            if rec.no_expiry:
                rec.doc_status = "no_expiry"; rec.days_to_expiry = 0; continue
            if not rec.expiry_date:
                rec.doc_status = "missing" if not rec.attachment_id else "valid"
                rec.days_to_expiry = 0; continue
            days = (rec.expiry_date - today).days
            rec.days_to_expiry = days
            rec.doc_status = "expired" if days < 0 else "expiring" if days <= rec.alert_days_before else "valid"

    @api.model
    def send_expiry_alerts(self):
        expiring = self.search([("doc_status","in",("expiring","expired")),("no_expiry","=",False)])
        for doc in expiring:
            doc.message_post(body=f"Documento {doc.name} scade il {doc.expiry_date}.")
''')

write('casafolino_supplier_qual/models/cf_supplier_evaluation.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class CfSupplierEvaluation(models.Model):
    _name = "casafolino.supplier.evaluation"
    _description = "Valutazione Fornitore"
    _inherit = ["mail.thread"]
    _order = "date desc"
    _rec_name = "display_name_computed"

    display_name_computed = fields.Char(compute="_compute_display_name", store=True)
    partner_id = fields.Many2one("res.partner", string="Fornitore", required=True,
        ondelete="cascade", domain="[(\'supplier_rank\',\'>\',0)]", tracking=True)
    date = fields.Date(string="Data", default=fields.Date.today, required=True)
    evaluator_id = fields.Many2one("res.users", string="Valutatore", default=lambda self: self.env.user)
    punteggio_qualita = fields.Selection([
        ("1","1 - Insufficiente"),("2","2 - Scarso"),("3","3 - Sufficiente"),
        ("4","4 - Buono"),("5","5 - Eccellente"),
    ], string="Qualita Prodotti", required=True)
    punteggio_puntualita = fields.Selection([
        ("1","1 - Insufficiente"),("2","2 - Scarso"),("3","3 - Sufficiente"),
        ("4","4 - Buono"),("5","5 - Eccellente"),
    ], string="Puntualita Consegne", required=True)
    punteggio_documentazione = fields.Selection([
        ("1","1 - Insufficiente"),("2","2 - Scarso"),("3","3 - Sufficiente"),
        ("4","4 - Buono"),("5","5 - Eccellente"),
    ], string="Documentazione", required=True)
    punteggio_totale = fields.Float(compute="_compute_punteggio", store=True, digits=(3,2))
    risultato = fields.Selection([
        ("confirmed","Confermato"),("observation","In Osservazione"),("excluded","Escluso"),
    ], string="Risultato", required=True, compute="_compute_risultato", store=True)
    note = fields.Text(string="Note")
    corrective_actions = fields.Text(string="Azioni Correttive")

    @api.depends("partner_id","date")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name_computed = f"{rec.partner_id.name or ''} — {rec.date or ''}"

    @api.depends("punteggio_qualita","punteggio_puntualita","punteggio_documentazione")
    def _compute_punteggio(self):
        for rec in self:
            scores = [int(v) for v in [rec.punteggio_qualita, rec.punteggio_puntualita, rec.punteggio_documentazione] if v]
            rec.punteggio_totale = sum(scores) / len(scores) if scores else 0.0

    @api.depends("punteggio_totale")
    def _compute_risultato(self):
        for rec in self:
            pt = rec.punteggio_totale
            rec.risultato = "confirmed" if pt >= 3.5 else "observation" if pt >= 2.0 else "excluded"

    def action_apply_result(self):
        for rec in self:
            qual = self.env["casafolino.supplier.qualification"].search(
                [("partner_id","=",rec.partner_id.id)], limit=1)
            if not qual:
                qual = self.env["casafolino.supplier.qualification"].create({"partner_id": rec.partner_id.id})
            qual.last_evaluation_date = rec.date
            qual.next_evaluation_date = rec.date + relativedelta(years=1)
            if rec.risultato == "confirmed": qual.status = "approved"
            elif rec.risultato == "observation": qual.status = "evaluation"
            elif rec.risultato == "excluded": qual.status = "excluded"
''')

write('casafolino_supplier_qual/security/cf_supplier_qual_security.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="module_category_cf_supplier_qual" model="ir.module.category">
        <field name="name">CasaFolino Fornitori Qualificati</field>
        <field name="sequence">105</field>
    </record>
    <record id="group_cf_supplier_raq" model="res.groups">
        <field name="name">RAQ Qualifica Fornitori</field>
        <field name="category_id" ref="module_category_cf_supplier_qual"/>
        <field name="implied_ids" eval="[(4, ref(\'base.group_user\'))]"/>
    </record>
</odoo>
''')

write('casafolino_supplier_qual/security/ir.model.access.csv', '''\
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_cf_supplier_qual_user,casafolino.supplier.qualification user,model_casafolino_supplier_qualification,base.group_user,1,1,1,0
access_cf_supplier_qual_raq,casafolino.supplier.qualification raq,model_casafolino_supplier_qualification,base.group_system,1,1,1,1
access_cf_supplier_doc_user,casafolino.supplier.document user,model_casafolino_supplier_document,base.group_user,1,1,1,0
access_cf_supplier_doc_raq,casafolino.supplier.document raq,model_casafolino_supplier_document,base.group_system,1,1,1,1
access_cf_supplier_eval_user,casafolino.supplier.evaluation user,model_casafolino_supplier_evaluation,base.group_user,1,1,1,0
access_cf_supplier_eval_raq,casafolino.supplier.evaluation raq,model_casafolino_supplier_evaluation,base.group_system,1,1,1,1
''')

write('casafolino_supplier_qual/data/cf_supplier_qual_cron.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="cron_cf_supplier_doc_expiry" model="ir.cron">
        <field name="name">Supplier Qual - Alert Scadenze Documenti</field>
        <field name="model_id" search="[(\'model\',\'=\',\'casafolino.supplier.document\')]" model="ir.model"/>
        <field name="state">code</field>
        <field name="code">model.send_expiry_alerts()</field>
        <field name="interval_number">1</field>
        <field name="interval_type">days</field>
        <field name="numbercall">-1</field>
        <field name="active">True</field>
    </record>
</odoo>
''')

write('casafolino_supplier_qual/views/menus.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="action_cf_supplier_qual" model="ir.actions.act_window">
        <field name="name">Fornitori Qualificati</field>
        <field name="res_model">casafolino.supplier.qualification</field>
        <field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_supplier_documents" model="ir.actions.act_window">
        <field name="name">Documenti Fornitori</field>
        <field name="res_model">casafolino.supplier.document</field>
        <field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_supplier_evaluations" model="ir.actions.act_window">
        <field name="name">Valutazioni Fornitori</field>
        <field name="res_model">casafolino.supplier.evaluation</field>
        <field name="view_mode">list,form</field>
    </record>
    <menuitem id="menu_cf_supplier_qual_root" name="Fornitori Qualificati" sequence="32"/>
    <menuitem id="menu_cf_supplier_dashboard" name="Schede Qualifica"
              parent="menu_cf_supplier_qual_root" action="action_cf_supplier_qual" sequence="1"/>
    <menuitem id="menu_cf_supplier_docs" name="Documenti"
              parent="menu_cf_supplier_qual_root" action="action_cf_supplier_documents" sequence="2"/>
    <menuitem id="menu_cf_supplier_evals" name="Valutazioni"
              parent="menu_cf_supplier_qual_root" action="action_cf_supplier_evaluations" sequence="3"/>
</odoo>
''')

print('✅ casafolino_supplier_qual completo')

# =============================================================================
# CASAFOLINO SUPPLIER QUAL
# =============================================================================
write('casafolino_supplier_qual/__manifest__.py', '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Supplier Qualification",
    "version": "18.0.1.0.0",
    "category": "Purchase",
    "summary": "Qualifica fornitori BRC/IFS",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "purchase", "stock"],
    "data": [
        "security/cf_supplier_qual_security.xml",
        "security/ir.model.access.csv",
        "data/cf_supplier_qual_cron.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''')
write('casafolino_supplier_qual/__init__.py', 'from . import models\n')
write('casafolino_supplier_qual/models/__init__.py', 'from . import cf_supplier_qualification\nfrom . import cf_supplier_document\nfrom . import cf_supplier_evaluation\n')
write('casafolino_supplier_qual/models/cf_supplier_qualification.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

class CfSupplierQualification(models.Model):
    _name = "casafolino.supplier.qualification"
    _description = "Qualifica Fornitore"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "partner_id"
    _rec_name = "partner_id"
    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade", domain="[(\'supplier_rank\',\'>\',0)]", tracking=True)
    partner_country_id = fields.Many2one(related="partner_id.country_id", store=True, readonly=True)
    status = fields.Selection([("approved","Approvato"),("evaluation","In Valutazione"),("suspended","Sospeso"),("excluded","Escluso")], default="evaluation", required=True, tracking=True)
    traffic_light = fields.Selection([("green","Verde"),("yellow","Giallo"),("red","Rosso")], compute="_compute_traffic_light", store=True)
    date_qualification = fields.Date(default=fields.Date.today)
    qualified_by = fields.Many2one("res.users", default=lambda self: self.env.user)
    last_evaluation_date = fields.Date(readonly=True)
    next_evaluation_date = fields.Date(tracking=True)
    notes = fields.Text()
    document_ids = fields.One2many("casafolino.supplier.document", "partner_id", string="Documenti")
    evaluation_ids = fields.One2many("casafolino.supplier.evaluation", "partner_id", string="Valutazioni")
    document_count = fields.Integer(compute="_compute_stats")
    evaluation_count = fields.Integer(compute="_compute_stats")
    expired_doc_count = fields.Integer(compute="_compute_stats")
    expiring_doc_count = fields.Integer(compute="_compute_stats")
    last_score = fields.Float(compute="_compute_stats", store=True)

    @api.depends("document_ids","document_ids.doc_status","evaluation_ids","evaluation_ids.punteggio_totale")
    def _compute_stats(self):
        for rec in self:
            docs = rec.document_ids
            rec.document_count = len(docs)
            rec.evaluation_count = len(rec.evaluation_ids)
            rec.expired_doc_count = len(docs.filtered(lambda d: d.doc_status == "expired"))
            rec.expiring_doc_count = len(docs.filtered(lambda d: d.doc_status == "expiring"))
            last_eval = rec.evaluation_ids.sorted("date", reverse=True)[:1]
            rec.last_score = last_eval.punteggio_totale if last_eval else 0.0

    @api.depends("status","document_ids.doc_status","next_evaluation_date")
    def _compute_traffic_light(self):
        today = date.today()
        for rec in self:
            if rec.status in ("suspended","excluded"): rec.traffic_light = "red"; continue
            if any(d.doc_status == "expired" for d in rec.document_ids): rec.traffic_light = "red"; continue
            if any(d.doc_status == "expiring" for d in rec.document_ids): rec.traffic_light = "yellow"; continue
            if rec.next_evaluation_date and rec.next_evaluation_date < today: rec.traffic_light = "yellow"; continue
            rec.traffic_light = "green"

    def action_approve(self):
        self.write({"status": "approved"})
    def action_suspend(self):
        self.write({"status": "suspended"})
    def action_exclude(self):
        self.write({"status": "excluded"})

class ResPartnerSupplierQual(models.Model):
    _inherit = "res.partner"
    supplier_qual_id = fields.Many2one("casafolino.supplier.qualification", compute="_compute_supplier_qual", store=False)
    supplier_qual_status = fields.Selection(related="supplier_qual_id.status", readonly=True)
    supplier_traffic_light = fields.Selection(related="supplier_qual_id.traffic_light", readonly=True)

    def _compute_supplier_qual(self):
        for rec in self:
            rec.supplier_qual_id = self.env["casafolino.supplier.qualification"].search([("partner_id","=",rec.id)], limit=1)

    def action_open_qualification(self):
        self.ensure_one()
        qual = self.env["casafolino.supplier.qualification"].search([("partner_id","=",self.id)], limit=1)
        if not qual:
            qual = self.env["casafolino.supplier.qualification"].create({"partner_id": self.id})
        return {"type":"ir.actions.act_window","name":f"Qualifica {self.name}","res_model":"casafolino.supplier.qualification","res_id":qual.id,"view_mode":"form","target":"current"}
''')
write('casafolino_supplier_qual/models/cf_supplier_document.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

class CfSupplierDocument(models.Model):
    _name = "casafolino.supplier.document"
    _description = "Documento Fornitore"
    _inherit = ["mail.thread"]
    _order = "expiry_date asc"
    _rec_name = "name"
    name = fields.Char(required=True)
    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    document_type = fields.Selection([
        ("brc_ifs","BRC/IFS"),("iso_9001","ISO 9001"),("microbiological","Analisi Microbiologiche"),
        ("allergen_decl","Dichiarazione Allergeni"),("kosher","Kosher"),("halal","Halal"),
        ("bio_organic","Biologico"),("visura","Visura Camerale"),("contract","Contratto"),
        ("tech_sheet","Scheda Tecnica"),("analysis","CoA"),("other","Altro"),
    ], required=True, default="other")
    attachment_id = fields.Many2one("ir.attachment")
    has_file = fields.Boolean(compute="_compute_has_file", store=True)
    issue_date = fields.Date()
    expiry_date = fields.Date(tracking=True)
    no_expiry = fields.Boolean(default=False)
    alert_days_before = fields.Integer(default=30)
    doc_status = fields.Selection([("valid","Valido"),("expiring","In Scadenza"),("expired","Scaduto"),("no_expiry","Nessuna Scadenza"),("missing","File Mancante")], compute="_compute_doc_status", store=True, tracking=True)
    days_to_expiry = fields.Integer(compute="_compute_doc_status", store=False)
    notes = fields.Text()
    reference_number = fields.Char()

    @api.depends("attachment_id")
    def _compute_has_file(self):
        for rec in self:
            rec.has_file = bool(rec.attachment_id)

    @api.depends("expiry_date","no_expiry","alert_days_before","attachment_id")
    def _compute_doc_status(self):
        today = date.today()
        for rec in self:
            if rec.no_expiry: rec.doc_status = "no_expiry"; rec.days_to_expiry = 0; continue
            if not rec.expiry_date: rec.doc_status = "missing" if not rec.attachment_id else "valid"; rec.days_to_expiry = 0; continue
            days = (rec.expiry_date - today).days
            rec.days_to_expiry = days
            rec.doc_status = "expired" if days < 0 else "expiring" if days <= rec.alert_days_before else "valid"

    @api.model
    def send_expiry_alerts(self):
        for doc in self.search([("doc_status","in",("expiring","expired")),("no_expiry","=",False)]):
            doc.message_post(body=f"Documento {doc.name} scade il {doc.expiry_date}.")
''')
write('casafolino_supplier_qual/models/cf_supplier_evaluation.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class CfSupplierEvaluation(models.Model):
    _name = "casafolino.supplier.evaluation"
    _description = "Valutazione Fornitore"
    _inherit = ["mail.thread"]
    _order = "date desc"
    _rec_name = "display_name_computed"
    display_name_computed = fields.Char(compute="_compute_display_name", store=True)
    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade", tracking=True)
    date = fields.Date(default=fields.Date.today, required=True)
    evaluator_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    punteggio_qualita = fields.Selection([("1","1"),("2","2"),("3","3"),("4","4"),("5","5")], required=True)
    punteggio_puntualita = fields.Selection([("1","1"),("2","2"),("3","3"),("4","4"),("5","5")], required=True)
    punteggio_documentazione = fields.Selection([("1","1"),("2","2"),("3","3"),("4","4"),("5","5")], required=True)
    punteggio_totale = fields.Float(compute="_compute_punteggio", store=True, digits=(3,2))
    risultato = fields.Selection([("confirmed","Confermato"),("observation","In Osservazione"),("excluded","Escluso")], compute="_compute_risultato", store=True, required=True)
    note = fields.Text()

    @api.depends("partner_id","date")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name_computed = f"{rec.partner_id.name or ''} - {rec.date or ''}"

    @api.depends("punteggio_qualita","punteggio_puntualita","punteggio_documentazione")
    def _compute_punteggio(self):
        for rec in self:
            scores = [int(v) for v in [rec.punteggio_qualita,rec.punteggio_puntualita,rec.punteggio_documentazione] if v]
            rec.punteggio_totale = sum(scores)/len(scores) if scores else 0.0

    @api.depends("punteggio_totale")
    def _compute_risultato(self):
        for rec in self:
            rec.risultato = "confirmed" if rec.punteggio_totale >= 3.5 else "observation" if rec.punteggio_totale >= 2.0 else "excluded"

    def action_apply_result(self):
        for rec in self:
            qual = self.env["casafolino.supplier.qualification"].search([("partner_id","=",rec.partner_id.id)],limit=1)
            if not qual:
                qual = self.env["casafolino.supplier.qualification"].create({"partner_id":rec.partner_id.id})
            qual.last_evaluation_date = rec.date
            qual.next_evaluation_date = rec.date + relativedelta(years=1)
            qual.status = "approved" if rec.risultato=="confirmed" else "evaluation" if rec.risultato=="observation" else "excluded"
''')
write('casafolino_supplier_qual/security/cf_supplier_qual_security.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="module_category_cf_supplier_qual" model="ir.module.category">
        <field name="name">CasaFolino Fornitori Qualificati</field><field name="sequence">105</field>
    </record>
    <record id="group_cf_supplier_raq" model="res.groups">
        <field name="name">RAQ Qualifica Fornitori</field>
        <field name="category_id" ref="module_category_cf_supplier_qual"/>
        <field name="implied_ids" eval="[(4, ref(\'base.group_user\'))]"/>
    </record>
</odoo>
''')
write('casafolino_supplier_qual/security/ir.model.access.csv', '''\
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_cf_supplier_qual_user,casafolino.supplier.qualification user,model_casafolino_supplier_qualification,base.group_user,1,1,1,0
access_cf_supplier_qual_mgr,casafolino.supplier.qualification mgr,model_casafolino_supplier_qualification,base.group_system,1,1,1,1
access_cf_supplier_doc_user,casafolino.supplier.document user,model_casafolino_supplier_document,base.group_user,1,1,1,0
access_cf_supplier_doc_mgr,casafolino.supplier.document mgr,model_casafolino_supplier_document,base.group_system,1,1,1,1
access_cf_supplier_eval_user,casafolino.supplier.evaluation user,model_casafolino_supplier_evaluation,base.group_user,1,1,1,0
access_cf_supplier_eval_mgr,casafolino.supplier.evaluation mgr,model_casafolino_supplier_evaluation,base.group_system,1,1,1,1
''')
write('casafolino_supplier_qual/data/cf_supplier_qual_cron.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="cron_cf_supplier_doc_expiry" model="ir.cron">
        <field name="name">Supplier Qual - Alert Scadenze</field>
        <field name="model_id" search="[(\'model\',\'=\',\'casafolino.supplier.document\')]" model="ir.model"/>
        <field name="state">code</field>
        <field name="code">model.send_expiry_alerts()</field>
        <field name="interval_number">1</field><field name="interval_type">days</field>
        <field name="numbercall">-1</field><field name="active">True</field>
    </record>
</odoo>
''')
write('casafolino_supplier_qual/views/menus.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="action_cf_supplier_qual" model="ir.actions.act_window">
        <field name="name">Fornitori Qualificati</field><field name="res_model">casafolino.supplier.qualification</field><field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_supplier_documents" model="ir.actions.act_window">
        <field name="name">Documenti Fornitori</field><field name="res_model">casafolino.supplier.document</field><field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_supplier_evaluations" model="ir.actions.act_window">
        <field name="name">Valutazioni Fornitori</field><field name="res_model">casafolino.supplier.evaluation</field><field name="view_mode">list,form</field>
    </record>
    <menuitem id="menu_cf_supplier_qual_root" name="Fornitori Qualificati" sequence="32"/>
    <menuitem id="menu_cf_supplier_schede" name="Schede Qualifica" parent="menu_cf_supplier_qual_root" action="action_cf_supplier_qual" sequence="1"/>
    <menuitem id="menu_cf_supplier_docs" name="Documenti" parent="menu_cf_supplier_qual_root" action="action_cf_supplier_documents" sequence="2"/>
    <menuitem id="menu_cf_supplier_evals" name="Valutazioni" parent="menu_cf_supplier_qual_root" action="action_cf_supplier_evaluations" sequence="3"/>
</odoo>
''')
print('✅ casafolino_supplier_qual completo')

# =============================================================================
# CASAFOLINO TREASURY
# =============================================================================
write('casafolino_treasury/__manifest__.py', '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Treasury",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "Tesoreria e Cash Flow",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "account", "sale_management", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "data/cf_treasury_cron.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''')
write('casafolino_treasury/__init__.py', 'from . import models\n')
write('casafolino_treasury/models/__init__.py', 'from . import cf_treasury\n')
write('casafolino_treasury/models/cf_treasury.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta

class CfTreasury(models.Model):
    _name = "cf.treasury.snapshot"
    _description = "Snapshot Tesoreria"
    _order = "date desc"
    _rec_name = "date"

    date = fields.Date(string="Data", required=True, default=fields.Date.today)
    total_balance = fields.Monetary(string="Saldo Totale", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.EUR"))
    receivable_30d = fields.Monetary(string="Crediti 30gg", currency_field="currency_id")
    payable_30d = fields.Monetary(string="Debiti 30gg", currency_field="currency_id")
    forecast_30d = fields.Monetary(string="Forecast 30gg", currency_field="currency_id", compute="_compute_forecast", store=True)
    forecast_60d = fields.Monetary(string="Forecast 60gg", currency_field="currency_id", compute="_compute_forecast", store=True)
    forecast_90d = fields.Monetary(string="Forecast 90gg", currency_field="currency_id", compute="_compute_forecast", store=True)
    notes = fields.Text(string="Note")

    @api.depends("total_balance","receivable_30d","payable_30d")
    def _compute_forecast(self):
        for rec in self:
            base = rec.total_balance + rec.receivable_30d - rec.payable_30d
            rec.forecast_30d = base
            rec.forecast_60d = base * 1.05
            rec.forecast_90d = base * 1.10

    @api.model
    def create_daily_snapshot(self):
        today = date.today()
        existing = self.search([("date","=",today)])
        if existing: return
        journals = self.env["account.journal"].search([("type","in",("bank","cash"))])
        total = sum(j.default_account_id.current_balance for j in journals if j.default_account_id)
        domain_recv = [("account_id.account_type","=","asset_receivable"),
                       ("reconciled","=",False),("date_maturity","<=",str(today+timedelta(days=30)))]
        domain_pay  = [("account_id.account_type","=","liability_payable"),
                       ("reconciled","=",False),("date_maturity","<=",str(today+timedelta(days=30)))]
        recv = sum(self.env["account.move.line"].search(domain_recv).mapped("amount_residual"))
        pay  = abs(sum(self.env["account.move.line"].search(domain_pay).mapped("amount_residual")))
        self.create({"date":today,"total_balance":total,"receivable_30d":recv,"payable_30d":pay})
''')
write('casafolino_treasury/security/ir.model.access.csv', '''\
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_cf_treasury_user,cf.treasury.snapshot user,model_cf_treasury_snapshot,base.group_user,1,0,0,0
access_cf_treasury_mgr,cf.treasury.snapshot manager,model_cf_treasury_snapshot,base.group_system,1,1,1,1
''')
write('casafolino_treasury/data/cf_treasury_cron.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="cron_cf_treasury_snapshot" model="ir.cron">
        <field name="name">Treasury - Snapshot Giornaliero</field>
        <field name="model_id" search="[(\'model\',\'=\',\'cf.treasury.snapshot\')]" model="ir.model"/>
        <field name="state">code</field>
        <field name="code">model.create_daily_snapshot()</field>
        <field name="interval_number">1</field><field name="interval_type">days</field>
        <field name="numbercall">-1</field><field name="active">True</field>
    </record>
</odoo>
''')
write('casafolino_treasury/views/menus.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="action_cf_treasury" model="ir.actions.act_window">
        <field name="name">Tesoreria</field><field name="res_model">cf.treasury.snapshot</field><field name="view_mode">list,form</field>
    </record>
    <menuitem id="menu_cf_treasury_root" name="Tesoreria" sequence="30"/>
    <menuitem id="menu_cf_treasury_snapshots" name="Snapshots" parent="menu_cf_treasury_root" action="action_cf_treasury" sequence="1"/>
</odoo>
''')
print('✅ casafolino_treasury completo')

# =============================================================================
# CASAFOLINO RECALL
# =============================================================================
write('casafolino_recall/__manifest__.py', '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Mock Recall",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Mock Recall BRC/IFS - Tracciabilita lotti",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "mrp", "stock", "purchase", "sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
        "wizard/cf_recall_wizard_views.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''')
write('casafolino_recall/__init__.py', 'from . import models\nfrom . import wizard\n')
write('casafolino_recall/models/__init__.py', 'from . import cf_recall_session\n')
write('casafolino_recall/wizard/__init__.py', 'from . import cf_recall_wizard\n')
write('casafolino_recall/models/cf_recall_session.py', '''\
# -*- coding: utf-8 -*-
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
    notes = fields.Text()

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
''')
write('casafolino_recall/wizard/__init__.py', 'from . import cf_recall_wizard\n')
write('casafolino_recall/wizard/cf_recall_wizard.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields

class CfRecallWizard(models.TransientModel):
    _name = "cf.recall.wizard"
    _description = "Wizard Avvio Mock Recall"
    lot_id = fields.Many2one("stock.lot", required=True)
    direction = fields.Selection([("forward","Avanti"),("backward","Indietro"),("both","Entrambe")], required=True, default="both")
    session_type = fields.Selection([("mock","Mock"),("real","Reale"),("audit","Audit")], required=True, default="mock")
    notes = fields.Text()

    def action_run_recall(self):
        session = self.env["cf.recall.session"].create({
            "lot_id": self.lot_id.id,
            "direction": self.direction,
            "session_type": self.session_type,
            "notes": self.notes,
        })
        session.action_run()
        return {"type":"ir.actions.act_window","name":"Risultato Recall","res_model":"cf.recall.session","res_id":session.id,"view_mode":"form","target":"current"}
''')
write('casafolino_recall/wizard/cf_recall_wizard_views.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_cf_recall_wizard_form" model="ir.ui.view">
        <field name="name">cf.recall.wizard.form</field>
        <field name="model">cf.recall.wizard</field>
        <field name="arch" type="xml">
            <form string="Avvia Mock Recall">
                <sheet>
                    <group>
                        <field name="lot_id"/>
                        <field name="direction"/>
                        <field name="session_type"/>
                        <field name="notes"/>
                    </group>
                </sheet>
                <footer>
                    <button name="action_run_recall" type="object" string="Avvia Recall" class="btn-primary"/>
                    <button special="cancel" string="Annulla" class="btn-secondary"/>
                </footer>
            </form>
        </field>
    </record>
    <record id="action_cf_recall_wizard" model="ir.actions.act_window">
        <field name="name">Avvia Mock Recall</field>
        <field name="res_model">cf.recall.wizard</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>
    </record>
</odoo>
''')
write('casafolino_recall/security/ir.model.access.csv', '''\
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_cf_recall_session_user,cf.recall.session user,model_cf_recall_session,base.group_user,1,1,1,0
access_cf_recall_session_mgr,cf.recall.session manager,model_cf_recall_session,base.group_system,1,1,1,1
access_cf_recall_wizard_user,cf.recall.wizard user,model_cf_recall_wizard,base.group_user,1,1,1,1
''')
write('casafolino_recall/views/menus.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="seq_cf_recall_session" model="ir.sequence">
        <field name="name">Mock Recall</field>
        <field name="code">cf.recall.session</field>
        <field name="prefix">RECALL-%(year)s-</field>
        <field name="padding">4</field>
    </record>
    <record id="action_cf_recall_sessions" model="ir.actions.act_window">
        <field name="name">Sessioni Recall</field><field name="res_model">cf.recall.session</field><field name="view_mode">list,form</field>
    </record>
    <menuitem id="menu_cf_recall_root" name="Mock Recall" sequence="29"/>
    <menuitem id="menu_cf_recall_new" name="Avvia Recall" parent="menu_cf_recall_root" action="action_cf_recall_wizard" sequence="1"/>
    <menuitem id="menu_cf_recall_sessions" name="Sessioni" parent="menu_cf_recall_root" action="action_cf_recall_sessions" sequence="2"/>
</odoo>
''')
print('✅ casafolino_recall completo')

# =============================================================================
# CASAFOLINO KPI
# =============================================================================
write('casafolino_kpi/__manifest__.py', '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino KPI Dashboard",
    "version": "18.0.1.0.0",
    "category": "Reporting",
    "summary": "Dashboard KPI unificata",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "sale_management", "purchase", "account", "mrp", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "data/cf_kpi_cron.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''')
write('casafolino_kpi/__init__.py', 'from . import models\n')
write('casafolino_kpi/models/__init__.py', 'from . import cf_kpi_dashboard\n')
write('casafolino_kpi/models/cf_kpi_dashboard.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta

class CfKpiSnapshot(models.Model):
    _name = "cf.kpi.snapshot"
    _description = "Snapshot KPI Giornaliero"
    _order = "date desc"
    _rec_name = "date"

    date = fields.Date(required=True, default=fields.Date.today)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.EUR"))
    sales_today = fields.Monetary(string="Vendite Oggi", currency_field="currency_id")
    sales_mtd = fields.Monetary(string="Vendite MTD", currency_field="currency_id")
    sales_ytd = fields.Monetary(string="Vendite YTD", currency_field="currency_id")
    sales_amazon = fields.Monetary(string="Amazon", currency_field="currency_id")
    sales_shopify = fields.Monetary(string="Shopify", currency_field="currency_id")
    sales_b2b = fields.Monetary(string="B2B", currency_field="currency_id")
    sales_gdo = fields.Monetary(string="GDO", currency_field="currency_id")
    mo_open = fields.Integer(string="MO Aperti")
    mo_done = fields.Integer(string="MO Completati MTD")
    nc_open = fields.Integer(string="NC Aperte")
    quarantine_active = fields.Integer(string="Quarantene Attive")
    notes = fields.Text()

    @api.model
    def create_daily_snapshot(self):
        today = date.today()
        if self.search([("date","=",today)]): return
        first_day_month = today.replace(day=1)
        first_day_year = today.replace(month=1,day=1)

        def get_sales(domain_extra=[]):
            domain = [("state","in",("sale","done")),("date_order",">=",str(first_day_year))] + domain_extra
            orders = self.env["sale.order"].search(domain)
            return sum(orders.mapped("amount_untaxed"))

        def get_sales_by_tag(tag_name):
            tag = self.env["res.partner.category"].search([("name","ilike",tag_name)],limit=1)
            if not tag: return 0.0
            domain = [("state","in",("sale","done")),("date_order",">=",str(first_day_year)),
                      ("partner_id.category_id","in",[tag.id])]
            return sum(self.env["sale.order"].search(domain).mapped("amount_untaxed"))

        mo_open = self.env["mrp.production"].search_count([("state","in",("confirmed","progress"))])
        mo_done = self.env["mrp.production"].search_count([("state","=","done"),("date_finished",">=",str(first_day_month))])

        nc_open = 0
        quarantine = 0
        if "cf.haccp.nc" in self.env:
            nc_open = self.env["cf.haccp.nc"].search_count([("state","not in",("closed","cancelled"))])
        if "cf.haccp.quarantine" in self.env:
            quarantine = self.env["cf.haccp.quarantine"].search_count([("state","=","active")])

        self.create({
            "date": today,
            "sales_ytd": get_sales(),
            "sales_mtd": get_sales([("date_order",">=",str(first_day_month))]),
            "sales_amazon": get_sales_by_tag("Amazon"),
            "sales_shopify": get_sales_by_tag("Shopify"),
            "sales_b2b": get_sales_by_tag("B2B"),
            "sales_gdo": get_sales_by_tag("GDO"),
            "mo_open": mo_open,
            "mo_done": mo_done,
            "nc_open": nc_open,
            "quarantine_active": quarantine,
        })
''')
write('casafolino_kpi/security/ir.model.access.csv', '''\
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_cf_kpi_user,cf.kpi.snapshot user,model_cf_kpi_snapshot,base.group_user,1,0,0,0
access_cf_kpi_mgr,cf.kpi.snapshot manager,model_cf_kpi_snapshot,base.group_system,1,1,1,1
''')
write('casafolino_kpi/data/cf_kpi_cron.xml', '<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n</odoo>\n')
write('casafolino_kpi/views/menus.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="action_cf_kpi" model="ir.actions.act_window">
        <field name="name">KPI Dashboard</field><field name="res_model">cf.kpi.snapshot</field><field name="view_mode">list,form</field>
    </record>
    <menuitem id="menu_cf_kpi_root" name="KPI" sequence="10"/>
    <menuitem id="menu_cf_kpi_snapshots" name="Snapshots" parent="menu_cf_kpi_root" action="action_cf_kpi" sequence="1"/>
</odoo>
''')
print('✅ casafolino_kpi completo')

# =============================================================================
# CASAFOLINO GDO
# =============================================================================
write('casafolino_gdo/__manifest__.py', '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino GDO",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "summary": "Pipeline GDO — Listing, Contratti, Forecast",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "sale_management", "product", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''')
write('casafolino_gdo/__init__.py', 'from . import models\n')
write('casafolino_gdo/models/__init__.py', 'from . import cf_gdo\n')
write('casafolino_gdo/models/cf_gdo.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CfGdoRetailer(models.Model):
    _name = "cf.gdo.retailer"
    _description = "Retailer GDO"
    _inherit = ["mail.thread"]
    _rec_name = "partner_id"
    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    retailer_type = fields.Selection([
        ("supermarket","Supermercato"),("hypermarket","Ipermercato"),
        ("discount","Discount"),("specialty","Specialty"),("online","Online"),
    ], required=True, default="supermarket")
    country_id = fields.Many2one(related="partner_id.country_id", store=True)
    num_stores = fields.Integer(string="N° Punti Vendita")
    buyer_id = fields.Many2one("res.partner", string="Buyer")
    annual_target = fields.Monetary(string="Target Annuale", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.EUR"))
    listing_ids = fields.One2many("cf.gdo.listing", "retailer_id", string="Listing")
    active = fields.Boolean(default=True)
    notes = fields.Text()

class CfGdoListing(models.Model):
    _name = "cf.gdo.listing"
    _description = "Listing Prodotto GDO"
    _inherit = ["mail.thread"]
    _rec_name = "display_name_computed"
    display_name_computed = fields.Char(compute="_compute_display_name", store=True)
    retailer_id = fields.Many2one("cf.gdo.retailer", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.template", required=True)
    state = fields.Selection([
        ("draft","Bozza"),("sample","Campione"),("evaluation","Valutazione"),
        ("approved","Approvato"),("active","Attivo"),("delisted","Delistato"),
    ], default="draft", tracking=True, required=True)
    date_submission = fields.Date(string="Data Sottomissione")
    date_approval = fields.Date(string="Data Approvazione")
    date_active = fields.Date(string="Data Attivazione")
    selling_price = fields.Monetary(string="Prezzo Vendita", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.EUR"))
    num_stores = fields.Integer(string="N° Store")
    notes = fields.Text()

    @api.depends("retailer_id","product_id")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name_computed = f"{rec.retailer_id.partner_id.name or ''} - {rec.product_id.name or ''}"

class ResPartnerGdo(models.Model):
    _inherit = "res.partner"
    is_gdo_retailer = fields.Boolean(string="Retailer GDO", default=False)
''')
write('casafolino_gdo/security/ir.model.access.csv', '''\
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_cf_gdo_retailer_user,cf.gdo.retailer user,model_cf_gdo_retailer,base.group_user,1,1,1,0
access_cf_gdo_retailer_mgr,cf.gdo.retailer manager,model_cf_gdo_retailer,base.group_system,1,1,1,1
access_cf_gdo_listing_user,cf.gdo.listing user,model_cf_gdo_listing,base.group_user,1,1,1,0
access_cf_gdo_listing_mgr,cf.gdo.listing manager,model_cf_gdo_listing,base.group_system,1,1,1,1
''')
write('casafolino_gdo/views/menus.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="action_cf_gdo_retailers" model="ir.actions.act_window">
        <field name="name">Retailer GDO</field><field name="res_model">cf.gdo.retailer</field><field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_gdo_listings" model="ir.actions.act_window">
        <field name="name">Listing Prodotti</field><field name="res_model">cf.gdo.listing</field><field name="view_mode">list,form</field>
    </record>
    <menuitem id="menu_cf_gdo_root" name="GDO" sequence="35"/>
    <menuitem id="menu_cf_gdo_retailers" name="Retailer" parent="menu_cf_gdo_root" action="action_cf_gdo_retailers" sequence="1"/>
    <menuitem id="menu_cf_gdo_listings" name="Listing" parent="menu_cf_gdo_root" action="action_cf_gdo_listings" sequence="2"/>
</odoo>
''')
print('✅ casafolino_gdo completo')

# =============================================================================
# CASAFOLINO PRIVATE LABEL
# =============================================================================
write('casafolino_private_label/__manifest__.py', '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Private Label",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "summary": "Gestione clienti Private Label",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "sale_management", "product", "account", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''')
write('casafolino_private_label/__init__.py', 'from . import models\n')
write('casafolino_private_label/models/__init__.py', 'from . import cf_private_label\n')
write('casafolino_private_label/models/cf_private_label.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CfPlClient(models.Model):
    _name = "cf.pl.client"
    _description = "Cliente Private Label"
    _inherit = ["mail.thread"]
    _rec_name = "partner_id"
    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    country_id = fields.Many2one(related="partner_id.country_id", store=True)
    annual_target = fields.Monetary(string="Target Annuale", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.EUR"))
    product_ids = fields.One2many("cf.pl.product", "client_id", string="Prodotti PL")
    active = fields.Boolean(default=True)
    notes = fields.Text()

class CfPlProduct(models.Model):
    _name = "cf.pl.product"
    _description = "Prodotto Private Label"
    _inherit = ["mail.thread"]
    _rec_name = "name"
    name = fields.Char(string="Nome Prodotto PL", required=True)
    client_id = fields.Many2one("cf.pl.client", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.template", string="Prodotto Base")
    state = fields.Selection([
        ("request","Richiesta"),("development","Sviluppo"),("sampling","Campionatura"),
        ("approved","Approvato"),("active","Attivo"),
    ], default="request", tracking=True, required=True)
    selling_price = fields.Monetary(string="Prezzo PL", currency_field="currency_id")
    production_cost = fields.Monetary(string="Costo Produzione", currency_field="currency_id")
    label_cost = fields.Monetary(string="Costo Etichetta", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.EUR"))
    margin_pct = fields.Float(string="Margine %", compute="_compute_margin", store=True)
    min_order_qty = fields.Float(string="MOQ")
    notes = fields.Text()

    @api.depends("selling_price","production_cost","label_cost")
    def _compute_margin(self):
        for rec in self:
            cost = rec.production_cost + rec.label_cost
            rec.margin_pct = ((rec.selling_price - cost) / rec.selling_price * 100) if rec.selling_price else 0.0

class ResPartnerPl(models.Model):
    _inherit = "res.partner"
    is_pl_client = fields.Boolean(string="Cliente Private Label", default=False)
''')
write('casafolino_private_label/security/ir.model.access.csv', '''\
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_cf_pl_client_user,cf.pl.client user,model_cf_pl_client,base.group_user,1,1,1,0
access_cf_pl_client_mgr,cf.pl.client manager,model_cf_pl_client,base.group_system,1,1,1,1
access_cf_pl_product_user,cf.pl.product user,model_cf_pl_product,base.group_user,1,1,1,0
access_cf_pl_product_mgr,cf.pl.product manager,model_cf_pl_product,base.group_system,1,1,1,1
''')
write('casafolino_private_label/views/menus.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="action_cf_pl_clients" model="ir.actions.act_window">
        <field name="name">Clienti PL</field><field name="res_model">cf.pl.client</field><field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_pl_products" model="ir.actions.act_window">
        <field name="name">Prodotti PL</field><field name="res_model">cf.pl.product</field><field name="view_mode">list,form</field>
    </record>
    <menuitem id="menu_cf_pl_root" name="Private Label" sequence="40"/>
    <menuitem id="menu_cf_pl_clients" name="Clienti" parent="menu_cf_pl_root" action="action_cf_pl_clients" sequence="1"/>
    <menuitem id="menu_cf_pl_products" name="Prodotti" parent="menu_cf_pl_root" action="action_cf_pl_products" sequence="2"/>
</odoo>
''')
print('✅ casafolino_private_label completo')

# =============================================================================
# CASAFOLINO PRODUCTION
# =============================================================================
write('casafolino_production/__manifest__.py', '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Production Calendar",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Commesse produzione con calendario",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "project", "mrp", "sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''')
write('casafolino_production/__init__.py', 'from . import models\n')
write('casafolino_production/models/__init__.py', 'from . import cf_production_job\n')
write('casafolino_production/models/cf_production_job.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

PRODUCTION_LINES = [
    ("miele","Miele"),("creme","Creme Spalmabili"),("cantucci","Cantucci GF"),
    ("cioccolato","Cioccolato"),("crispy","Crispy Chili"),
    ("risotti","Risotti"),("confezionamento","Confezionamento"),
]

LINE_COLORS = {
    "miele":"#F59E0B","creme":"#8B5CF6","cantucci":"#10B981",
    "cioccolato":"#92400E","crispy":"#EF4444","risotti":"#3B82F6","confezionamento":"#6B7280",
}

class CfProductionJob(models.Model):
    _name = "cf.production.job"
    _description = "Commessa Produzione"
    _inherit = ["mail.thread","mail.activity.mixin"]
    _order = "date_start asc"
    _rec_name = "reference"

    reference = fields.Char(required=True, copy=False, readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("cf.production.job") or "PROD-NUOVO")
    state = fields.Selection([
        ("draft","Bozza"),("confirmed","Confermata"),("in_progress","In Produzione"),
        ("done","Completata"),("cancelled","Annullata"),
    ], default="draft", tracking=True)
    production_line = fields.Selection(PRODUCTION_LINES, required=True, tracking=True)
    line_color = fields.Char(compute="_compute_line_color", store=False)
    product_id = fields.Many2one("product.template", required=True)
    quantity_planned = fields.Float(string="Quantita Pianificata", required=True)
    quantity_done = fields.Float(string="Quantita Prodotta")
    date_start = fields.Datetime(string="Inizio", required=True)
    date_end = fields.Datetime(string="Fine", required=True)
    operator_ids = fields.Many2many("res.users", string="Operatori")
    production_id = fields.Many2one("mrp.production", string="Ordine Produzione")
    notes = fields.Text()

    @api.depends("production_line")
    def _compute_line_color(self):
        for rec in self:
            rec.line_color = LINE_COLORS.get(rec.production_line, "#6B7280")

    @api.constrains("date_start","date_end")
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start >= rec.date_end:
                raise ValidationError("La data di fine deve essere successiva alla data di inizio.")

    def action_confirm(self):
        self.write({"state":"confirmed"})
    def action_start(self):
        self.write({"state":"in_progress"})
    def action_done(self):
        self.write({"state":"done"})
    def action_cancel(self):
        self.write({"state":"cancelled"})

    def action_create_mo(self):
        self.ensure_one()
        mo = self.env["mrp.production"].create({
            "product_id": self.product_id.product_variant_id.id if self.product_id.product_variant_id else False,
            "product_qty": self.quantity_planned,
            "date_start": self.date_start,
        })
        self.production_id = mo
        return {"type":"ir.actions.act_window","name":"Ordine Produzione","res_model":"mrp.production","res_id":mo.id,"view_mode":"form"}
''')
write('casafolino_production/security/ir.model.access.csv', '''\
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_cf_prod_job_user,cf.production.job user,model_cf_production_job,base.group_user,1,1,1,0
access_cf_prod_job_mgr,cf.production.job manager,model_cf_production_job,base.group_system,1,1,1,1
''')
write('casafolino_production/views/menus.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="seq_cf_production_job" model="ir.sequence">
        <field name="name">Commessa Produzione</field>
        <field name="code">cf.production.job</field>
        <field name="prefix">PROD-%(year)s-</field>
        <field name="padding">4</field>
    </record>
    <record id="action_cf_production_jobs" model="ir.actions.act_window">
        <field name="name">Commesse Produzione</field><field name="res_model">cf.production.job</field>
        <field name="view_mode">list,calendar,form</field>
    </record>
    <menuitem id="menu_cf_prod_root" name="Produzione CF" sequence="22"/>
    <menuitem id="menu_cf_prod_jobs" name="Commesse" parent="menu_cf_prod_root" action="action_cf_production_jobs" sequence="1"/>
</odoo>
''')
print('✅ casafolino_production completo')

# =============================================================================
# CASAFOLINO ALLERGEN
# =============================================================================
write('casafolino_allergen/__manifest__.py', '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Allergeni",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Gestione 14 allergeni UE — Reg. 1169/2011",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "mrp", "product"],
    "data": [
        "security/ir.model.access.csv",
        "data/cf_allergen_14eu.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''')
write('casafolino_allergen/__init__.py', 'from . import models\n')
write('casafolino_allergen/models/__init__.py', 'from . import cf_allergen\n')
write('casafolino_allergen/models/cf_allergen.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CfAllergen(models.Model):
    _name = "cf.allergen"
    _description = "Allergene UE"
    _order = "sequence"
    _rec_name = "name"
    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    regulation_ref = fields.Char(string="Rif. Regolamento", default="Reg. 1169/2011")
    active = fields.Boolean(default=True)

class CfAllergenKeyword(models.Model):
    _name = "cf.allergen.keyword"
    _description = "Keyword Allergene"
    allergen_id = fields.Many2one("cf.allergen", required=True, ondelete="cascade")
    keyword = fields.Char(required=True)
    match_type = fields.Selection([("exact","Esatta"),("partial","Parziale"),("starts","Inizia con")], default="partial")

class CfRecipeAllergen(models.Model):
    _name = "cf.recipe.allergen"
    _description = "Allergene Ricetta"
    bom_id = fields.Many2one("mrp.bom", required=True, ondelete="cascade")
    allergen_id = fields.Many2one("cf.allergen", required=True)
    status = fields.Selection([
        ("present","Presente"),("traces","Puo Contenere Tracce"),("absent","Assente"),
    ], required=True, default="absent")
    cross_contamination = fields.Boolean(default=False)
    notes = fields.Text()
    validated_by = fields.Many2one("res.users", string="Validato da")
    validation_date = fields.Date(string="Data Validazione")

class MrpBomAllergen(models.Model):
    _inherit = "mrp.bom"
    allergen_ids = fields.One2many("cf.recipe.allergen", "bom_id", string="Allergeni")
    allergen_validated = fields.Boolean(string="Dichiarazione Validata", default=False)

    def action_analyze_allergens(self):
        self.ensure_one()
        allergens = self.env["cf.allergen"].search([])
        keywords = self.env["cf.allergen.keyword"].search([])
        ingredient_names = " ".join(self.bom_line_ids.mapped("product_id.name")).lower()
        for allergen in allergens:
            existing = self.allergen_ids.filtered(lambda a: a.allergen_id.id == allergen.id)
            if existing: continue
            kws = keywords.filtered(lambda k: k.allergen_id.id == allergen.id)
            found = False
            for kw in kws:
                k = kw.keyword.lower()
                if kw.match_type == "exact" and k == ingredient_names: found = True
                elif kw.match_type == "partial" and k in ingredient_names: found = True
                elif kw.match_type == "starts" and ingredient_names.startswith(k): found = True
            self.env["cf.recipe.allergen"].create({
                "bom_id": self.id,
                "allergen_id": allergen.id,
                "status": "present" if found else "absent",
            })
''')
write('casafolino_allergen/data/cf_allergen_14eu.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="allergen_01_gluten" model="cf.allergen"><field name="sequence">1</field><field name="code">01</field><field name="name">Cereali contenenti glutine</field></record>
    <record id="allergen_02_crustaceans" model="cf.allergen"><field name="sequence">2</field><field name="code">02</field><field name="name">Crostacei</field></record>
    <record id="allergen_03_eggs" model="cf.allergen"><field name="sequence">3</field><field name="code">03</field><field name="name">Uova</field></record>
    <record id="allergen_04_fish" model="cf.allergen"><field name="sequence">4</field><field name="code">04</field><field name="name">Pesce</field></record>
    <record id="allergen_05_peanuts" model="cf.allergen"><field name="sequence">5</field><field name="code">05</field><field name="name">Arachidi</field></record>
    <record id="allergen_06_soy" model="cf.allergen"><field name="sequence">6</field><field name="code">06</field><field name="name">Soia</field></record>
    <record id="allergen_07_milk" model="cf.allergen"><field name="sequence">7</field><field name="code">07</field><field name="name">Latte</field></record>
    <record id="allergen_08_nuts" model="cf.allergen"><field name="sequence">8</field><field name="code">08</field><field name="name">Frutta a guscio</field></record>
    <record id="allergen_09_celery" model="cf.allergen"><field name="sequence">9</field><field name="code">09</field><field name="name">Sedano</field></record>
    <record id="allergen_10_mustard" model="cf.allergen"><field name="sequence">10</field><field name="code">10</field><field name="name">Senape</field></record>
    <record id="allergen_11_sesame" model="cf.allergen"><field name="sequence">11</field><field name="code">11</field><field name="name">Semi di sesamo</field></record>
    <record id="allergen_12_so2" model="cf.allergen"><field name="sequence">12</field><field name="code">12</field><field name="name">Anidride solforosa e solfiti</field></record>
    <record id="allergen_13_lupin" model="cf.allergen"><field name="sequence">13</field><field name="code">13</field><field name="name">Lupini</field></record>
    <record id="allergen_14_molluscs" model="cf.allergen"><field name="sequence">14</field><field name="code">14</field><field name="name">Molluschi</field></record>
</odoo>
''')
write('casafolino_allergen/security/ir.model.access.csv', '''\
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_cf_allergen_user,cf.allergen user,model_cf_allergen,base.group_user,1,0,0,0
access_cf_allergen_mgr,cf.allergen manager,model_cf_allergen,base.group_system,1,1,1,1
access_cf_allergen_kw_user,cf.allergen.keyword user,model_cf_allergen_keyword,base.group_user,1,0,0,0
access_cf_allergen_kw_mgr,cf.allergen.keyword manager,model_cf_allergen_keyword,base.group_system,1,1,1,1
access_cf_recipe_allergen_user,cf.recipe.allergen user,model_cf_recipe_allergen,base.group_user,1,1,1,0
access_cf_recipe_allergen_mgr,cf.recipe.allergen manager,model_cf_recipe_allergen,base.group_system,1,1,1,1
''')
write('casafolino_allergen/views/menus.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="action_cf_allergens" model="ir.actions.act_window">
        <field name="name">Allergeni UE</field><field name="res_model">cf.allergen</field><field name="view_mode">list,form</field>
    </record>
    <menuitem id="menu_cf_allergen_root" name="Allergeni" sequence="27"/>
    <menuitem id="menu_cf_allergens" name="14 Allergeni UE" parent="menu_cf_allergen_root" action="action_cf_allergens" sequence="1"/>
</odoo>
''')
print('✅ casafolino_allergen completo')

# =============================================================================
# CASAFOLINO NUTRITION
# =============================================================================
write('casafolino_nutrition/__manifest__.py', '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Nutrition",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Valori nutrizionali da BoM",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "mrp", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''')
write('casafolino_nutrition/__init__.py', 'from . import models\n')
write('casafolino_nutrition/models/__init__.py', 'from . import cf_nutrition\n')
write('casafolino_nutrition/models/cf_nutrition.py', '''\
# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CfNutritionIngredient(models.Model):
    _name = "cf.nutrition.ingredient"
    _description = "Valori Nutrizionali Ingrediente"
    _rec_name = "product_id"
    product_id = fields.Many2one("product.template", required=True, ondelete="cascade")
    energy_kcal = fields.Float(string="Energia (kcal/100g)")
    energy_kj = fields.Float(string="Energia (kJ/100g)")
    fat = fields.Float(string="Grassi (g/100g)")
    saturated_fat = fields.Float(string="Acidi Grassi Saturi (g/100g)")
    carbs = fields.Float(string="Carboidrati (g/100g)")
    sugars = fields.Float(string="Zuccheri (g/100g)")
    fiber = fields.Float(string="Fibra (g/100g)")
    protein = fields.Float(string="Proteine (g/100g)")
    salt = fields.Float(string="Sale (g/100g)")
    sodium = fields.Float(string="Sodio (g/100g)")
    fdc_id = fields.Char(string="USDA FDC ID")
    notes = fields.Text()

class CfNutritionBom(models.Model):
    _name = "cf.nutrition.bom"
    _description = "Valori Nutrizionali Ricetta"
    _rec_name = "bom_id"
    bom_id = fields.Many2one("mrp.bom", required=True, ondelete="cascade")
    serving_size_g = fields.Float(string="Porzione (g)", default=100.0)
    energy_kcal = fields.Float(string="Energia (kcal/100g)", readonly=True)
    energy_kj = fields.Float(string="Energia (kJ/100g)", readonly=True)
    fat = fields.Float(string="Grassi (g/100g)", readonly=True)
    saturated_fat = fields.Float(string="Saturi (g/100g)", readonly=True)
    carbs = fields.Float(string="Carboidrati (g/100g)", readonly=True)
    sugars = fields.Float(string="Zuccheri (g/100g)", readonly=True)
    fiber = fields.Float(string="Fibra (g/100g)", readonly=True)
    protein = fields.Float(string="Proteine (g/100g)", readonly=True)
    salt = fields.Float(string="Sale (g/100g)", readonly=True)
    last_computed = fields.Datetime(string="Ultimo Calcolo", readonly=True)

    def action_compute(self):
        self.ensure_one()
        bom = self.bom_id
        total_qty = sum(line.product_qty for line in bom.bom_line_ids)
        if not total_qty: return
        fields_map = ["energy_kcal","energy_kj","fat","saturated_fat","carbs","sugars","fiber","protein","salt"]
        totals = {f: 0.0 for f in fields_map}
        for line in bom.bom_line_ids:
            ingredient = self.env["cf.nutrition.ingredient"].search(
                [("product_id","=",line.product_id.product_tmpl_id.id)], limit=1)
            if not ingredient: continue
            ratio = line.product_qty / total_qty
            for f in fields_map:
                totals[f] += getattr(ingredient, f) * ratio
        totals["last_computed"] = fields.Datetime.now()
        self.write(totals)

class MrpBomNutrition(models.Model):
    _inherit = "mrp.bom"
    nutrition_ids = fields.One2many("cf.nutrition.bom", "bom_id", string="Valori Nutrizionali")
''')
write('casafolino_nutrition/security/ir.model.access.csv', '''\
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_cf_nutrition_ingredient_user,cf.nutrition.ingredient user,model_cf_nutrition_ingredient,base.group_user,1,1,1,0
access_cf_nutrition_ingredient_mgr,cf.nutrition.ingredient manager,model_cf_nutrition_ingredient,base.group_system,1,1,1,1
access_cf_nutrition_bom_user,cf.nutrition.bom user,model_cf_nutrition_bom,base.group_user,1,1,1,0
access_cf_nutrition_bom_mgr,cf.nutrition.bom manager,model_cf_nutrition_bom,base.group_system,1,1,1,1
''')
write('casafolino_nutrition/views/menus.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="action_cf_nutrition_ingredients" model="ir.actions.act_window">
        <field name="name">Ingredienti Nutrizionali</field><field name="res_model">cf.nutrition.ingredient</field><field name="view_mode">list,form</field>
    </record>
    <menuitem id="menu_cf_nutrition_root" name="Nutrizione" sequence="28"/>
    <menuitem id="menu_cf_nutrition_ingredients" name="Ingredienti" parent="menu_cf_nutrition_root" action="action_cf_nutrition_ingredients" sequence="1"/>
</odoo>
''')
print('✅ casafolino_nutrition completo')
print('\n🎉 Build completo — tutti i moduli pronti!')

# =============================================================================
# VISTE FORM — CASAFOLINO HACCP
# =============================================================================
write('casafolino_haccp/views/cf_haccp_receipt_views.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_cf_haccp_receipt_form" model="ir.ui.view">
        <field name="name">cf.haccp.receipt.form</field>
        <field name="model">cf.haccp.receipt</field>
        <field name="arch" type="xml">
            <form string="Controllo Ricezione">
                <header>
                    <button name="action_accept" type="object" string="Accetta" class="btn-success" attrs="{'invisible': [('state','not in',('draft','in_progress'))]}"/>
                    <button name="action_quarantine" type="object" string="Quarantena" class="btn-warning" attrs="{'invisible': [('state','not in',('draft','in_progress'))]}"/>
                    <button name="action_reject" type="object" string="Rifiuta" class="btn-danger" attrs="{'invisible': [('state','not in',('draft','in_progress'))]}"/>
                    <field name="state" widget="statusbar" statusbar_visible="draft,in_progress,accepted"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="reference" readonly="1"/></h1>
                    </div>
                    <group>
                        <group string="Prodotto">
                            <field name="product_id"/>
                            <field name="lot_id"/>
                            <field name="partner_id"/>
                            <field name="quantity_received"/>
                        </group>
                        <group string="Controllo">
                            <field name="date"/>
                            <field name="operator_id"/>
                            <field name="temperature_measured"/>
                        </group>
                    </group>
                    <group string="Checklist">
                        <group>
                            <field name="appearance_ok"/>
                            <field name="smell_ok"/>
                            <field name="color_ok"/>
                        </group>
                        <group>
                            <field name="ddt_present"/>
                            <field name="cert_present"/>
                            <field name="packaging_intact"/>
                        </group>
                    </group>
                    <group>
                        <field name="general_notes" placeholder="Note..."/>
                    </group>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>
    <record id="view_cf_haccp_receipt_list" model="ir.ui.view">
        <field name="name">cf.haccp.receipt.list</field>
        <field name="model">cf.haccp.receipt</field>
        <field name="arch" type="xml">
            <list string="Controlli Ricezione" decoration-success="state==\'accepted\'" decoration-warning="state==\'quarantine\'" decoration-danger="state==\'rejected\'">
                <field name="reference"/>
                <field name="date"/>
                <field name="product_id"/>
                <field name="lot_id"/>
                <field name="partner_id"/>
                <field name="quantity_received"/>
                <field name="operator_id" widget="many2one_avatar_user"/>
                <field name="state" widget="badge" decoration-success="state==\'accepted\'" decoration-warning="state==\'quarantine\'" decoration-danger="state==\'rejected\'"/>
            </list>
        </field>
    </record>
</odoo>
''')

write('casafolino_haccp/views/cf_haccp_sp_views.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_cf_haccp_sp_form" model="ir.ui.view">
        <field name="name">cf.haccp.sp.form</field>
        <field name="model">cf.haccp.sp</field>
        <field name="arch" type="xml">
            <form string="Scheda Produzione">
                <header>
                    <button name="action_start" type="object" string="Avvia" class="btn-primary" attrs="{'invisible': [('state','!=','draft')]}"/>
                    <button name="action_complete" type="object" string="Completa" class="btn-success" attrs="{'invisible': [('state','!=','in_progress')]}"/>
                    <button name="action_release" type="object" string="Rilascia" class="btn-primary" attrs="{'invisible': [('state','!=','completed')]}"/>
                    <field name="state" widget="statusbar" statusbar_visible="draft,in_progress,completed,released"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="reference" readonly="1"/></h1>
                    </div>
                    <group>
                        <group string="Produzione">
                            <field name="product_id"/>
                            <field name="lot_id"/>
                            <field name="production_id"/>
                            <field name="quantity_produced"/>
                        </group>
                        <group string="Info">
                            <field name="date"/>
                            <field name="date_end"/>
                            <field name="operator_id"/>
                        </group>
                    </group>
                    <group string="10 Step HACCP">
                        <group>
                            <field name="step1_ok" string="Step 1 — Ricevimento MP"/>
                            <field name="step2_ok" string="Step 2 — Pesatura"/>
                            <field name="step3_ok" string="Step 3 — Miscelazione"/>
                            <field name="step4_ok" string="Step 4 — Lavorazione"/>
                            <field name="step5_ok" string="Step 5 — Controllo Intermedio"/>
                        </group>
                        <group>
                            <field name="step6_ok" string="Step 6 — Confezionamento"/>
                            <field name="step7_ok" string="Step 7 — Etichettatura"/>
                            <field name="step8_ok" string="Step 8 — Controllo Finale"/>
                            <field name="step9_ok" string="Step 9 — Stoccaggio"/>
                            <field name="step10_ok" string="Step 10 — Spedizione"/>
                        </group>
                    </group>
                    <notebook>
                        <page string="CCP">
                            <field name="ccp_ids">
                                <list editable="bottom" decoration-danger="state==\'ko\'" decoration-success="state==\'ok\'">
                                    <field name="sequence" widget="handle"/>
                                    <field name="name"/>
                                    <field name="ccp_type"/>
                                    <field name="critical_limit_min"/>
                                    <field name="critical_limit_max"/>
                                    <field name="unit"/>
                                    <field name="measured_value"/>
                                    <field name="measurement_time"/>
                                    <field name="state" widget="badge" decoration-success="state==\'ok\'" decoration-danger="state==\'ko\'"/>
                                </list>
                            </field>
                        </page>
                        <page string="Non Conformita">
                            <field name="nc_ids">
                                <list decoration-danger="severity==\'critical\'" decoration-warning="severity==\'high\'">
                                    <field name="reference"/>
                                    <field name="date"/>
                                    <field name="severity" widget="badge"/>
                                    <field name="description"/>
                                    <field name="state" widget="badge"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                    <field name="notes" placeholder="Note..."/>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>
    <record id="view_cf_haccp_sp_list" model="ir.ui.view">
        <field name="name">cf.haccp.sp.list</field>
        <field name="model">cf.haccp.sp</field>
        <field name="arch" type="xml">
            <list string="Schede Produzione" decoration-danger="state==\'blocked\'" decoration-success="state==\'released\'">
                <field name="reference"/>
                <field name="date"/>
                <field name="product_id"/>
                <field name="lot_id"/>
                <field name="production_id"/>
                <field name="quantity_produced"/>
                <field name="operator_id" widget="many2one_avatar_user"/>
                <field name="state" widget="badge"/>
            </list>
        </field>
    </record>
</odoo>
''')

write('casafolino_haccp/views/cf_haccp_nc_views.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_cf_haccp_nc_form" model="ir.ui.view">
        <field name="name">cf.haccp.nc.form</field>
        <field name="model">cf.haccp.nc</field>
        <field name="arch" type="xml">
            <form string="Non Conformita">
                <header>
                    <button name="action_close" type="object" string="Chiudi" class="btn-success" attrs="{'invisible': [('state','=','closed')]}"/>
                    <field name="state" widget="statusbar" statusbar_visible="open,analysis,action,verified,closed"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="reference" readonly="1"/></h1>
                    </div>
                    <group>
                        <group>
                            <field name="origin"/>
                            <field name="severity" widget="badge" decoration-danger="severity in (\'high\',\'critical\')" decoration-warning="severity==\'medium\'"/>
                            <field name="product_id"/>
                            <field name="lot_id"/>
                        </group>
                        <group>
                            <field name="date"/>
                            <field name="reported_by" widget="many2one_avatar_user"/>
                            <field name="assigned_to" widget="many2one_avatar_user"/>
                            <field name="sp_id"/>
                        </group>
                    </group>
                    <group string="Descrizione">
                        <field name="description" nolabel="1"/>
                    </group>
                    <group string="Azione Correttiva">
                        <field name="corrective_action" nolabel="1"/>
                    </group>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>
    <record id="view_cf_haccp_nc_list" model="ir.ui.view">
        <field name="name">cf.haccp.nc.list</field>
        <field name="model">cf.haccp.nc</field>
        <field name="arch" type="xml">
            <list string="Non Conformita" decoration-danger="severity in (\'high\',\'critical\')" decoration-warning="severity==\'medium\'">
                <field name="reference"/>
                <field name="date"/>
                <field name="origin"/>
                <field name="severity" widget="badge" decoration-danger="severity in (\'high\',\'critical\')"/>
                <field name="description"/>
                <field name="assigned_to" widget="many2one_avatar_user"/>
                <field name="state" widget="badge"/>
            </list>
        </field>
    </record>
</odoo>
''')

write('casafolino_haccp/views/cf_haccp_calibration_views.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_cf_haccp_calibration_form" model="ir.ui.view">
        <field name="name">cf.haccp.calibration.form</field>
        <field name="model">cf.haccp.calibration</field>
        <field name="arch" type="xml">
            <form string="Calibrazione Strumento">
                <header>
                    <field name="state" widget="statusbar"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="instrument_name"/></h1>
                        <h3><field name="instrument_code"/></h3>
                    </div>
                    <group>
                        <group>
                            <field name="instrument_type"/>
                            <field name="location"/>
                            <field name="workcenter_id"/>
                        </group>
                        <group>
                            <field name="date_last_calibration"/>
                            <field name="date_next_calibration"/>
                            <field name="calibration_interval_months"/>
                            <field name="calibrated_by" widget="many2one_avatar_user"/>
                            <field name="certificate_ref"/>
                            <field name="result_ok"/>
                        </group>
                    </group>
                    <field name="notes" placeholder="Note..."/>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>
    <record id="view_cf_haccp_calibration_list" model="ir.ui.view">
        <field name="name">cf.haccp.calibration.list</field>
        <field name="model">cf.haccp.calibration</field>
        <field name="arch" type="xml">
            <list string="Calibrazioni" decoration-danger="state==\'expired\'" decoration-warning="state==\'expiring\'">
                <field name="instrument_name"/>
                <field name="instrument_code"/>
                <field name="instrument_type"/>
                <field name="location"/>
                <field name="date_last_calibration"/>
                <field name="date_next_calibration"/>
                <field name="calibrated_by" widget="many2one_avatar_user"/>
                <field name="state" widget="badge" decoration-success="state==\'valid\'" decoration-warning="state==\'expiring\'" decoration-danger="state==\'expired\'"/>
            </list>
        </field>
    </record>
</odoo>
''')

write('casafolino_haccp/views/cf_haccp_quarantine_views.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_cf_haccp_quarantine_form" model="ir.ui.view">
        <field name="name">cf.haccp.quarantine.form</field>
        <field name="model">cf.haccp.quarantine</field>
        <field name="arch" type="xml">
            <form string="Quarantena">
                <header>
                    <button name="action_release" type="object" string="Rilascia" class="btn-success" attrs="{'invisible': [('state','!=','active')]}"/>
                    <button name="action_destroy" type="object" string="Distruggi" class="btn-danger" attrs="{'invisible': [('state','!=','active')]}"/>
                    <field name="state" widget="statusbar"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="reference" readonly="1"/></h1>
                    </div>
                    <group>
                        <group>
                            <field name="lot_id"/>
                            <field name="product_id"/>
                            <field name="receipt_id"/>
                        </group>
                        <group>
                            <field name="date_start"/>
                            <field name="date_end"/>
                            <field name="operator_id" widget="many2one_avatar_user"/>
                            <field name="location"/>
                        </group>
                    </group>
                    <group string="Motivo">
                        <field name="reason" nolabel="1"/>
                    </group>
                    <group string="Risoluzione">
                        <field name="resolution" nolabel="1"/>
                    </group>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>
</odoo>
''')

write('casafolino_haccp/views/cf_haccp_document_views.xml', '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_cf_haccp_document_form" model="ir.ui.view">
        <field name="name">cf.haccp.document.form</field>
        <field name="model">cf.haccp.document</field>
        <field name="arch" type="xml">
            <form string="Documento HACCP">
                <header>
                    <field name="state" widget="statusbar"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="name"/></h1>
                    </div>
                    <group>
                        <group>
                            <field name="doc_type"/>
                            <field name="partner_id"/>
                            <field name="product_id"/>
                            <field name="document_ref"/>
                        </group>
                        <group>
                            <field name="date_issue"/>
                            <field name="date_expiry"/>
                        </group>
                    </group>
                    <field name="attachment_ids" widget="many2many_binary"/>
                    <field name="notes" placeholder="Note..."/>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>
    <record id="view_cf_haccp_document_list" model="ir.ui.view">
        <field name="name">cf.haccp.document.list</field>
        <field name="model">cf.haccp.document</field>
        <field name="arch" type="xml">
            <list decoration-danger="state==\'expired\'" decoration-warning="state==\'expiring\'">
                <field name="name"/>
                <field name="doc_type"/>
                <field name="partner_id"/>
                <field name="date_expiry"/>
                <field name="state" widget="badge" decoration-success="state==\'valid\'" decoration-warning="state==\'expiring\'" decoration-danger="state==\'expired\'"/>
            </list>
        </field>
    </record>
</odoo>
''')

# Aggiorna manifest con le viste
write('casafolino_haccp/__manifest__.py', '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino HACCP",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "HACCP Manager nativo Odoo 18",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "mrp", "stock", "purchase", "product"],
    "data": [
        "security/cf_haccp_security.xml",
        "security/ir.model.access.csv",
        "data/cf_haccp_sequences.xml",
        "views/cf_haccp_receipt_views.xml",
        "views/cf_haccp_sp_views.xml",
        "views/cf_haccp_nc_views.xml",
        "views/cf_haccp_quarantine_views.xml",
        "views/cf_haccp_calibration_views.xml",
        "views/cf_haccp_document_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''')
print('✅ Viste HACCP complete')
