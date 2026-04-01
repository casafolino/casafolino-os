# -*- coding: utf-8 -*-
"""
Migration 18.0.3.1.0 — Rimuovi modelli fantasma dal DB.

casafolino.task e casafolino.b2b.approve.wizard non esistono più nel codice
ma rimangono come righe orfane in ir_model / ir_model_data,
causando warning ad ogni avvio.
"""
import logging

_logger = logging.getLogger(__name__)

GHOST_MODELS = [
    "casafolino.task",
    "casafolino.b2b.approve.wizard",
]


def migrate(cr, version):
    for model in GHOST_MODELS:
        # Rimuovi da ir_model_data (evita cascata su altri record)
        cr.execute(
            "DELETE FROM ir_model_data WHERE model = 'ir.model' "
            "AND res_id IN (SELECT id FROM ir_model WHERE model = %s)",
            (model,),
        )
        rows = cr.rowcount
        if rows:
            _logger.info("Migration: rimosso %d ir_model_data per modello fantasma '%s'", rows, model)

        # Rimuovi da ir_model
        cr.execute("DELETE FROM ir_model WHERE model = %s", (model,))
        rows = cr.rowcount
        if rows:
            _logger.info("Migration: rimosso modello fantasma '%s' da ir_model", model)
