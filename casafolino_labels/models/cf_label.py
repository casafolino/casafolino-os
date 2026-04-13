from odoo import models, fields


class CasafolinoLabel(models.Model):
    _name = 'casafolino.label'
    _description = 'Pipeline Etichette CasaFolino'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'deadline asc, id desc'

    # ── Identificazione ──────────────────────────────────────────────
    name = fields.Char('Nome etichetta', required=True, tracking=True)
    product_id = fields.Many2one('product.template', string='Prodotto')
    sku = fields.Char('SKU')
    version = fields.Char('Versione', default='v1')

    # ── Pipeline stage ───────────────────────────────────────────────
    stage = fields.Selection([
        ('recipe', 'Ricetta in sviluppo'),
        ('specs', 'Specifiche → Marketing'),
        ('draft', 'Bozza grafica'),
        ('quality', 'Controllo Qualità'),
        ('revision', 'Revisioni'),
        ('printing', 'Approvato → In stampa'),
        ('archived', 'Archiviata'),
    ], string='Fase', default='recipe', tracking=True, group_expand='_group_expand_stage')

    # ── Responsabile e destinazione ──────────────────────────────────
    responsible_id = fields.Many2one('res.users', string='Responsabile',
                                      default=lambda self: self.env.uid, tracking=True)
    market_ids = fields.Many2many('res.country',
        'casafolino_label_country_rel', 'label_id', 'country_id',
        string='Mercati di destinazione')
    languages = fields.Char('Lingue', help='Es. IT, EN, DE')
    deadline = fields.Date('Scadenza', tracking=True)

    # ── Checklist Fase 1 - Dati Tecnici ──────────────────────────────
    check_recipe = fields.Boolean('Ricetta definita')
    check_perc = fields.Boolean('Percentuali ingredienti caratterizzanti')
    check_origin = fields.Boolean('Origine indicata dove obbligatorio')
    check_nutrition = fields.Boolean('Tabelle nutrizionali aggiornate')
    check_diary = fields.Boolean('Diario di produzione compilato')

    # ── Checklist Fase 2 - Legale e Sicurezza ────────────────────────
    check_allergens = fields.Boolean('Allergeni evidenziati')
    check_company = fields.Boolean('Ragione sociale corretta')
    check_lot = fields.Boolean('Spazio lotto/TMC presente')
    check_eco = fields.Boolean('Codici smaltimento presenti')

    # ── Checklist Fase 3 - Visual & Layout ───────────────────────────
    check_size = fields.Boolean('Dimensioni fustella corrette')
    check_readability = fields.Boolean('Font e contrasto leggibili')
    check_languages = fields.Boolean('Tutte le traduzioni presenti')
    check_ean = fields.Boolean('Codice EAN corretto e scansionabile')

    # ── Note ─────────────────────────────────────────────────────────
    notes = fields.Html('Note generali')
    quality_notes = fields.Text('Note controllo qualità')

    # ── Audit ────────────────────────────────────────────────────────
    active = fields.Boolean(default=True)

    def _group_expand_stage(self, stages, domain, order):
        """Mostra tutte le colonne stage nel kanban anche se vuote."""
        return [key for key, _ in self._fields['stage'].selection]
