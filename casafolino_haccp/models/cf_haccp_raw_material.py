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
        string="Fornitori Approvati", domain="[(\"supplier_rank\", \">\", 0)]")
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
