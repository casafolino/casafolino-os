-- ══════════════════════════════════════════════════════════════
-- STEP 3: Verifica post-riconciliazione
-- ══════════════════════════════════════════════════════════════

-- Stato BSL per journal
SELECT
  aj.name as journal,
  COUNT(*) as totale,
  COUNT(*) FILTER (WHERE bsl.is_reconciled = true) as riconciliate,
  COUNT(*) FILTER (WHERE bsl.is_reconciled = false) as da_riconciliare
FROM account_bank_statement_line bsl
JOIN account_move am ON am.id = bsl.move_id
JOIN account_journal aj ON aj.id = bsl.journal_id
GROUP BY aj.name
ORDER BY aj.name;

-- Fatture aperte residue
SELECT
  CASE WHEN move_type IN ('out_invoice','out_refund') THEN 'CLIENTI' ELSE 'FORNITORI' END as tipo,
  COUNT(*) as n_fatture,
  ROUND(SUM(amount_residual)::numeric, 2) as residuo_totale
FROM account_move
WHERE state = 'posted'
  AND payment_state IN ('not_paid','partial')
  AND move_type IN ('out_invoice','out_refund','in_invoice','in_refund')
GROUP BY CASE WHEN move_type IN ('out_invoice','out_refund') THEN 'CLIENTI' ELSE 'FORNITORI' END;

-- Top 20 partner con BSL non riconciliate (per sapere dove lavorare)
SELECT
  COALESCE(rp.name, '** SENZA PARTNER **') as partner,
  COUNT(*) as righe_aperte,
  ROUND(SUM(bsl.amount)::numeric, 2) as totale
FROM account_bank_statement_line bsl
JOIN account_move am ON am.id = bsl.move_id
LEFT JOIN res_partner rp ON rp.id = am.partner_id
WHERE bsl.is_reconciled = false
GROUP BY rp.name
ORDER BY ABS(SUM(bsl.amount)) DESC
LIMIT 20;

-- BSL senza partner che hanno payment_ref con nomi riconoscibili
SELECT
  bsl.payment_ref,
  bsl.amount,
  am.date
FROM account_bank_statement_line bsl
JOIN account_move am ON am.id = bsl.move_id
WHERE bsl.is_reconciled = false
  AND am.partner_id IS NULL
  AND ABS(bsl.amount) > 500
ORDER BY ABS(bsl.amount) DESC
LIMIT 30;
