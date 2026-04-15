-- ══════════════════════════════════════════════════════════════
-- STEP 1: Map partner_id sulle righe bancarie non riconciliate
-- Eseguire su EC2 con:
--   sudo docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -f /tmp/reconcile_step1_map_partners.sql
-- ══════════════════════════════════════════════════════════════

-- Pre-check: quante righe senza partner?
SELECT 'BEFORE' as step,
       COUNT(*) as total_bsl,
       COUNT(*) FILTER (WHERE am.partner_id IS NULL) as no_partner,
       COUNT(*) FILTER (WHERE am.partner_id IS NOT NULL) as with_partner
FROM account_bank_statement_line bsl
JOIN account_move am ON am.id = bsl.move_id
WHERE bsl.is_reconciled = false;

-- Mapping clienti principali
UPDATE account_move am SET partner_id = sub.pid
FROM (
  SELECT bsl.move_id,
    CASE
      WHEN bsl.payment_ref ILIKE '%RE ITALO%' THEN 7422
      WHEN bsl.payment_ref ILIKE '%BENSI%' THEN 7338
      WHEN bsl.payment_ref ILIKE '%ITALIANA BAKERY%' THEN 7384
      WHEN bsl.payment_ref ILIKE '%DEGUSTA%' AND bsl.payment_ref ILIKE '%ES%' THEN 8209
      WHEN bsl.payment_ref ILIKE '%DEGUSTA%' AND bsl.payment_ref ILIKE '%DE%' THEN 15740
      WHEN bsl.payment_ref ILIKE '%DEGUSTA%' AND bsl.payment_ref ILIKE '%UK%' THEN 15615
      WHEN bsl.payment_ref ILIKE '%DEGUSTA%' AND bsl.payment_ref ILIKE '%FR%' THEN 15783
      WHEN bsl.payment_ref ILIKE '%DEGUSTA%' THEN 15776
      WHEN bsl.payment_ref ILIKE '%MISONO%' THEN 7594
      WHEN bsl.payment_ref ILIKE '%VOLTEM%' THEN 61123
      WHEN bsl.payment_ref ILIKE '%JUSAMI%' THEN 7388
      WHEN bsl.payment_ref ILIKE '%CIOFFIS%' THEN 7811
      WHEN bsl.payment_ref ILIKE '%ICHOOSE%' THEN 16163
      WHEN bsl.payment_ref ILIKE '%HEALTHY BRANDING%' THEN 15654
      WHEN bsl.payment_ref ILIKE '%EUROPA COMMERCIALE%' THEN 5012
      WHEN bsl.payment_ref ILIKE '%MARTELLI%' THEN 16145
      WHEN bsl.payment_ref ILIKE '%CONCA%' THEN 7357
      WHEN bsl.payment_ref ILIKE '%CARDACE%' THEN 7416
      WHEN bsl.payment_ref ILIKE '%PIROZZI%' THEN 16816
      WHEN bsl.payment_ref ILIKE '%MARANO%' THEN 7401
      WHEN bsl.payment_ref ILIKE '%PERSEPOLI%' THEN 16122
      WHEN bsl.payment_ref ILIKE '%CIPTRONIC%' THEN 15690
      WHEN bsl.payment_ref ILIKE '%TASWIK%' THEN 7440
      WHEN bsl.payment_ref ILIKE '%BRANDITALIA%' THEN 7344
      WHEN bsl.payment_ref ILIKE '%VALENTINO%' AND bsl.payment_ref ILIKE '%FOOD%' THEN 7803
      WHEN bsl.payment_ref ILIKE '%MARKETING PETROLI%' THEN 7595
      WHEN bsl.payment_ref ILIKE '%AMERONGEN%' THEN 7370
      WHEN bsl.payment_ref ILIKE '%HOFER%' THEN (SELECT id FROM res_partner WHERE name ILIKE '%Hofer KG%' LIMIT 1)
      WHEN bsl.payment_ref ILIKE '%FENICE FOOD%' THEN (SELECT id FROM res_partner WHERE name ILIKE '%Fenice Food%' LIMIT 1)
      WHEN bsl.payment_ref ILIKE '%ANTICA PASTICCERIA%' THEN (SELECT id FROM res_partner WHERE name ILIKE '%Antica Pasticceria%' LIMIT 1)
      WHEN bsl.payment_ref ILIKE '%CUORDIFARINA%' THEN (SELECT id FROM res_partner WHERE name ILIKE '%Cuordifarina%' LIMIT 1)
      WHEN bsl.payment_ref ILIKE '%PARENTE S.R.L%' THEN (SELECT id FROM res_partner WHERE name ILIKE '%Parente S.R.L%' LIMIT 1)
      WHEN bsl.payment_ref ILIKE '%CONAL FOOD%' THEN (SELECT id FROM res_partner WHERE name ILIKE '%Conal Food%' LIMIT 1)
      WHEN bsl.payment_ref ILIKE '%FATTORIA SILA%' THEN (SELECT id FROM res_partner WHERE name ILIKE '%Fattoria Sila%' LIMIT 1)
      WHEN bsl.payment_ref ILIKE '%NETO FERDINANDO%' THEN (SELECT id FROM res_partner WHERE name ILIKE '%Neto Ferdinando%' LIMIT 1)
      WHEN bsl.payment_ref ILIKE '%STRIPE%' THEN (SELECT id FROM res_partner WHERE name ILIKE '%Stripe%' AND is_company = true LIMIT 1)
      WHEN bsl.payment_ref ILIKE '%AMAZON%' THEN (SELECT id FROM res_partner WHERE name ILIKE '%Amazon%' AND is_company = true LIMIT 1)
      WHEN bsl.payment_ref ILIKE '%SHOPIFY%' THEN (SELECT id FROM res_partner WHERE name ILIKE '%Shopify%' LIMIT 1)
      WHEN bsl.payment_ref ILIKE '%BILAIT%' THEN 7342
    END as pid
  FROM account_bank_statement_line bsl
  JOIN account_move am2 ON am2.id = bsl.move_id
  WHERE bsl.is_reconciled = false AND am2.partner_id IS NULL
) sub
WHERE am.id = sub.move_id AND sub.pid IS NOT NULL AND am.partner_id IS NULL;

-- Mapping anche sulle account_move_line collegate (partner sulla riga contabile)
UPDATE account_move_line aml SET partner_id = am.partner_id
FROM account_move am
JOIN account_bank_statement_line bsl ON bsl.move_id = am.id
WHERE aml.move_id = am.id
  AND aml.partner_id IS NULL
  AND am.partner_id IS NOT NULL
  AND bsl.is_reconciled = false;

-- Post-check
SELECT 'AFTER' as step,
       COUNT(*) as total_bsl,
       COUNT(*) FILTER (WHERE am.partner_id IS NULL) as no_partner,
       COUNT(*) FILTER (WHERE am.partner_id IS NOT NULL) as with_partner
FROM account_bank_statement_line bsl
JOIN account_move am ON am.id = bsl.move_id
WHERE bsl.is_reconciled = false;

-- Top partner mappati
SELECT rp.name, COUNT(*) as righe_mappate
FROM account_bank_statement_line bsl
JOIN account_move am ON am.id = bsl.move_id
JOIN res_partner rp ON rp.id = am.partner_id
WHERE bsl.is_reconciled = false
GROUP BY rp.name
ORDER BY righe_mappate DESC
LIMIT 20;
