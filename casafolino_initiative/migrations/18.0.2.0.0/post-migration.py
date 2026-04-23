import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# Atoms with generate_on_create=False (manual atoms)
MANUAL_ATOMS = {'A01', 'A07', 'A08', 'A09', 'A10', 'A15'}

# Subject templates per atom code
SUBJECT_TEMPLATES = {
    'A02': 'Invio listino a {{object.initiative_id.partner_id.name}}',
    'A03': 'Spedizione sample — {{object.initiative_id.name}}',
    'A04': 'Follow-up {{object.initiative_id.partner_id.name}}',
    'A05': 'Offerta {{object.initiative_id.partner_id.name}} — {{object.initiative_id.code}}',
    'A06': 'Attendere approvazione {{object.initiative_id.partner_id.name}}',
    'A11': 'Brief avvio — {{object.initiative_id.name}}',
    'A12': 'Debrief — {{object.initiative_id.name}}',
    'A13': 'Prenotazione logistica {{object.initiative_id.name}}',
    'A14': 'Preparazione kit — {{object.initiative_id.name}}',
    'A16': 'Brief etichetta — {{object.initiative_id.name}}',
    'A17': 'Mockup etichetta — {{object.initiative_id.name}}',
    'A18': 'Stampa etichette — {{object.initiative_id.name}}',
    'A19': 'Brief prodotto nuovo — {{object.initiative_id.name}}',
    'A20': 'Prototipo — {{object.initiative_id.name}}',
    'A21': 'TDS + Allergeni — {{object.initiative_id.name}}',
    'A22': 'Test shelf-life — {{object.initiative_id.name}}',
    'A23': 'Documenti cert. — {{object.initiative_id.name}}',
    'A24': 'Audit cert. — {{object.initiative_id.name}}',
    'A25': 'Shooting — {{object.initiative_id.name}}',
    'A26': 'Milestone review — {{object.initiative_id.name}}',
    'A27': 'Competitive intel — {{object.initiative_id.partner_id.name}}',
    'A28': 'Onboarding — {{object.initiative_id.partner_id.name}}',
    'A29': 'Nuova referenza — {{object.initiative_id.name}}',
    'A30': 'Complaint — {{object.initiative_id.partner_id.name}}',
    'A31': 'Rinnovo cert. — {{object.initiative_id.name}}',
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    atoms = env['cf.initiative.atom'].search([])
    updated = 0
    for atom in atoms:
        vals = {}
        if atom.code in MANUAL_ATOMS:
            vals['generate_on_create'] = False
        else:
            vals['generate_on_create'] = True
        if atom.code in SUBJECT_TEMPLATES:
            vals['subject_template'] = SUBJECT_TEMPLATES[atom.code]
        if vals:
            atom.write(vals)
            updated += 1

    # Set existing atom_lines generation_state based on their atom config
    lines = env['cf.initiative.atom.line'].search([('generation_state', '=', 'pending')])
    for line in lines:
        if not line.atom_id.generate_on_create:
            line.generation_state = 'manual'

    _logger.info('F2 migration: updated %d atoms, processed %d atom lines', updated, len(lines))
