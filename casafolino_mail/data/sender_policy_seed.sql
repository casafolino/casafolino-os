-- sender_policy_seed.sql
-- Auto-generated from mail recon analysis (5 months)
-- Date: 2026-05-05
-- DO NOT execute on folinofood (prod) without explicit approval

BEGIN;

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — billa.at', 'domain', 'billa.at', 'auto_keep', 90, true, true,
    'BILLA (REWE group) buyer', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'billa.at' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_INTERNAL — casafolino.com', 'domain', 'casafolino.com', 'auto_keep', 90, true, false,
    'Team CasaFolino', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'casafolino.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — contactlbb.com', 'domain', 'contactlbb.com', 'auto_keep', 90, true, true,
    'LBB — top contact volume, commercial partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'contactlbb.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — hofer.at', 'domain', 'hofer.at', 'auto_keep', 90, true, true,
    'Hofer (REWE/ALDI group) buyer', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'hofer.at' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — acmefood.com', 'domain', 'acmefood.com', 'auto_keep', 85, true, true,
    'ACME Food — Biofach', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'acmefood.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — acmeimport.com', 'domain', 'acmeimport.com', 'auto_keep', 85, true, true,
    'ACME Import — Summer Fancy Food', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'acmeimport.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — altios.com', 'domain', 'altios.com', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'altios.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — aristospice.com', 'domain', 'aristospice.com', 'auto_keep', 85, true, true,
    'Aristospice — Summer Fancy Food', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'aristospice.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — basalfoods.com', 'domain', 'basalfoods.com', 'auto_keep', 85, true, true,
    'Basal Foods — active project (chili crisp)', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'basalfoods.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — belgustofood.com', 'domain', 'belgustofood.com', 'auto_keep', 85, true, true,
    'Bel Gusto Food — commercial', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'belgustofood.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — blm-pantos.de', 'domain', 'blm-pantos.de', 'auto_keep', 85, true, true,
    'BLM Pantos — dm Bio / Asia promo', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'blm-pantos.de' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — bosanet.com', 'domain', 'bosanet.com', 'auto_keep', 85, true, true,
    'Bosa Foods — known contact', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'bosanet.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — callipogroup.com', 'domain', 'callipogroup.com', 'auto_keep', 85, true, true,
    'Callipo Group — presentazione', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'callipogroup.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — carbonefinefood.com', 'domain', 'carbonefinefood.com', 'auto_keep', 85, true, true,
    'Carbone Fine Food — PLMA', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'carbonefinefood.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — cencosud.com.ar', 'domain', 'cencosud.com.ar', 'auto_keep', 85, true, true,
    'Cencosud Argentina — retail buyer', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'cencosud.com.ar' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — chapterfoods.com', 'domain', 'chapterfoods.com', 'auto_keep', 85, true, true,
    'Chapter Foods — PLMA', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'chapterfoods.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — chocolateworks.com', 'domain', 'chocolateworks.com', 'auto_keep', 85, true, true,
    'Chocolate Works — PLMA follow-up', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'chocolateworks.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — choosenj.com', 'domain', 'choosenj.com', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'choosenj.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — cioffisgroup.com', 'domain', 'cioffisgroup.com', 'auto_keep', 85, true, true,
    'Cioffis Group — quotation', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'cioffisgroup.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — ciptronic.ro', 'domain', 'ciptronic.ro', 'auto_keep', 85, true, true,
    'Ciptronic Romania — condiments stock', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ciptronic.ro' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — clama-int.de', 'domain', 'clama-int.de', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'clama-int.de' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — degustabox.com', 'domain', 'degustabox.com', 'auto_keep', 85, true, true,
    'Degusta Box — partnership', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'degustabox.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — deliterraneus.com', 'domain', 'deliterraneus.com', 'auto_keep', 85, true, true,
    'Deliterraneus — vodka sauce PL', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'deliterraneus.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — dietbox.es', 'domain', 'dietbox.es', 'auto_keep', 85, true, true,
    'DietBox Spain — collaboration', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'dietbox.es' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — diplomat-global.com', 'domain', 'diplomat-global.com', 'auto_keep', 85, true, true,
    'Diplomat Global — Marca', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'diplomat-global.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — egicompany.com', 'domain', 'egicompany.com', 'auto_keep', 85, true, true,
    'EGI Company — Sigep', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'egicompany.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — eronkantech.com', 'domain', 'eronkantech.com', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'eronkantech.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — flexpet.nl', 'domain', 'flexpet.nl', 'auto_keep', 85, true, true,
    'FlexPET Netherlands — packaging', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'flexpet.nl' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — ftm-ns.be', 'domain', 'ftm-ns.be', 'auto_keep', 85, true, true,
    'FTM NS Belgium — active orders', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ftm-ns.be' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — gauscento.kr', 'domain', 'gauscento.kr', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gauscento.kr' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — gelatogranucci.com', 'domain', 'gelatogranucci.com', 'auto_keep', 85, true, true,
    'Gelato Granucci — Las Vegas', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gelatogranucci.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — giafoods.com', 'domain', 'giafoods.com', 'auto_keep', 85, true, true,
    'Gia Foods — spreads', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'giafoods.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — groupeaksal.com', 'domain', 'groupeaksal.com', 'auto_keep', 85, true, true,
    'Groupe Aksal — samples + orders', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'groupeaksal.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — gsitalia.com', 'domain', 'gsitalia.com', 'auto_keep', 85, true, true,
    'GS Italia', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gsitalia.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — gustusnapoli.com', 'domain', 'gustusnapoli.com', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gustusnapoli.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — henaninternational.com', 'domain', 'henaninternational.com', 'auto_keep', 85, true, true,
    'Henan International — TuttoFood', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'henaninternational.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — incucinaconpatty.it', 'domain', 'incucinaconpatty.it', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'incucinaconpatty.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — intermar.es', 'domain', 'intermar.es', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'intermar.es' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — italianproducts.com', 'domain', 'italianproducts.com', 'auto_keep', 85, true, true,
    'Italian Products & Beyond — PO', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'italianproducts.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — jusamiimports.com', 'domain', 'jusamiimports.com', 'auto_keep', 85, true, true,
    'Jusami Imports — SIAL', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'jusamiimports.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — kayco.com', 'domain', 'kayco.com', 'auto_keep', 85, true, true,
    'Kayco — PLMA follow-up', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'kayco.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — lasomadis.com', 'domain', 'lasomadis.com', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'lasomadis.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — live-organic.co.il', 'domain', 'live-organic.co.il', 'auto_keep', 85, true, true,
    'Live Organic Israel — Biofach', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'live-organic.co.il' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — mail.fieramilano.it', 'domain', 'mail.fieramilano.it', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'mail.fieramilano.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — miasiagroup.com', 'domain', 'miasiagroup.com', 'auto_keep', 85, true, true,
    'MI Asia Group — import inquiry', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'miasiagroup.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — ncubexpo.com', 'domain', 'ncubexpo.com', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ncubexpo.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — noricum.si', 'domain', 'noricum.si', 'auto_keep', 85, true, true,
    'Noricum Slovenia — SANA Food', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'noricum.si' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — northcoast.com.pl', 'domain', 'northcoast.com.pl', 'auto_keep', 85, true, true,
    'North Coast Poland — Tutto Food', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'northcoast.com.pl' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — nutkao.com', 'domain', 'nutkao.com', 'auto_keep', 85, true, true,
    'Nutkao — ricette proposta', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'nutkao.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — productguru.co', 'domain', 'productguru.co', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'productguru.co' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — proservicebrokerage.com', 'domain', 'proservicebrokerage.com', 'auto_keep', 85, true, true,
    'Pro Service Brokerage — Costco', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'proservicebrokerage.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — quotaly.co', 'domain', 'quotaly.co', 'auto_keep', 85, true, true,
    'Quotaly — procurement contacts', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'quotaly.co' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — redcare-pharmacy.com', 'domain', 'redcare-pharmacy.com', 'auto_keep', 85, true, true,
    'Redcare Pharmacy — onboarding', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'redcare-pharmacy.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — remma.ru', 'domain', 'remma.ru', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'remma.ru' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — rohlik.cz', 'domain', 'rohlik.cz', 'auto_keep', 85, true, true,
    'Rohlik Czech — TuttoFood follow-up', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'rohlik.cz' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — rscompras.com', 'domain', 'rscompras.com', 'auto_keep', 85, true, true,
    'RS Compras — Riba Smith Panama', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'rscompras.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — sardofoods.com', 'domain', 'sardofoods.com', 'auto_keep', 85, true, true,
    'Sardo Foods — PLMA follow-up', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'sardofoods.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — scrumptiousbrands.com', 'domain', 'scrumptiousbrands.com', 'auto_keep', 85, true, true,
    'Scrumptious Brands — Fancy Faire', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'scrumptiousbrands.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — shop-fever.com', 'domain', 'shop-fever.com', 'auto_keep', 85, true, true,
    'ShopFever — Asia ecommerce', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'shop-fever.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — startex.ai', 'domain', 'startex.ai', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'startex.ai' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — symulfinance.com', 'domain', 'symulfinance.com', 'auto_keep', 85, true, true,
    'Symul Finance — contratto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'symulfinance.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — synergyind.com.hk', 'domain', 'synergyind.com.hk', 'auto_keep', 85, true, true,
    'Synergy HK — price list', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'synergyind.com.hk' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — tc-markets.com', 'domain', 'tc-markets.com', 'auto_keep', 85, true, true,
    'TC Markets — catalog/pricing', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'tc-markets.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — treurkaas.nl', 'domain', 'treurkaas.nl', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'treurkaas.nl' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — tropic.ba', 'domain', 'tropic.ba', 'auto_keep', 85, true, true,
    'Tropic Bosnia — Biofach', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'tropic.ba' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — twlspa.com', 'domain', 'twlspa.com', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'twlspa.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — unisrl.it', 'domain', 'unisrl.it', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'unisrl.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — vegora.com', 'domain', 'vegora.com', 'auto_keep', 85, true, true,
    'Vegora — active orders/reorder', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'vegora.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — visiodp.com', 'domain', 'visiodp.com', 'auto_keep', 85, true, true,
    'Visio DP — forecast management', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'visiodp.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — way2global.com', 'domain', 'way2global.com', 'auto_keep', 85, true, true,
    'Domain matches active CRM lead', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'way2global.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_CRITICAL — wuerth-biokaese.de', 'domain', 'wuerth-biokaese.de', 'auto_keep', 85, true, true,
    'Würth — organic cheese/payments', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'wuerth-biokaese.de' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — 3.basecamp.com', 'domain', '3.basecamp.com', 'auto_keep', 70, true, true,
    'Basecamp — project mgmt with agency', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = '3.basecamp.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — absfood.com', 'domain', 'absfood.com', 'auto_keep', 70, true, true,
    'ABS Food — materie prime', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'absfood.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — ac-finance.it', 'domain', 'ac-finance.it', 'auto_keep', 70, true, true,
    'AC Finance — contratto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ac-finance.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — aciexpress.net', 'domain', 'aciexpress.net', 'auto_keep', 70, true, true,
    'ACI Express — invoice', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'aciexpress.net' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — adv-pax.de', 'domain', 'adv-pax.de', 'auto_keep', 70, true, true,
    'ADV-PAX — Anuga visit', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'adv-pax.de' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — ahlan-herbs.com', 'domain', 'ahlan-herbs.com', 'auto_keep', 70, true, true,
    'Ahlan Herbs — spearmint/peppermint', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ahlan-herbs.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — aism.it', 'domain', 'aism.it', 'auto_keep', 70, true, true,
    'AISM — catalogo richiesta', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'aism.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — alphabetcity.it', 'domain', 'alphabetcity.it', 'auto_keep', 70, true, true,
    'AlphabetCity — collaborazione', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'alphabetcity.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — alpiworld.com', 'domain', 'alpiworld.com', 'auto_keep', 70, true, true,
    'Alpi World — trasporto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'alpiworld.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — analytec.at', 'domain', 'analytec.at', 'auto_keep', 70, true, true,
    'Analytec — invoice reminder', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'analytec.at' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — apadolci.it', 'domain', 'apadolci.it', 'auto_keep', 70, true, true,
    'APA Dolci — TuttoFood', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'apadolci.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — arpaiaspa.it', 'domain', 'arpaiaspa.it', 'auto_keep', 70, true, true,
    'Arpaia — estratto conto/ordini', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'arpaiaspa.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — artemar-sped.com', 'domain', 'artemar-sped.com', 'auto_keep', 70, true, true,
    'Artemar — spedizioni', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'artemar-sped.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — artigianoinfiera.it', 'domain', 'artigianoinfiera.it', 'auto_keep', 70, true, true,
    'Artigiano in Fiera', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'artigianoinfiera.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — assitur.it', 'domain', 'assitur.it', 'auto_keep', 70, true, true,
    'Assitur — fatture pendenti', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'assitur.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — avanzagroup.com', 'domain', 'avanzagroup.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'avanzagroup.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — avioninternational.com', 'domain', 'avioninternational.com', 'auto_keep', 70, true, true,
    'Avion International — freight', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'avioninternational.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — belfoods.ro', 'domain', 'belfoods.ro', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'belfoods.ro' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — betobee.it', 'domain', 'betobee.it', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'betobee.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — bilait.it', 'domain', 'bilait.it', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'bilait.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — biozentrale.de', 'domain', 'biozentrale.de', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'biozentrale.de' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — blife.cloud', 'domain', 'blife.cloud', 'auto_keep', 70, true, true,
    'B-Life — materie prime offerte', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'blife.cloud' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — bnkragency.com', 'domain', 'bnkragency.com', 'auto_keep', 70, true, true,
    'Low auto/newsletter ratio, 3 messages', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'bnkragency.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — bolognafiere.it', 'domain', 'bolognafiere.it', 'auto_keep', 70, true, true,
    'Bologna Fiere — Marca, SANA', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'bolognafiere.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — brillainfluencers.com', 'domain', 'brillainfluencers.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'brillainfluencers.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — buonitalia.com', 'domain', 'buonitalia.com', 'auto_keep', 70, true, true,
    'Buonitalia — bonifico', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'buonitalia.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — bykwiklok.com', 'domain', 'bykwiklok.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'bykwiklok.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — calcmenu.net', 'domain', 'calcmenu.net', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'calcmenu.net' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — canvaslogistics.pl', 'domain', 'canvaslogistics.pl', 'auto_keep', 70, true, true,
    'Canvas Logistics — transport', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'canvaslogistics.pl' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — cargonord.it', 'domain', 'cargonord.it', 'auto_keep', 70, true, true,
    'Cargonord — shipping', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'cargonord.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — caselli.it', 'domain', 'caselli.it', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'caselli.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — ccis.ch', 'domain', 'ccis.ch', 'auto_keep', 70, true, true,
    'CCIS Switzerland — Taste of Italy', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ccis.ch' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — charltonmediamail.com', 'domain', 'charltonmediamail.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'charltonmediamail.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — cientoluna.com', 'domain', 'cientoluna.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'cientoluna.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — corexpo.it', 'domain', 'corexpo.it', 'auto_keep', 70, true, true,
    'Corexpo — Africa Food Show', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'corexpo.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — coupang.com', 'domain', 'coupang.com', 'auto_keep', 70, true, true,
    'Coupang — marketplace operations', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'coupang.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — cove-srl.com', 'domain', 'cove-srl.com', 'auto_keep', 70, true, true,
    'Cove SRL — ordini/fatture', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'cove-srl.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — cpff.net', 'domain', 'cpff.net', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'cpff.net' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — crm.ice.it', 'domain', 'crm.ice.it', 'auto_keep', 70, true, true,
    'ICE Agenzia — export support', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'crm.ice.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — daudino.it', 'domain', 'daudino.it', 'auto_keep', 70, true, true,
    'Daudino — fatture', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'daudino.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — des-so.com', 'domain', 'des-so.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'des-so.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — designdeskexhibits.sbs', 'domain', 'designdeskexhibits.sbs', 'auto_keep', 70, true, true,
    'Design Desk — SIAL Paris', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'designdeskexhibits.sbs' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — dhl.com', 'domain', 'dhl.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'dhl.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — dijonbourgogne-events.com', 'domain', 'dijonbourgogne-events.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'dijonbourgogne-events.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — dinamicapackaging.it', 'domain', 'dinamicapackaging.it', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'dinamicapackaging.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — easyexporteu.com', 'domain', 'easyexporteu.com', 'auto_keep', 70, true, true,
    'Easy Export EU — Biofach logistics', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'easyexporteu.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — email.pandadoc.net', 'domain', 'email.pandadoc.net', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'email.pandadoc.net' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — eminoglumakina.com', 'domain', 'eminoglumakina.com', 'auto_keep', 70, true, true,
    'Eminoglu — ball mill', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'eminoglumakina.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — enews.ita-airways.com', 'domain', 'enews.ita-airways.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'enews.ita-airways.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — epipoli.com', 'domain', 'epipoli.com', 'auto_keep', 70, true, true,
    'Epipoli — estratto conto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'epipoli.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — eurosender.com', 'domain', 'eurosender.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'eurosender.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — eurovo.com', 'domain', 'eurovo.com', 'auto_keep', 70, true, true,
    'Eurovo — maionese project', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'eurovo.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — exl.eventshq.com', 'domain', 'exl.eventshq.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'exl.eventshq.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — federicobollarino.it', 'domain', 'federicobollarino.it', 'auto_keep', 70, true, true,
    'Bollarino — allestimento MARCA', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'federicobollarino.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — fercam.com', 'domain', 'fercam.com', 'auto_keep', 70, true, true,
    'Fercam — logistics', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'fercam.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — fieramilano.it', 'domain', 'fieramilano.it', 'auto_keep', 70, true, true,
    'Fiera Milano — TuttoFood, MilanoHome', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'fieramilano.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — fiereparma.it', 'domain', 'fiereparma.it', 'auto_keep', 70, true, true,
    'Fiere Parma — TuttoFood agenda', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'fiereparma.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — fioredipuglia.com', 'domain', 'fioredipuglia.com', 'auto_keep', 70, true, true,
    'Fiore di Puglia — industry contact', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'fioredipuglia.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — forward-investments.com', 'domain', 'forward-investments.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'forward-investments.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — freezpak.com', 'domain', 'freezpak.com', 'auto_keep', 70, true, true,
    'FreezPak — transport', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'freezpak.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — gabfoodsco.com', 'domain', 'gabfoodsco.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gabfoodsco.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — gestionefiere.com', 'domain', 'gestionefiere.com', 'auto_keep', 70, true, true,
    'Gestione Fiere — ordini/ammissione', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gestionefiere.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — gestionefiere.it', 'domain', 'gestionefiere.it', 'auto_keep', 70, true, true,
    'Gestione Fiere — ordini acquisto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gestionefiere.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — ginger-media.biz', 'domain', 'ginger-media.biz', 'auto_keep', 70, true, true,
    'Ginger Media — creator prodotti', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ginger-media.biz' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — giordaninox.it', 'domain', 'giordaninox.it', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'giordaninox.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — gluszko.pl', 'domain', 'gluszko.pl', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gluszko.pl' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — gourmets.net', 'domain', 'gourmets.net', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gourmets.net' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — gruppobucciarelli.site', 'domain', 'gruppobucciarelli.site', 'auto_keep', 70, true, true,
    'Low auto/newsletter ratio, 3 messages', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gruppobucciarelli.site' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — gustoitalianfoods.com', 'domain', 'gustoitalianfoods.com', 'auto_keep', 70, true, true,
    'Gusto Italian Foods — immagini', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gustoitalianfoods.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — halaloffice.com', 'domain', 'halaloffice.com', 'auto_keep', 70, true, true,
    'Halal Office — certificazione', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'halaloffice.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — halalqualitycontrol.com', 'domain', 'halalqualitycontrol.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'halalqualitycontrol.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — hampers.co.uk', 'domain', 'hampers.co.uk', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'hampers.co.uk' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — hedessent.com', 'domain', 'hedessent.com', 'auto_keep', 70, true, true,
    'Hedessent — aromi supplier', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'hedessent.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — henoto.com', 'domain', 'henoto.com', 'auto_keep', 70, true, true,
    'Henoto — stand allestimento', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'henoto.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — hlpklearfold.eu', 'domain', 'hlpklearfold.eu', 'auto_keep', 70, true, true,
    'Low auto/newsletter ratio, 3 messages', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'hlpklearfold.eu' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — ice.it', 'domain', 'ice.it', 'auto_keep', 70, true, true,
    'ICE — export/internazionalizzazione', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ice.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — ichooseitalia.com', 'domain', 'ichooseitalia.com', 'auto_keep', 70, true, true,
    'iChoose Italia — Frolle Pautassi', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ichooseitalia.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — iconicteam.it', 'domain', 'iconicteam.it', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'iconicteam.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — iegasia.com.sg', 'domain', 'iegasia.com.sg', 'auto_keep', 70, true, true,
    'IEG Asia — Sigep Asia', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'iegasia.com.sg' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — iegexpo.it', 'domain', 'iegexpo.it', 'auto_keep', 70, true, true,
    'IEG Expo — Sigep', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'iegexpo.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — imageallestimenti.it', 'domain', 'imageallestimenti.it', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'imageallestimenti.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — imagingtechsalerator.com', 'domain', 'imagingtechsalerator.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'imagingtechsalerator.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — innovactionitalia.it', 'domain', 'innovactionitalia.it', 'auto_keep', 70, true, true,
    'Innovaction — estratto conto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'innovactionitalia.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — interglobo.com', 'domain', 'interglobo.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'interglobo.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — italcamara-es.com', 'domain', 'italcamara-es.com', 'auto_keep', 70, true, true,
    'Italcamara Spain — Salon Gourmets', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'italcamara-es.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — italiantasteexport.eu', 'domain', 'italiantasteexport.eu', 'auto_keep', 70, true, true,
    'Italian Taste Export', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'italiantasteexport.eu' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — italianway.house', 'domain', 'italianway.house', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'italianway.house' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — italyfoodawards.com', 'domain', 'italyfoodawards.com', 'auto_keep', 70, true, true,
    'Italy Food Awards', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'italyfoodawards.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — itscompany.si', 'domain', 'itscompany.si', 'auto_keep', 70, true, true,
    'ITS Company — sunflower oil', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'itscompany.si' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — jgbanis.com', 'domain', 'jgbanis.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'jgbanis.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — justgourmetfoods.co.uk', 'domain', 'justgourmetfoods.co.uk', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'justgourmetfoods.co.uk' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — kehe.com', 'domain', 'kehe.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'kehe.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — koelnmesse.de', 'domain', 'koelnmesse.de', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'koelnmesse.de' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — koelnmesse.it', 'domain', 'koelnmesse.it', 'auto_keep', 70, true, true,
    'Koelnmesse — ISM, Anuga, TuttoFood', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'koelnmesse.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — kosherspain.com', 'domain', 'kosherspain.com', 'auto_keep', 70, true, true,
    'Kosher Spain — certificazione', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'kosherspain.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — linkedin.com', 'domain', 'linkedin.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'linkedin.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — lovetoitaly.com', 'domain', 'lovetoitaly.com', 'auto_keep', 70, true, true,
    'Love to Italy — SANA Food', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'lovetoitaly.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — luscioux.it', 'domain', 'luscioux.it', 'auto_keep', 70, true, true,
    'Luscioux — pistacchio supplier', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'luscioux.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — machado-import.com', 'domain', 'machado-import.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'machado-import.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — marfreight.com', 'domain', 'marfreight.com', 'auto_keep', 70, true, true,
    'Mar Freight — US shipping', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'marfreight.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — martinoparisi.com', 'domain', 'martinoparisi.com', 'auto_keep', 70, true, true,
    'Martino Parisi — VOLEM', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'martinoparisi.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — mielevangelisti.it', 'domain', 'mielevangelisti.it', 'auto_keep', 70, true, true,
    'Miele Vangelisti — supplier', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'mielevangelisti.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — mktg-effetto-b2b.com', 'domain', 'mktg-effetto-b2b.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'mktg-effetto-b2b.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — molinobongiovanni.com', 'domain', 'molinobongiovanni.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'molinobongiovanni.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — moralco.it', 'domain', 'moralco.it', 'auto_keep', 70, true, true,
    'Moralco — yogurt/ingredients', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'moralco.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — ncubeexpo.com', 'domain', 'ncubeexpo.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ncubeexpo.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — nolostand.it', 'domain', 'nolostand.it', 'auto_keep', 70, true, true,
    'Nolostand — allestimento stand', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'nolostand.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — noz.fr', 'domain', 'noz.fr', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'noz.fr' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — nuernbergmesse.de', 'domain', 'nuernbergmesse.de', 'auto_keep', 70, true, true,
    'Nürnberg Messe — Biofach', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'nuernbergmesse.de' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — nxgengourmet.com', 'domain', 'nxgengourmet.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'nxgengourmet.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — olrservices.us', 'domain', 'olrservices.us', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'olrservices.us' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — omnilogistics.com', 'domain', 'omnilogistics.com', 'auto_keep', 70, true, true,
    'Omni Logistics — US freight', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'omnilogistics.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — omnitradeservices.com', 'domain', 'omnitradeservices.com', 'auto_keep', 70, true, true,
    'Omni Trade — US air freight', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'omnitradeservices.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — orchestraweb.biz', 'domain', 'orchestraweb.biz', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'orchestraweb.biz' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — organic.nl', 'domain', 'organic.nl', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'organic.nl' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — otim.it', 'domain', 'otim.it', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'otim.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — ovgrp.com', 'domain', 'ovgrp.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ovgrp.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — packint.com', 'domain', 'packint.com', 'auto_keep', 70, true, true,
    'Packint — chocolate machines', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'packint.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — palibex.com', 'domain', 'palibex.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'palibex.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — parente.biz', 'domain', 'parente.biz', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'parente.biz' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — pautassi.com', 'domain', 'pautassi.com', 'auto_keep', 70, true, true,
    'Pautassi — frolle supplier', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'pautassi.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — perfect-mail.it', 'domain', 'perfect-mail.it', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'perfect-mail.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — pipedrive.com', 'domain', 'pipedrive.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'pipedrive.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — plukgroup.com', 'domain', 'plukgroup.com', 'auto_keep', 70, true, true,
    'Pluk Group — transport', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'plukgroup.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — pmr.it', 'domain', 'pmr.it', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'pmr.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — polipack.eu', 'domain', 'polipack.eu', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'polipack.eu' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — premieressrl.it', 'domain', 'premieressrl.it', 'auto_keep', 70, true, true,
    'Premieres — quotation', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'premieressrl.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — quatroetiquetas.com', 'domain', 'quatroetiquetas.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'quatroetiquetas.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — regione.calabria.it', 'domain', 'regione.calabria.it', 'auto_keep', 70, true, true,
    'Regione Calabria — fiere/bandi', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'regione.calabria.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — reireshop.it', 'domain', 'reireshop.it', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'reireshop.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — ringover.com', 'domain', 'ringover.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ringover.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — saromi.it', 'domain', 'saromi.it', 'auto_keep', 70, true, true,
    'Saromi — aromi supplier', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'saromi.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — scminsonorizzazione.it', 'domain', 'scminsonorizzazione.it', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'scminsonorizzazione.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — sendcloudspedizioni24.com', 'domain', 'sendcloudspedizioni24.com', 'auto_keep', 70, true, true,
    'Sendcloud — tariffe spedizione', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'sendcloudspedizioni24.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — seng.it', 'domain', 'seng.it', 'auto_keep', 70, true, true,
    'Low auto/newsletter ratio, 9 messages', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'seng.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — services-elis.com', 'domain', 'services-elis.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'services-elis.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — shopify.com', 'domain', 'shopify.com', 'auto_keep', 70, true, true,
    'Shopify — accrediti/payments', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'shopify.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — sintekassisi.it', 'domain', 'sintekassisi.it', 'auto_keep', 70, true, true,
    'Sintek Assisi — PET vasi', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'sintekassisi.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — slvmanagement.com', 'domain', 'slvmanagement.com', 'auto_keep', 70, true, true,
    'SLV Management', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'slvmanagement.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — sonarobookings.com', 'domain', 'sonarobookings.com', 'auto_keep', 70, true, true,
    'Sonaro — supporto clienti', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'sonarobookings.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — specialtyfood.com', 'domain', 'specialtyfood.com', 'auto_keep', 70, true, true,
    'Specialty Food — SFF/NYC', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'specialtyfood.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — squeezer.it', 'domain', 'squeezer.it', 'auto_keep', 70, true, true,
    'Squeezer — merce spedizione', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'squeezer.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — stiltrasporti.it', 'domain', 'stiltrasporti.it', 'auto_keep', 70, true, true,
    'Stil Trasporti — quotazioni', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'stiltrasporti.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — studioconsulenzaamato.it', 'domain', 'studioconsulenzaamato.it', 'auto_keep', 70, true, true,
    'Studio Amato — paghe/F24', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'studioconsulenzaamato.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — sudcapsule.it', 'domain', 'sudcapsule.it', 'auto_keep', 70, true, true,
    'Sud Capsule — grafiche aggiornamento', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'sudcapsule.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — talque.com', 'domain', 'talque.com', 'auto_keep', 70, true, true,
    'Talque — Biofach digital/meetings', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'talque.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — temu.com', 'domain', 'temu.com', 'auto_keep', 70, true, true,
    'Temu — seller communication', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'temu.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — thatsagrowth.com', 'domain', 'thatsagrowth.com', 'auto_keep', 70, true, true,
    'ThatsAGrowth — marketing agency', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'thatsagrowth.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — tiktok.com', 'domain', 'tiktok.com', 'auto_keep', 70, true, true,
    'TikTok Shop — seller', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'tiktok.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — tissquad.com', 'domain', 'tissquad.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'tissquad.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — traspelitalia.it', 'domain', 'traspelitalia.it', 'auto_keep', 70, true, true,
    'Traspel Italia — quotazioni', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'traspelitalia.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — trip.com', 'domain', 'trip.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'trip.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — unitedmakina.com', 'domain', 'unitedmakina.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'unitedmakina.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — universalmarketing.it', 'domain', 'universalmarketing.it', 'auto_keep', 70, true, true,
    'Universal Marketing — fiere (SIAL, SFF)', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'universalmarketing.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — wetalentia.com', 'domain', 'wetalentia.com', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'wetalentia.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — xplacecompany.biz', 'domain', 'xplacecompany.biz', 'auto_keep', 70, true, true,
    'XPlace — comunicazione', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'xplacecompany.biz' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — zohocrm.eu', 'domain', 'zohocrm.eu', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'zohocrm.eu' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — zohoworkdrive.eu', 'domain', 'zohoworkdrive.eu', 'auto_keep', 70, true, true,
    'Domain matches CRM partner', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'zohoworkdrive.eu' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — zorzi.co', 'domain', 'zorzi.co', 'auto_keep', 70, true, true,
    'Low auto/newsletter ratio, 4 messages', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'zorzi.co' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — estraspa.it', 'domain', 'estraspa.it', 'auto_keep', 60, true, true,
    'Estra — utility/fatture', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'estraspa.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — ionos.it', 'domain', 'ionos.it', 'auto_keep', 60, true, true,
    'IONOS — hosting/fatture', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ionos.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — multigrafica.net', 'domain', 'multigrafica.net', 'auto_keep', 60, true, true,
    'Multigrafica — print/eventi', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'multigrafica.net' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — zohocorp.com', 'domain', 'zohocorp.com', 'auto_keep', 60, true, true,
    'Zoho Corp — invoices', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'zohocorp.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟢 CRM_LIKELY — zohostore.eu', 'domain', 'zohostore.eu', 'auto_keep', 60, true, true,
    'Zoho/Bigin — CRM sottoscrizione', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'zohostore.eu' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — ', 'domain', '', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = '' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — account.temu.com', 'domain', 'account.temu.com', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'account.temu.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — action.nl', 'domain', 'action.nl', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'action.nl' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — agrigenus.com', 'domain', 'agrigenus.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'agrigenus.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — alimentaria-matchmaking.com', 'domain', 'alimentaria-matchmaking.com', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'alimentaria-matchmaking.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — alimentaria.com', 'domain', 'alimentaria.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'alimentaria.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — antzoulatos.gr', 'domain', 'antzoulatos.gr', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'antzoulatos.gr' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — apcinordamerica.com', 'domain', 'apcinordamerica.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'apcinordamerica.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — basecamp.com', 'domain', 'basecamp.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'basecamp.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — bcsroyal.com', 'domain', 'bcsroyal.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'bcsroyal.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — bnlpositivity.it', 'domain', 'bnlpositivity.it', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'bnlpositivity.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — caffegalliano.com', 'domain', 'caffegalliano.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'caffegalliano.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — cainoxsrl.it', 'domain', 'cainoxsrl.it', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'cainoxsrl.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — cerved.com', 'domain', 'cerved.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 2 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'cerved.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — christiansen-ctl.dk', 'domain', 'christiansen-ctl.dk', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'christiansen-ctl.dk' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — cknb.co.kr', 'domain', 'cknb.co.kr', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'cknb.co.kr' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — cotswold-fayre.co.uk', 'domain', 'cotswold-fayre.co.uk', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'cotswold-fayre.co.uk' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — csmingredients.com', 'domain', 'csmingredients.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'csmingredients.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — cuoredilanga.it', 'domain', 'cuoredilanga.it', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'cuoredilanga.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — e-shop.koelnmesse.de', 'domain', 'e-shop.koelnmesse.de', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'e-shop.koelnmesse.de' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — e-sme.net', 'domain', 'e-sme.net', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'e-sme.net' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — e.backmarket.it', 'domain', 'e.backmarket.it', 'review', 50, true, false,
    'CRM partner but 2/2 newsletter-flagged', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'e.backmarket.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — elblogdeceleste.com', 'domain', 'elblogdeceleste.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'elblogdeceleste.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — electricservice.re.it', 'domain', 'electricservice.re.it', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'electricservice.re.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — em1.cloudflare.com', 'domain', 'em1.cloudflare.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 1 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'em1.cloudflare.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — email.cz', 'domain', 'email.cz', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'email.cz' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — expotrans.net', 'domain', 'expotrans.net', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'expotrans.net' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — freshways.it', 'domain', 'freshways.it', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'freshways.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — garantiroasters.com', 'domain', 'garantiroasters.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 2 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'garantiroasters.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — gecomedia.it', 'domain', 'gecomedia.it', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gecomedia.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — gestiondecompras.com', 'domain', 'gestiondecompras.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gestiondecompras.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — gff.co.uk', 'domain', 'gff.co.uk', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gff.co.uk' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — gmail.com', 'domain', 'gmail.com', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gmail.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — google.com', 'domain', 'google.com', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'google.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — gourmand.com.br', 'domain', 'gourmand.com.br', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gourmand.com.br' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — gruppofood.com', 'domain', 'gruppofood.com', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gruppofood.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — grupposerenissima.it', 'domain', 'grupposerenissima.it', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'grupposerenissima.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — hlpklearfold.it', 'domain', 'hlpklearfold.it', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'hlpklearfold.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — hotmail.com', 'domain', 'hotmail.com', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'hotmail.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — hotmail.it', 'domain', 'hotmail.it', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'hotmail.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — icloud.com', 'domain', 'icloud.com', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'icloud.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — ilmercatodelgourmet.es', 'domain', 'ilmercatodelgourmet.es', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ilmercatodelgourmet.es' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — info.n8n.io', 'domain', 'info.n8n.io', 'review', 50, true, false,
    'CRM partner but 2/2 newsletter-flagged', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'info.n8n.io' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — italiana-bakery-srls2.odoo.com', 'domain', 'italiana-bakery-srls2.odoo.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'italiana-bakery-srls2.odoo.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — italyexport.net', 'domain', 'italyexport.net', 'review', 50, true, false,
    'Mixed signals: 2 msg, 1 newsletter, 1 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'italyexport.net' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — kaufland-marketplace.com', 'domain', 'kaufland-marketplace.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'kaufland-marketplace.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — keychain.com', 'domain', 'keychain.com', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'keychain.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — lamezialogistica.it', 'domain', 'lamezialogistica.it', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'lamezialogistica.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — libero.it', 'domain', 'libero.it', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'libero.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — mammamiacompany.com', 'domain', 'mammamiacompany.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'mammamiacompany.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — medbrands.gr', 'domain', 'medbrands.gr', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'medbrands.gr' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — money.it', 'domain', 'money.it', 'review', 50, true, false,
    'CRM partner but 3/3 newsletter-flagged', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'money.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — namirialarchive.com', 'domain', 'namirialarchive.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'namirialarchive.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — nationalcortina.com', 'domain', 'nationalcortina.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'nationalcortina.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — netstrategy.it', 'domain', 'netstrategy.it', 'review', 50, true, false,
    'Mixed signals: 3 msg, 0 newsletter, 1 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'netstrategy.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — news.rajapack.it', 'domain', 'news.rajapack.it', 'review', 50, true, false,
    'Mixed signals: 2 msg, 2 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'news.rajapack.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — nimaia.it', 'domain', 'nimaia.it', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'nimaia.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — nm.messe-ticket.de', 'domain', 'nm.messe-ticket.de', 'review', 50, true, false,
    'Mixed signals: 3 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'nm.messe-ticket.de' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — notify.cloudflare.com', 'domain', 'notify.cloudflare.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'notify.cloudflare.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — orders.temu.com', 'domain', 'orders.temu.com', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'orders.temu.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — ou.org', 'domain', 'ou.org', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ou.org' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — outlook.com', 'domain', 'outlook.com', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'outlook.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — packlink.com', 'domain', 'packlink.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'packlink.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — partful.io', 'domain', 'partful.io', 'review', 50, true, false,
    'Mixed signals: 2 msg, 2 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'partful.io' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — pastificiodutto.com', 'domain', 'pastificiodutto.com', 'review', 50, true, false,
    'Mixed signals: 3 msg, 0 newsletter, 1 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'pastificiodutto.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — pederzolli-italy.com', 'domain', 'pederzolli-italy.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'pederzolli-italy.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — planetahuerto.es', 'domain', 'planetahuerto.es', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'planetahuerto.es' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — plma.nl', 'domain', 'plma.nl', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'plma.nl' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — rmsalt.com', 'domain', 'rmsalt.com', 'review', 50, true, false,
    'CRM partner but 2/2 newsletter-flagged', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'rmsalt.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — ros.com', 'domain', 'ros.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ros.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — roundraisestartupinvestor.shop', 'domain', 'roundraisestartupinvestor.shop', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'roundraisestartupinvestor.shop' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — sapurhi.com', 'domain', 'sapurhi.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'sapurhi.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — seatram.it', 'domain', 'seatram.it', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'seatram.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — sevenfluss.com', 'domain', 'sevenfluss.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'sevenfluss.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — signanywhere.com', 'domain', 'signanywhere.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'signanywhere.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — slowfood.it', 'domain', 'slowfood.it', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'slowfood.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — support.whatsapp.com', 'domain', 'support.whatsapp.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'support.whatsapp.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — system.imsinoexpo.com', 'domain', 'system.imsinoexpo.com', 'review', 50, true, false,
    'CRM partner but 2/2 newsletter-flagged', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'system.imsinoexpo.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — tbksrl.it', 'domain', 'tbksrl.it', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'tbksrl.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — tecno-3.com', 'domain', 'tecno-3.com', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'tecno-3.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — tiscali.it', 'domain', 'tiscali.it', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'tiscali.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — truetrade.pl', 'domain', 'truetrade.pl', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'truetrade.pl' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — trustpilotmail.com', 'domain', 'trustpilotmail.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'trustpilotmail.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — ukeventexhibition.com', 'domain', 'ukeventexhibition.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ukeventexhibition.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — updates.klm-mail.com', 'domain', 'updates.klm-mail.com', 'review', 50, true, false,
    'CRM partner but 2/2 newsletter-flagged', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'updates.klm-mail.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — ups.com', 'domain', 'ups.com', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ups.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — vantaggi-coverflex.com', 'domain', 'vantaggi-coverflex.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'vantaggi-coverflex.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — viasat.com', 'domain', 'viasat.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'viasat.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — virgilio.it', 'domain', 'virgilio.it', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'virgilio.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — well360.it', 'domain', 'well360.it', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'well360.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — wellspackaging.com', 'domain', 'wellspackaging.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'wellspackaging.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — wetransfer.com', 'domain', 'wetransfer.com', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'wetransfer.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — yahoo.it', 'domain', 'yahoo.it', 'review', 50, true, false,
    'Generic email provider or ambiguous domain', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'yahoo.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — zdravo.info', 'domain', 'zdravo.info', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'zdravo.info' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — zenithoutbound.com', 'domain', 'zenithoutbound.com', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 0 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'zenithoutbound.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🟡 REVIEW — zohoaccounts.eu', 'domain', 'zohoaccounts.eu', 'review', 50, true, false,
    'Mixed signals: 2 msg, 0 newsletter, 2 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'zohoaccounts.eu' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — accounts.google.com', 'domain', 'accounts.google.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/17 newsletter, 17/17 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'accounts.google.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — aiizipchatai.com', 'domain', 'aiizipchatai.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/3 newsletter, 0/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'aiizipchatai.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — airdolomiti.it', 'domain', 'airdolomiti.it', 'auto_discard', 30, true, false,
    'Auto ratio 100% (3/3)', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'airdolomiti.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — aliceemichael.it', 'domain', 'aliceemichael.it', 'auto_discard', 30, true, false,
    'Auto-classified: 30/30 newsletter, 30/30 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'aliceemichael.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — amadeus.com', 'domain', 'amadeus.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/6 newsletter, 0/6 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'amadeus.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — amazon.com', 'domain', 'amazon.com', 'auto_discard', 30, true, false,
    'Auto-classified: 3/3 newsletter, 0/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'amazon.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — amazonaws.com', 'domain', 'amazonaws.com', 'auto_discard', 30, true, false,
    'Auto ratio 100% (37/37)', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'amazonaws.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — artecarta.it', 'domain', 'artecarta.it', 'auto_discard', 30, true, false,
    'Auto-classified: 7/7 newsletter, 7/7 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'artecarta.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — chicstudioeventsgroup.com', 'domain', 'chicstudioeventsgroup.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/6 newsletter, 0/6 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'chicstudioeventsgroup.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — costalerts.amazonaws.com', 'domain', 'costalerts.amazonaws.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/6 newsletter, 0/6 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'costalerts.amazonaws.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — coverpan.es', 'domain', 'coverpan.es', 'auto_discard', 30, true, false,
    'Auto-classified: 2/3 newsletter, 0/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'coverpan.es' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — creditsafe.it', 'domain', 'creditsafe.it', 'auto_discard', 30, true, false,
    'Auto-classified: 0/5 newsletter, 0/5 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'creditsafe.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — datacreator.it', 'domain', 'datacreator.it', 'auto_discard', 30, true, false,
    'Auto-classified: 1/3 newsletter, 0/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'datacreator.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — digitalturnover.it', 'domain', 'digitalturnover.it', 'auto_discard', 30, true, false,
    'Auto-classified: 0/6 newsletter, 0/6 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'digitalturnover.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — dispenserstudio.it', 'domain', 'dispenserstudio.it', 'auto_discard', 30, true, false,
    'Auto-classified: 3/4 newsletter, 3/4 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'dispenserstudio.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — dolcesalato.com', 'domain', 'dolcesalato.com', 'auto_discard', 30, true, false,
    'Auto-classified: 5/5 newsletter, 5/5 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'dolcesalato.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — e.coupang.com', 'domain', 'e.coupang.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/3 newsletter, 3/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'e.coupang.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — e.read.ai', 'domain', 'e.read.ai', 'auto_discard', 30, true, false,
    'Auto-classified: 33/35 newsletter, 35/35 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'e.read.ai' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — ecoviaint.com', 'domain', 'ecoviaint.com', 'auto_discard', 30, true, false,
    'Auto-classified: 4/4 newsletter, 4/4 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ecoviaint.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — em-s.dropbox.com', 'domain', 'em-s.dropbox.com', 'auto_discard', 30, true, false,
    'Auto-classified: 4/4 newsletter, 4/4 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'em-s.dropbox.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — email-marriott.com', 'domain', 'email-marriott.com', 'auto_discard', 30, true, false,
    'Auto-classified: 20/20 newsletter, 0/20 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'email-marriott.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — email.iegexpo.it', 'domain', 'email.iegexpo.it', 'auto_discard', 30, true, false,
    'Auto-classified: 5/5 newsletter, 5/5 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'email.iegexpo.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — email.pipedrive.com', 'domain', 'email.pipedrive.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/6 newsletter, 6/6 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'email.pipedrive.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — emails.facile.it', 'domain', 'emails.facile.it', 'auto_discard', 30, true, false,
    'Auto-classified: 21/21 newsletter, 0/21 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'emails.facile.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — enews-airfrance.com', 'domain', 'enews-airfrance.com', 'auto_discard', 30, true, false,
    'Auto-classified: 7/7 newsletter, 0/7 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'enews-airfrance.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — exportjbexperts.com', 'domain', 'exportjbexperts.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/6 newsletter, 0/6 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'exportjbexperts.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — express.fra1.medallia.eu', 'domain', 'express.fra1.medallia.eu', 'auto_discard', 30, true, false,
    'Auto-classified: 5/5 newsletter, 0/5 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'express.fra1.medallia.eu' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — fatturazioneelettronica.aruba.it', 'domain', 'fatturazioneelettronica.aruba.it', 'auto_discard', 30, true, false,
    'Auto-classified: 0/4 newsletter, 4/4 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'fatturazioneelettronica.aruba.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — fedex.com', 'domain', 'fedex.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/3 newsletter, 3/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'fedex.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — foodweb.it', 'domain', 'foodweb.it', 'auto_discard', 30, true, false,
    'Auto-classified: 19/19 newsletter, 0/19 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'foodweb.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — geoaidc.com', 'domain', 'geoaidc.com', 'auto_discard', 30, true, false,
    'Auto-classified: 3/3 newsletter, 0/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'geoaidc.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — gis-studio.com', 'domain', 'gis-studio.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/4 newsletter, 4/4 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gis-studio.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — github.com', 'domain', 'github.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/25 newsletter, 25/25 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'github.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — gls-italy.com', 'domain', 'gls-italy.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/4 newsletter, 4/4 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gls-italy.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — goharbouraisolutions.com', 'domain', 'goharbouraisolutions.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/4 newsletter, 0/4 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'goharbouraisolutions.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — gohighlevel.com', 'domain', 'gohighlevel.com', 'auto_discard', 30, true, false,
    'Auto-classified: 44/46 newsletter, 40/46 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'gohighlevel.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — googlemail.com', 'domain', 'googlemail.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/14 newsletter, 14/14 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'googlemail.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — groupama.it', 'domain', 'groupama.it', 'auto_discard', 30, true, false,
    'Auto-classified: 0/4 newsletter, 4/4 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'groupama.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — heropay.eu', 'domain', 'heropay.eu', 'auto_discard', 30, true, false,
    'Auto-classified: 16/16 newsletter, 0/16 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'heropay.eu' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — homemovebox.com', 'domain', 'homemovebox.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/3 newsletter, 0/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'homemovebox.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — inbank.it', 'domain', 'inbank.it', 'auto_discard', 30, true, false,
    'Auto-classified: 0/94 newsletter, 94/94 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'inbank.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — info-flyingblue.com', 'domain', 'info-flyingblue.com', 'auto_discard', 30, true, false,
    'Auto-classified: 7/7 newsletter, 0/7 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'info-flyingblue.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — info.gotogate.com', 'domain', 'info.gotogate.com', 'auto_discard', 30, true, false,
    'Auto-classified: 5/5 newsletter, 0/5 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'info.gotogate.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — info.kaufland-marketplace.com', 'domain', 'info.kaufland-marketplace.com', 'auto_discard', 30, true, false,
    'Auto-classified: 3/3 newsletter, 3/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'info.kaufland-marketplace.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — irca.eu', 'domain', 'irca.eu', 'auto_discard', 30, true, false,
    'Auto-classified: 3/3 newsletter, 3/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'irca.eu' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — ita-airways.com', 'domain', 'ita-airways.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/7 newsletter, 7/7 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'ita-airways.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — italianfairservice.com', 'domain', 'italianfairservice.com', 'auto_discard', 30, true, false,
    'Auto ratio 100% (7/7)', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'italianfairservice.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — itaspa.com', 'domain', 'itaspa.com', 'auto_discard', 30, true, false,
    'Auto-classified: 4/4 newsletter, 0/4 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'itaspa.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — itzed.it', 'domain', 'itzed.it', 'auto_discard', 30, true, false,
    'Auto-classified: 1/4 newsletter, 4/4 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'itzed.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — klm-mail.com', 'domain', 'klm-mail.com', 'auto_discard', 30, true, false,
    'Auto-classified: 6/6 newsletter, 0/6 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'klm-mail.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — lexpress-franchise.it', 'domain', 'lexpress-franchise.it', 'auto_discard', 30, true, false,
    'Auto-classified: 8/8 newsletter, 0/8 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'lexpress-franchise.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — lovable.dev', 'domain', 'lovable.dev', 'auto_discard', 30, true, false,
    'Auto-classified: 5/6 newsletter, 6/6 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'lovable.dev' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — mail.apollo.io', 'domain', 'mail.apollo.io', 'auto_discard', 30, true, false,
    'Auto-classified: 7/7 newsletter, 7/7 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'mail.apollo.io' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — mail.free-now.com', 'domain', 'mail.free-now.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/3 newsletter, 3/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'mail.free-now.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — mail.jma.or.jp', 'domain', 'mail.jma.or.jp', 'auto_discard', 30, true, false,
    'Newsletter ratio 100% (12/12)', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'mail.jma.or.jp' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — mail.zapier.com', 'domain', 'mail.zapier.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/3 newsletter, 3/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'mail.zapier.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — mailbox.gohighlevel.com', 'domain', 'mailbox.gohighlevel.com', 'auto_discard', 30, true, false,
    'Auto-classified: 7/7 newsletter, 0/7 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'mailbox.gohighlevel.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — marketingkromastudio.com', 'domain', 'marketingkromastudio.com', 'auto_discard', 30, true, false,
    'Auto-classified: 3/3 newsletter, 0/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'marketingkromastudio.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — metra-agency.it', 'domain', 'metra-agency.it', 'auto_discard', 30, true, false,
    'Auto-classified: 3/3 newsletter, 0/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'metra-agency.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — microspec.com', 'domain', 'microspec.com', 'auto_discard', 30, true, false,
    'Auto-classified: 7/9 newsletter, 9/9 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'microspec.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — mirakl.net', 'domain', 'mirakl.net', 'auto_discard', 30, true, false,
    'Auto-classified: 0/10 newsletter, 10/10 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'mirakl.net' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — mistercredit.it', 'domain', 'mistercredit.it', 'auto_discard', 30, true, false,
    'Auto-classified: 3/5 newsletter, 5/5 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'mistercredit.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — multi-consult.it', 'domain', 'multi-consult.it', 'auto_discard', 30, true, false,
    'Auto-classified: 4/6 newsletter, 4/6 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'multi-consult.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — mypos.com', 'domain', 'mypos.com', 'auto_discard', 30, true, false,
    'Auto-classified: 3/15 newsletter, 10/15 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'mypos.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — news.ita-airways-connect.com', 'domain', 'news.ita-airways-connect.com', 'auto_discard', 30, true, false,
    'Auto-classified: 6/6 newsletter, 6/6 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'news.ita-airways-connect.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — news.railway.app', 'domain', 'news.railway.app', 'auto_discard', 30, true, false,
    'Auto-classified: 0/5 newsletter, 5/5 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'news.railway.app' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — notifications.hubspot.com', 'domain', 'notifications.hubspot.com', 'auto_discard', 30, true, false,
    'Auto-classified: 8/8 newsletter, 8/8 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'notifications.hubspot.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — notifications.tiktok.com', 'domain', 'notifications.tiktok.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/3 newsletter, 3/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'notifications.tiktok.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — notify.railway.app', 'domain', 'notify.railway.app', 'auto_discard', 30, true, false,
    'Auto-classified: 0/8 newsletter, 8/8 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'notify.railway.app' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — onboarding.automatoai.it', 'domain', 'onboarding.automatoai.it', 'auto_discard', 30, true, false,
    'Auto-classified: 0/3 newsletter, 0/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'onboarding.automatoai.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — orchestraweb.com', 'domain', 'orchestraweb.com', 'auto_discard', 30, true, false,
    'Auto-classified: 5/5 newsletter, 5/5 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'orchestraweb.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — packnwood.com', 'domain', 'packnwood.com', 'auto_discard', 30, true, false,
    'Auto-classified: 9/9 newsletter, 0/9 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'packnwood.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — paypal.it', 'domain', 'paypal.it', 'auto_discard', 30, true, false,
    'Auto-classified: 0/19 newsletter, 0/19 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'paypal.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — plma.com', 'domain', 'plma.com', 'auto_discard', 30, true, false,
    'Auto-classified: 26/26 newsletter, 0/26 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'plma.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — posteitaliane.it', 'domain', 'posteitaliane.it', 'auto_discard', 30, true, false,
    'Auto-classified: 0/4 newsletter, 4/4 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'posteitaliane.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — prima.it', 'domain', 'prima.it', 'auto_discard', 30, true, false,
    'Auto-classified: 3/3 newsletter, 0/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'prima.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — primaryfundingcorp.com', 'domain', 'primaryfundingcorp.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/3 newsletter, 0/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'primaryfundingcorp.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — redcare.it', 'domain', 'redcare.it', 'auto_discard', 30, true, false,
    'Auto-classified: 4/4 newsletter, 4/4 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'redcare.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — replies.acct-mgmt.com', 'domain', 'replies.acct-mgmt.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/8 newsletter, 8/8 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'replies.acct-mgmt.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — service.biofach.de', 'domain', 'service.biofach.de', 'auto_discard', 30, true, false,
    'Auto-classified: 3/3 newsletter, 3/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'service.biofach.de' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — service.nuernbergmesse.de', 'domain', 'service.nuernbergmesse.de', 'auto_discard', 30, true, false,
    'Newsletter ratio 100% (3/3)', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'service.nuernbergmesse.de' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — shop-apotheke.com', 'domain', 'shop-apotheke.com', 'auto_discard', 30, true, false,
    'Auto-classified: 18/18 newsletter, 18/18 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'shop-apotheke.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — sibill.com', 'domain', 'sibill.com', 'auto_discard', 30, true, false,
    'Newsletter ratio 100% (3/3)', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'sibill.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — statusmatch.com', 'domain', 'statusmatch.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/16 newsletter, 16/16 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'statusmatch.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — stripe.com', 'domain', 'stripe.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/3 newsletter, 3/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'stripe.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — supabase.com', 'domain', 'supabase.com', 'auto_discard', 30, true, false,
    'Auto-classified: 6/10 newsletter, 1/10 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'supabase.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — sw-online.com', 'domain', 'sw-online.com', 'auto_discard', 30, true, false,
    'Auto-classified: 3/3 newsletter, 0/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'sw-online.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — tp2.terrapinn.com', 'domain', 'tp2.terrapinn.com', 'auto_discard', 30, true, false,
    'Auto-classified: 11/11 newsletter, 0/11 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'tp2.terrapinn.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — tryharbourproai.com', 'domain', 'tryharbourproai.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/4 newsletter, 0/4 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'tryharbourproai.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — tryzipchatzone.org', 'domain', 'tryzipchatzone.org', 'auto_discard', 30, true, false,
    'Auto-classified: 0/3 newsletter, 0/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'tryzipchatzone.org' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — unionalimentari.com', 'domain', 'unionalimentari.com', 'auto_discard', 30, true, false,
    'Auto ratio 100% (4/4)', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'unionalimentari.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — unionalimentari.it', 'domain', 'unionalimentari.it', 'auto_discard', 30, true, false,
    'Auto-classified: 0/9 newsletter, 9/9 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'unionalimentari.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — unipol.it', 'domain', 'unipol.it', 'auto_discard', 30, true, false,
    'Auto-classified: 0/3 newsletter, 0/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'unipol.it' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 MARKETING_COLD — update.backmarket.com', 'domain', 'update.backmarket.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/14 newsletter, 0/14 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'update.backmarket.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 TRANSACTIONAL — vercel.com', 'domain', 'vercel.com', 'auto_discard', 30, true, false,
    'Auto-classified: 0/15 newsletter, 14/15 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'vercel.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — waytogosrl.com', 'domain', 'waytogosrl.com', 'auto_discard', 30, true, false,
    'Auto-classified: 3/3 newsletter, 0/3 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'waytogosrl.com' AND active = true
);

INSERT INTO casafolino_mail_sender_policy
    (name, pattern_type, pattern_value, action, priority, active, auto_create_partner, notes, create_date, write_date, create_uid, write_uid)
SELECT '🔴 NEWSLETTER — woocommerce.com', 'domain', 'woocommerce.com', 'auto_discard', 30, true, false,
    'Auto-classified: 6/6 newsletter, 6/6 auto', NOW(), NOW(), 1, 1
WHERE NOT EXISTS (
    SELECT 1 FROM casafolino_mail_sender_policy WHERE pattern_value = 'woocommerce.com' AND active = true
);

COMMIT;
