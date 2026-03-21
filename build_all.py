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
