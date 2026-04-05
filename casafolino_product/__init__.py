from . import models


def post_init_hook(env):
    """Rimuove view duplicate lasciate da merge di moduli precedenti."""
    View = env['ir.ui.view']
    IrData = env['ir.model.data']

    canonical_xmlids = [
        'casafolino_product.view_mrp_bom_allergen_tab',
        'casafolino_product.view_mrp_bom_nutrition_tab',
    ]
    canonical_ids = set()
    for xmlid in canonical_xmlids:
        rec = env.ref(xmlid, raise_if_not_found=False)
        if rec:
            canonical_ids.add(rec.id)

    base_bom_view = env.ref('mrp.mrp_bom_form_view', raise_if_not_found=False)
    if not base_bom_view:
        return

    # Nomi che potrebbero identificare view duplicate da vecchi moduli
    stale_names = {
        'mrp.bom.allergen.tab',
        'mrp.bom.allergen',
        'mrp.bom.form.allergen',
        'mrp.bom.form.nutrition',
        'mrp.bom.nutrition.tab',
        'mrp.bom.nutrition',
    }
    duplicates = View.search([
        ('inherit_id', '=', base_bom_view.id),
        ('model', '=', 'mrp.bom'),
        ('id', 'not in', list(canonical_ids)),
        ('name', 'in', list(stale_names)),
    ])
    if duplicates:
        duplicates.sudo().unlink()
