-- apply_policies_backlog.sql
-- Retroactively apply sender policies to state='new' messages
-- Date: 2026-05-05
-- Replicates Python fnmatch logic from casafolino_mail_sender_policy model
-- Handles case where sender_domain may be empty by extracting from sender_email

BEGIN;

-- Step 0: Backfill sender_domain where empty but sender_email exists
UPDATE casafolino_mail_message
SET sender_domain = LOWER(SPLIT_PART(sender_email, '@', 2)),
    write_date = NOW()
WHERE (sender_domain IS NULL OR sender_domain = '')
  AND sender_email IS NOT NULL
  AND sender_email LIKE '%@%';

-- Step 1: Apply policies to new messages using highest-priority match
-- Uses a CTE to find the best matching policy per message
WITH best_policy AS (
    SELECT DISTINCT ON (m.id)
        m.id AS msg_id,
        p.id AS policy_id,
        p.action,
        p.priority
    FROM casafolino_mail_message m
    JOIN casafolino_mail_sender_policy p ON (
        p.active = true
        AND p.pattern_type = 'domain'
        AND (
            -- Exact domain match
            LOWER(m.sender_domain) = LOWER(p.pattern_value)
            -- Wildcard pattern match (fnmatch-style)
            OR LOWER(m.sender_domain) LIKE REPLACE(REPLACE(LOWER(p.pattern_value), '*', '%'), '?', '_')
            -- Pattern with @ matches full email
            OR (p.pattern_value LIKE '%@%' AND LOWER(m.sender_email) LIKE REPLACE(REPLACE(LOWER(p.pattern_value), '*', '%'), '?', '_'))
        )
    )
    WHERE m.state = 'new'
    ORDER BY m.id, p.priority DESC, p.id ASC
)
UPDATE casafolino_mail_message m
SET state = CASE
        WHEN bp.action = 'auto_keep' THEN 'auto_keep'
        WHEN bp.action = 'auto_discard' THEN 'auto_discard'
        WHEN bp.action = 'escalate' THEN 'review'
        WHEN bp.action = 'review' THEN 'review'
        ELSE m.state
    END,
    policy_applied_id = bp.policy_id,
    match_type = 'domain',
    write_date = NOW()
FROM best_policy bp
WHERE m.id = bp.msg_id
  AND m.state = 'new';

-- Report results
SELECT state, COUNT(*) AS count FROM casafolino_mail_message GROUP BY state ORDER BY count DESC;

COMMIT;
