"""F5 migration: snooze model, feedback model, new fields, cron reactivation."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info('[mail v3 F5] Starting migration 18.0.8.4.0')

    # ── 1. Add is_snoozed column to thread ──
    cr.execute("""
        ALTER TABLE casafolino_mail_thread
        ADD COLUMN IF NOT EXISTS is_snoozed BOOLEAN DEFAULT false;
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_casafolino_mail_thread_is_snoozed
        ON casafolino_mail_thread (is_snoozed) WHERE is_snoozed = true;
    """)

    # ── 2. Add has_outbound column to thread ──
    cr.execute("""
        ALTER TABLE casafolino_mail_thread
        ADD COLUMN IF NOT EXISTS has_outbound BOOLEAN DEFAULT false;
    """)
    cr.execute("""
        UPDATE casafolino_mail_thread t SET has_outbound = true
        WHERE EXISTS (
            SELECT 1 FROM casafolino_mail_message m
            WHERE m.thread_id = t.id AND m.direction = 'outbound' AND m.is_deleted = false
        );
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_casafolino_mail_thread_has_outbound
        ON casafolino_mail_thread (has_outbound, account_id, last_message_date DESC);
    """)

    # ── 3. Add undo_until + undoable state to outbox ──
    cr.execute("""
        ALTER TABLE casafolino_mail_outbox
        ADD COLUMN IF NOT EXISTS undo_until TIMESTAMP;
    """)

    # ── 4. Add is_scheduled to draft ──
    cr.execute("""
        ALTER TABLE casafolino_mail_draft
        ADD COLUMN IF NOT EXISTS is_scheduled BOOLEAN DEFAULT false;
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_casafolino_mail_draft_scheduled
        ON casafolino_mail_draft (is_scheduled, scheduled_send_at)
        WHERE is_scheduled = true;
    """)

    # ── 5. Add user preference fields ──
    cr.execute("""
        ALTER TABLE res_users
        ADD COLUMN IF NOT EXISTS mv3_font_size VARCHAR DEFAULT 'medium';
    """)
    cr.execute("""
        ALTER TABLE res_users
        ADD COLUMN IF NOT EXISTS mv3_ai_reply_enabled BOOLEAN DEFAULT true;
    """)
    cr.execute("""
        ALTER TABLE res_users
        ADD COLUMN IF NOT EXISTS mv3_ai_temperature FLOAT DEFAULT 0.5;
    """)
    cr.execute("""
        ALTER TABLE res_users
        ADD COLUMN IF NOT EXISTS mv3_ai_model VARCHAR DEFAULT 'llama-3.3-70b-versatile';
    """)

    # ── 6. Create snooze table if ORM hasn't yet ──
    cr.execute("""
        CREATE TABLE IF NOT EXISTS casafolino_mail_snooze (
            id SERIAL PRIMARY KEY,
            thread_id INTEGER NOT NULL REFERENCES casafolino_mail_thread(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES res_users(id) ON DELETE CASCADE,
            snooze_type VARCHAR NOT NULL DEFAULT 'until_date',
            wake_at TIMESTAMP,
            deadline_days INTEGER DEFAULT 3,
            snoozed_at TIMESTAMP DEFAULT NOW(),
            active BOOLEAN DEFAULT true,
            note TEXT,
            create_uid INTEGER,
            create_date TIMESTAMP DEFAULT NOW(),
            write_uid INTEGER,
            write_date TIMESTAMP DEFAULT NOW()
        );
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_casafolino_mail_snooze_active
        ON casafolino_mail_snooze (active, wake_at) WHERE active = true;
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_casafolino_mail_snooze_thread
        ON casafolino_mail_snooze (thread_id);
    """)

    # ── 7. Create feedback table if ORM hasn't yet ──
    cr.execute("""
        CREATE TABLE IF NOT EXISTS casafolino_partner_intelligence_feedback (
            id SERIAL PRIMARY KEY,
            partner_id INTEGER NOT NULL REFERENCES res_partner(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES res_users(id) ON DELETE CASCADE,
            action_type VARCHAR NOT NULL,
            hotness_at_action INTEGER,
            nba_text_at_action VARCHAR(255),
            nba_rule_id INTEGER,
            context_json TEXT,
            date TIMESTAMP DEFAULT NOW(),
            create_uid INTEGER,
            create_date TIMESTAMP DEFAULT NOW(),
            write_uid INTEGER,
            write_date TIMESTAMP DEFAULT NOW()
        );
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_intel_feedback_partner
        ON casafolino_partner_intelligence_feedback (partner_id);
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_intel_feedback_date
        ON casafolino_partner_intelligence_feedback (date DESC);
    """)

    # ── 8. Cron 92: Smart Snooze Checker (every 15 min) ──
    cr.execute("SELECT 1 FROM ir_cron WHERE cron_name ILIKE '%Smart Snooze%' LIMIT 1")
    if not cr.fetchone():
        cr.execute("""
            INSERT INTO ir_cron (
                cron_name, model_id, code, interval_number, interval_type,
                numbercall, active, priority,
                create_uid, create_date, write_uid, write_date
            ) VALUES (
                'Mail V3: Smart Snooze Checker',
                (SELECT id FROM ir_model WHERE model = 'casafolino.mail.snooze' LIMIT 1),
                'model._cron_check_snooze()',
                15, 'minutes',
                -1, true, 10,
                1, NOW(), 1, NOW()
            );
        """)
        _logger.info('[mail v3 F5] Created cron: Smart Snooze Checker')

    # ── 9. Cron 93: Scheduled Send Dispatch (every minute) ──
    cr.execute("SELECT 1 FROM ir_cron WHERE cron_name ILIKE '%Scheduled Send%' LIMIT 1")
    if not cr.fetchone():
        cr.execute("""
            INSERT INTO ir_cron (
                cron_name, model_id, code, interval_number, interval_type,
                numbercall, active, priority,
                create_uid, create_date, write_uid, write_date
            ) VALUES (
                'Mail V3: Scheduled Send Dispatch',
                (SELECT id FROM ir_model WHERE model = 'casafolino.mail.draft' LIMIT 1),
                'model._cron_scheduled_send()',
                1, 'minutes',
                -1, true, 5,
                1, NOW(), 1, NOW()
            );
        """)
        _logger.info('[mail v3 F5] Created cron: Scheduled Send Dispatch')

    # ── 10. Reactivate crons 82/83/84 (disabled during F2 deploy) ──
    cr.execute("""
        UPDATE ir_cron SET active = true
        WHERE id IN (82, 83, 84)
          AND active = false;
    """)
    reactivated_crons = cr.rowcount
    _logger.info('[mail v3 F5] Reactivated %d legacy crons (82/83/84)', reactivated_crons)

    # ── 11. Reactivate Mail V3 record rules that were disabled ──
    cr.execute("""
        UPDATE ir_rule SET active = true
        WHERE name::text ILIKE '%%Mail V3%%' AND active = false;
    """)
    reactivated_rules = cr.rowcount
    _logger.info('[mail v3 F5] Reactivated %d Mail V3 record rules', reactivated_rules)

    # ── 12. Config params ──
    cr.execute("""
        INSERT INTO ir_config_parameter (key, value, create_uid, create_date, write_uid, write_date)
        VALUES ('casafolino.mail.v5_groq_model_default', 'llama-3.3-70b-versatile', 1, NOW(), 1, NOW())
        ON CONFLICT (key) DO NOTHING;
    """)
    cr.execute("""
        INSERT INTO ir_config_parameter (key, value, create_uid, create_date, write_uid, write_date)
        VALUES ('casafolino.mail.v5_nba_llm_fallback_enabled', 'True', 1, NOW(), 1, NOW())
        ON CONFLICT (key) DO NOTHING;
    """)

    _logger.info('[mail v3 F5] Migration 18.0.8.4.0 complete')
