import logging
import markupsafe

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

DEFAULT_RECIPIENTS = (
    'antonio@casafolino.com,'
    'josefina.lazzaro@casafolino.com,'
    'martina.sinopoli@casafolino.com'
)


class CasafolinoFiera(models.Model):
    _inherit = 'casafolino.fiera'

    report_recipients = fields.Char(
        string='Destinatari report',
        default=DEFAULT_RECIPIENTS,
        help='Email separate da virgola — destinatari del report fine fiera',
    )
    last_report_sent = fields.Datetime(string='Ultimo report inviato')

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_close_fair(self):
        """🏁 Fine Fiera: send report + close."""
        for fiera in self:
            fiera._send_fair_report()
            fiera.status = 'closed'
            fiera.last_report_sent = fields.Datetime.now()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('🏁 Report Fiera Inviato'),
                'message': _('Report generato e inviato ai destinatari configurati.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_send_report_only(self):
        """📧 Send report without closing."""
        for fiera in self:
            fiera._send_fair_report()
            fiera.last_report_sent = fields.Datetime.now()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('📧 Report Inviato'),
                'message': _('Report generato e inviato.'),
                'type': 'success',
                'sticky': False,
            },
        }

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def _send_fair_report(self):
        self.ensure_one()
        data = self._gather_report_data()
        body_html = self._render_report_html(data)

        recipients = [
            r.strip()
            for r in (self.report_recipients or DEFAULT_RECIPIENTS).split(',')
            if r.strip()
        ]

        mail = self.env['mail.mail'].sudo().create({
            'subject': '🏁 Report Fiera — %s' % self.name,
            'body_html': body_html,
            'email_from': '"CasaFolino" <antonio@casafolino.com>',
            'email_to': ','.join(recipients),
            'auto_delete': False,
        })
        mail.send()

        self.message_post(
            body='Report fiera inviato a: %s' % ', '.join(recipients),
            message_type='comment',
        )

    def _gather_report_data(self):
        """Gather all metrics via optimised SQL."""
        self.ensure_one()
        cr = self.env.cr

        tag_id = self.tag_id.id if self.tag_id else False
        cat_id = self.category_id.id if self.category_id else False

        data = {
            'volume': {'scanned': 0, 'leads': 0, 'mails_sent': 0, 'operators': 0},
            'engagement': {'opened': 0, 'clicked': 0, 'replied': 0, 'bounced': 0},
            'top_countries': [],
            'operators': [],
            'hot_leads': [],
            'pipeline': [],
            'action_items': {
                'hot_no_activity': 0,
                'open_activities': 0,
                'bounced_emails': [],
                'no_open_48h': 0,
            },
            'all_contacts': [],
        }

        if not tag_id and not cat_id:
            return data

        # --- Volume: partners (scanned business cards) ---
        if cat_id:
            cr.execute("""
                SELECT COUNT(DISTINCT partner_id)
                FROM res_partner_res_partner_category_rel
                WHERE category_id = %s
            """, (cat_id,))
            data['volume']['scanned'] = cr.fetchone()[0] or 0

        # --- Volume: leads ---
        if tag_id:
            cr.execute("""
                SELECT COUNT(*)
                FROM crm_tag_rel
                WHERE tag_id = %s
            """, (tag_id,))
            data['volume']['leads'] = cr.fetchone()[0] or 0

        # --- Volume: mails sent (from mailings matching fiera name) ---
        fair_name = self.name
        cr.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE mt.trace_status = 'open') AS opened,
                COUNT(*) FILTER (WHERE mt.links_click_datetime IS NOT NULL) AS clicked,
                COUNT(*) FILTER (WHERE mt.trace_status = 'reply') AS replied,
                COUNT(*) FILTER (WHERE mt.trace_status = 'bounce') AS bounced
            FROM mailing_trace mt
            JOIN mailing_mailing mm ON mm.id = mt.mass_mailing_id
            WHERE mm.subject ILIKE %s
        """, ('%' + fair_name + '%',))
        row = cr.fetchone()
        if row:
            data['volume']['mails_sent'] = row[0] or 0
            data['engagement'] = {
                'opened': row[1] or 0,
                'clicked': row[2] or 0,
                'replied': row[3] or 0,
                'bounced': row[4] or 0,
            }

        # --- Volume: operators (who created the partners) ---
        if cat_id:
            cr.execute("""
                SELECT COUNT(DISTINCT p.create_uid)
                FROM res_partner p
                JOIN res_partner_res_partner_category_rel rel ON rel.partner_id = p.id
                WHERE rel.category_id = %s
            """, (cat_id,))
            data['volume']['operators'] = cr.fetchone()[0] or 0

        # --- Top 5 countries ---
        if cat_id:
            cr.execute("""
                SELECT COALESCE(c.name->>'en_US', 'N/D') AS country, COUNT(*) AS cnt
                FROM res_partner p
                JOIN res_partner_res_partner_category_rel rel ON rel.partner_id = p.id
                LEFT JOIN res_country c ON c.id = p.country_id
                WHERE rel.category_id = %s
                GROUP BY c.name
                ORDER BY cnt DESC
                LIMIT 5
            """, (cat_id,))
            data['top_countries'] = [
                {'name': r[0], 'count': r[1]} for r in cr.fetchall()
            ]

        # --- Operators breakdown ---
        if cat_id:
            cr.execute("""
                SELECT
                    COALESCE(rp2.name, u.login) AS operator_name,
                    COUNT(*) AS total_scanned,
                    COUNT(*) FILTER (
                        WHERE eng.engagement_status IN ('hot', 'replied')
                    ) AS hot_count
                FROM res_partner p
                JOIN res_partner_res_partner_category_rel rel ON rel.partner_id = p.id
                JOIN res_users u ON u.id = p.create_uid
                LEFT JOIN res_partner rp2 ON rp2.id = u.partner_id
                LEFT JOIN casafolino_mail_engagement eng
                    ON eng.res_model = 'res.partner' AND eng.res_id = p.id
                WHERE rel.category_id = %s
                GROUP BY operator_name, u.login
                ORDER BY total_scanned DESC
            """, (cat_id,))
            data['operators'] = [
                {'name': r[0], 'scanned': r[1], 'hot': r[2]}
                for r in cr.fetchall()
            ]

        # --- Top 5 Hot leads ---
        if tag_id:
            cr.execute("""
                SELECT
                    l.id,
                    COALESCE(l.partner_name, l.name) AS partner_name,
                    l.partner_name AS company,
                    COALESCE(c.name->>'en_US', '') AS country,
                    COALESCE(eng.opened_count, 0) AS opens,
                    eng.last_open_date
                FROM crm_lead l
                JOIN crm_tag_rel ctr ON ctr.lead_id = l.id AND ctr.tag_id = %s
                LEFT JOIN res_partner rp ON rp.id = l.partner_id
                LEFT JOIN res_country c ON c.id = COALESCE(rp.country_id, l.country_id)
                LEFT JOIN casafolino_mail_engagement eng
                    ON eng.res_model = 'res.partner' AND eng.res_id = l.partner_id
                WHERE eng.engagement_status IN ('hot', 'replied')
                ORDER BY eng.opened_count DESC NULLS LAST
                LIMIT 5
            """, (tag_id,))
            data['hot_leads'] = [
                {
                    'id': r[0],
                    'name': r[1],
                    'company': r[2] or '',
                    'country': r[3],
                    'opens': r[4],
                    'last_open': r[5].strftime('%d/%m/%Y %H:%M') if r[5] else '',
                }
                for r in cr.fetchall()
            ]

        # --- Pipeline stage breakdown ---
        if tag_id:
            cr.execute("""
                SELECT
                    COALESCE(s.name->>'en_US', s.name->>'it_IT', 'N/D') AS stage_name,
                    COUNT(*) AS cnt
                FROM crm_lead l
                JOIN crm_tag_rel ctr ON ctr.lead_id = l.id AND ctr.tag_id = %s
                LEFT JOIN crm_stage s ON s.id = l.stage_id
                GROUP BY stage_name, s.sequence
                ORDER BY s.sequence
            """, (tag_id,))
            data['pipeline'] = [
                {'stage': r[0], 'count': r[1]} for r in cr.fetchall()
            ]

        # --- Action items ---
        if tag_id:
            # Hot/replied leads without follow-up activity
            cr.execute("""
                SELECT COUNT(*)
                FROM crm_lead l
                JOIN crm_tag_rel ctr ON ctr.lead_id = l.id AND ctr.tag_id = %s
                LEFT JOIN casafolino_mail_engagement eng
                    ON eng.res_model = 'res.partner' AND eng.res_id = l.partner_id
                WHERE eng.engagement_status IN ('hot', 'replied')
                  AND NOT EXISTS (
                    SELECT 1 FROM mail_activity ma
                    WHERE ma.res_model = 'crm.lead' AND ma.res_id = l.id
                  )
            """, (tag_id,))
            data['action_items']['hot_no_activity'] = cr.fetchone()[0] or 0

            # Open activities count
            cr.execute("""
                SELECT COUNT(*)
                FROM mail_activity ma
                JOIN crm_lead l ON ma.res_model = 'crm.lead' AND ma.res_id = l.id
                JOIN crm_tag_rel ctr ON ctr.lead_id = l.id AND ctr.tag_id = %s
            """, (tag_id,))
            data['action_items']['open_activities'] = cr.fetchone()[0] or 0

        # Bounced emails
        if cat_id:
            cr.execute("""
                SELECT p.email
                FROM res_partner p
                JOIN res_partner_res_partner_category_rel rel ON rel.partner_id = p.id
                JOIN casafolino_mail_engagement eng
                    ON eng.res_model = 'res.partner' AND eng.res_id = p.id
                WHERE rel.category_id = %s
                  AND eng.engagement_status = 'bounced'
                  AND p.email IS NOT NULL
                LIMIT 20
            """, (cat_id,))
            data['action_items']['bounced_emails'] = [r[0] for r in cr.fetchall()]

        # No open after 48h
        if cat_id:
            cr.execute("""
                SELECT COUNT(*)
                FROM res_partner p
                JOIN res_partner_res_partner_category_rel rel ON rel.partner_id = p.id
                LEFT JOIN casafolino_mail_engagement eng
                    ON eng.res_model = 'res.partner' AND eng.res_id = p.id
                WHERE rel.category_id = %s
                  AND eng.engagement_status = 'cold'
                  AND eng.total_sent > 0
                  AND eng.last_update < NOW() - INTERVAL '48 hours'
            """, (cat_id,))
            data['action_items']['no_open_48h'] = cr.fetchone()[0] or 0

        # --- All contacts (max 100) ---
        if cat_id and tag_id:
            cr.execute("""
                SELECT
                    p.id,
                    p.name,
                    p.company_name,
                    COALESCE(c.name->>'en_US', '') AS country,
                    p.email,
                    COALESCE(eng.engagement_status, 'cold') AS status,
                    l.id AS lead_id
                FROM res_partner p
                JOIN res_partner_res_partner_category_rel rel ON rel.partner_id = p.id
                LEFT JOIN res_country c ON c.id = p.country_id
                LEFT JOIN casafolino_mail_engagement eng
                    ON eng.res_model = 'res.partner' AND eng.res_id = p.id
                LEFT JOIN crm_lead l
                    ON l.partner_id = p.id
                    AND EXISTS (
                        SELECT 1 FROM crm_tag_rel ctr
                        WHERE ctr.lead_id = l.id AND ctr.tag_id = %s
                    )
                WHERE rel.category_id = %s
                ORDER BY
                    CASE eng.engagement_status
                        WHEN 'replied' THEN 1
                        WHEN 'hot' THEN 2
                        WHEN 'warm' THEN 3
                        WHEN 'cold' THEN 4
                        WHEN 'bounced' THEN 5
                        ELSE 6
                    END,
                    p.name
                LIMIT 100
            """, (tag_id, cat_id))
            total_partners = data['volume']['scanned']
            rows = cr.fetchall()
            data['all_contacts'] = [
                {
                    'name': r[1] or '',
                    'company': r[2] or '',
                    'country': r[3],
                    'email': r[4] or '',
                    'status': r[5],
                    'lead_id': r[6],
                }
                for r in rows
            ]
            data['all_contacts_total'] = total_partners
            data['all_contacts_shown'] = len(rows)

        return data

    # ------------------------------------------------------------------
    # HTML rendering
    # ------------------------------------------------------------------

    def _render_report_html(self, data):
        """Build complete HTML email report."""
        self.ensure_one()
        vol = data['volume']
        eng = data['engagement']
        total_sent = vol.get('mails_sent', 0) or 1  # avoid div/0

        now_str = fields.Datetime.now().strftime('%d/%m/%Y %H:%M')
        tag_id = self.tag_id.id if self.tag_id else 0

        # --- SVG Donut chart ---
        def donut_svg(values, colors, labels, size=160):
            total = sum(values) or 1
            parts = []
            offset = 0
            for val, color, label in zip(values, colors, labels):
                pct = val / total
                dash = pct * 100
                gap = 100 - dash
                parts.append(
                    '<circle cx="50" cy="50" r="40" fill="none" '
                    'stroke="%s" stroke-width="18" '
                    'stroke-dasharray="%.1f %.1f" '
                    'stroke-dashoffset="%.1f" '
                    'style="transition: stroke-dashoffset 0.3s;"/>'
                    % (color, dash, gap, -offset)
                )
                offset += dash
            svg = (
                '<svg viewBox="0 0 100 100" width="%d" height="%d" '
                'style="transform:rotate(-90deg);">'
                '%s</svg>'
            ) % (size, size, ''.join(parts))
            return svg

        eng_values = [eng['opened'], eng['clicked'], eng['replied'], eng['bounced']]
        eng_colors = ['#C8A43A', '#5A6E3A', '#2E7D32', '#C62828']
        eng_labels = ['Aperte', 'Click', 'Reply', 'Bounce']
        donut = donut_svg(eng_values, eng_colors, eng_labels)

        # --- SVG Bar chart for countries ---
        def bar_chart_svg(items, width=500, bar_height=28):
            if not items:
                return '<p style="color:#999;font-size:13px;">Nessun dato geografico</p>'
            max_val = max(i['count'] for i in items) or 1
            bars = []
            for idx, item in enumerate(items):
                y = idx * (bar_height + 8)
                bar_w = max(int((item['count'] / max_val) * 320), 4)
                bars.append(
                    '<g transform="translate(0,%d)">'
                    '<text x="0" y="%d" font-size="13" fill="#333">%s</text>'
                    '<rect x="120" y="0" width="%d" height="%d" rx="3" fill="#C8A43A"/>'
                    '<text x="%d" y="%d" font-size="12" fill="#6B4A1E" font-weight="bold">%d</text>'
                    '</g>'
                    % (y, bar_height - 8, item['name'], bar_w, bar_height, 120 + bar_w + 6, bar_height - 8, item['count'])
                )
            svg_height = len(items) * (bar_height + 8)
            return (
                '<svg width="%d" height="%d" style="font-family:Arial,sans-serif;">'
                '%s</svg>'
            ) % (width, svg_height, ''.join(bars))

        country_chart = bar_chart_svg(data['top_countries'])

        # --- Pipeline bar chart ---
        pipeline_chart = bar_chart_svg(
            [{'name': p['stage'], 'count': p['count']} for p in data['pipeline']]
        )

        # --- Engagement legend ---
        def eng_legend():
            items = [
                ('📬 Aperte', eng['opened'], '#C8A43A'),
                ('🖱️ Click', eng['clicked'], '#5A6E3A'),
                ('💬 Reply', eng['replied'], '#2E7D32'),
                ('❌ Bounce', eng['bounced'], '#C62828'),
            ]
            cells = []
            for label, count, color in items:
                pct = round(count / total_sent * 100, 1) if total_sent else 0
                cells.append(
                    '<td style="padding:4px 12px;text-align:center;">'
                    '<span style="display:inline-block;width:12px;height:12px;'
                    'background:%s;border-radius:2px;margin-right:4px;vertical-align:middle;"></span>'
                    '<strong>%d</strong> (%s%%)<br/>'
                    '<span style="font-size:11px;color:#666;">%s</span></td>'
                    % (color, count, pct, label)
                )
            return '<table cellpadding="0" cellspacing="0" border="0"><tr>%s</tr></table>' % ''.join(cells)

        # --- Hot leads table ---
        def hot_leads_table():
            if not data['hot_leads']:
                return '<p style="color:#999;font-size:13px;">Nessun lead hot/replied</p>'
            rows = []
            for hl in data['hot_leads']:
                rows.append(
                    '<tr>'
                    '<td style="padding:8px 10px;border-bottom:1px solid #eee;">%s</td>'
                    '<td style="padding:8px 10px;border-bottom:1px solid #eee;">%s</td>'
                    '<td style="padding:8px 10px;border-bottom:1px solid #eee;">%s</td>'
                    '<td style="padding:8px 10px;border-bottom:1px solid #eee;text-align:center;">%d</td>'
                    '<td style="padding:8px 10px;border-bottom:1px solid #eee;">%s</td>'
                    '<td style="padding:8px 10px;border-bottom:1px solid #eee;">'
                    '<a href="https://erp.casafolino.com/odoo/crm/%d" '
                    'style="color:#6B4A1E;text-decoration:underline;">Apri →</a></td>'
                    '</tr>'
                    % (hl['name'], hl['company'], hl['country'], hl['opens'], hl['last_open'], hl['id'])
                )
            return (
                '<table cellpadding="0" cellspacing="0" border="0" width="100%%" '
                'style="font-size:13px;">'
                '<tr style="background:#F5E6C8;">'
                '<th style="padding:8px 10px;text-align:left;">Nome</th>'
                '<th style="padding:8px 10px;text-align:left;">Azienda</th>'
                '<th style="padding:8px 10px;text-align:left;">Paese</th>'
                '<th style="padding:8px 10px;text-align:center;">Aperture</th>'
                '<th style="padding:8px 10px;text-align:left;">Ultima apertura</th>'
                '<th style="padding:8px 10px;text-align:left;">Link</th>'
                '</tr>'
                '%s</table>'
            ) % ''.join(rows)

        # --- Operators table ---
        def operators_table():
            if not data['operators']:
                return '<p style="color:#999;font-size:13px;">Nessun operatore</p>'
            rows = []
            for op in data['operators']:
                rows.append(
                    '<tr>'
                    '<td style="padding:6px 10px;border-bottom:1px solid #eee;">%s</td>'
                    '<td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;">%d</td>'
                    '<td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;">%d</td>'
                    '</tr>'
                    % (op['name'], op['scanned'], op['hot'])
                )
            return (
                '<table cellpadding="0" cellspacing="0" border="0" width="100%%" '
                'style="font-size:13px;">'
                '<tr style="background:#F5E6C8;">'
                '<th style="padding:6px 10px;text-align:left;">Operatore</th>'
                '<th style="padding:6px 10px;text-align:center;">Biglietti</th>'
                '<th style="padding:6px 10px;text-align:center;">Lead caldi</th>'
                '</tr>'
                '%s</table>'
            ) % ''.join(rows)

        # --- All contacts table ---
        def contacts_table():
            contacts = data.get('all_contacts', [])
            if not contacts:
                return ''
            total = data.get('all_contacts_total', 0)
            shown = data.get('all_contacts_shown', 0)
            status_colors = {
                'replied': '#2E7D32', 'hot': '#E65100',
                'warm': '#C8A43A', 'cold': '#9E9E9E', 'bounced': '#C62828',
            }
            rows = []
            for idx, ct in enumerate(contacts):
                bg = '#fff' if idx % 2 == 0 else '#fafafa'
                sc = status_colors.get(ct['status'], '#999')
                link = ''
                if ct.get('lead_id'):
                    link = (
                        '<a href="https://erp.casafolino.com/odoo/crm/%d" '
                        'style="color:#6B4A1E;">→</a>'
                    ) % ct['lead_id']
                rows.append(
                    '<tr style="background:%s;">'
                    '<td style="padding:5px 8px;border-bottom:1px solid #eee;font-size:12px;">%s</td>'
                    '<td style="padding:5px 8px;border-bottom:1px solid #eee;font-size:12px;">%s</td>'
                    '<td style="padding:5px 8px;border-bottom:1px solid #eee;font-size:12px;">%s</td>'
                    '<td style="padding:5px 8px;border-bottom:1px solid #eee;font-size:12px;">%s</td>'
                    '<td style="padding:5px 8px;border-bottom:1px solid #eee;font-size:12px;">'
                    '<span style="color:%s;font-weight:bold;">%s</span></td>'
                    '<td style="padding:5px 8px;border-bottom:1px solid #eee;font-size:12px;">%s</td>'
                    '</tr>'
                    % (bg, ct['name'], ct['company'], ct['country'], ct['email'], sc, ct['status'].upper(), link)
                )
            overflow = ''
            if total > shown:
                overflow = (
                    '<p style="font-size:12px;color:#666;margin-top:8px;">'
                    'Mostrati %d di %d — '
                    '<a href="https://erp.casafolino.com/odoo/crm?search_default_tag=%d" '
                    'style="color:#6B4A1E;">vedi pipeline completa</a></p>'
                ) % (shown, total, tag_id)
            return (
                '<h2 style="color:#6B4A1E;margin:24px 0 12px 0;font-size:16px;">'
                '👥 Lista Contatti</h2>'
                '<table cellpadding="0" cellspacing="0" border="0" width="100%%" '
                'style="font-size:12px;">'
                '<tr style="background:#F5E6C8;">'
                '<th style="padding:6px 8px;text-align:left;">Nome</th>'
                '<th style="padding:6px 8px;text-align:left;">Azienda</th>'
                '<th style="padding:6px 8px;text-align:left;">Paese</th>'
                '<th style="padding:6px 8px;text-align:left;">Email</th>'
                '<th style="padding:6px 8px;text-align:left;">Status</th>'
                '<th style="padding:6px 8px;text-align:left;">Link</th>'
                '</tr>'
                '%s</table>%s'
            ) % (''.join(rows), overflow)

        # --- Action items ---
        ai = data['action_items']
        bounced_list = ', '.join(ai['bounced_emails'][:10]) if ai['bounced_emails'] else 'nessuno'

        # --- Assemble full HTML ---
        html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<style>
@media only screen and (max-width: 600px) {{
    .report-table {{ width: 100%% !important; }}
    .card-row td {{ display: block !important; width: 100%% !important; margin-bottom: 8px; }}
    .section-pad {{ padding: 20px 16px !important; }}
}}
</style>
</head>
<body style="margin:0;padding:0;background:#f7f5f1;font-family:Arial,Helvetica,sans-serif;">
<table cellpadding="0" cellspacing="0" border="0" width="100%%" style="background:#f7f5f1;">
<tr><td align="center" style="padding:20px 10px;">

<table cellpadding="0" cellspacing="0" border="0" width="720" class="report-table"
       style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

<!-- Header -->
<tr><td style="padding:28px 40px;background:#6B4A1E;color:#fff;" class="section-pad">
    <h1 style="margin:0;font-size:22px;font-weight:bold;">🏁 Report Fiera — {fair_name}</h1>
    <p style="margin:8px 0 0 0;color:#F5E6C8;font-size:13px;">
        {date_range} · Generato il {now}
    </p>
</td></tr>

<!-- Volume Cards -->
<tr><td style="padding:28px 40px;" class="section-pad">
    <h2 style="color:#6B4A1E;margin:0 0 16px 0;font-size:17px;">📊 Volume</h2>
    <table cellpadding="0" cellspacing="8" border="0" width="100%%">
    <tr class="card-row">
        <td bgcolor="#FFF8E1" align="center" width="25%%" style="padding:18px 8px;border-radius:8px;">
            <div style="font-size:32px;font-weight:bold;color:#6B4A1E;">{scanned}</div>
            <div style="font-size:11px;color:#888;margin-top:4px;">📷 Biglietti</div>
        </td>
        <td bgcolor="#FFF8E1" align="center" width="25%%" style="padding:18px 8px;border-radius:8px;">
            <div style="font-size:32px;font-weight:bold;color:#6B4A1E;">{leads}</div>
            <div style="font-size:11px;color:#888;margin-top:4px;">📋 Lead</div>
        </td>
        <td bgcolor="#FFF8E1" align="center" width="25%%" style="padding:18px 8px;border-radius:8px;">
            <div style="font-size:32px;font-weight:bold;color:#6B4A1E;">{mails_sent}</div>
            <div style="font-size:11px;color:#888;margin-top:4px;">✉️ Mail inviate</div>
        </td>
        <td bgcolor="#FFF8E1" align="center" width="25%%" style="padding:18px 8px;border-radius:8px;">
            <div style="font-size:32px;font-weight:bold;color:#6B4A1E;">{operators}</div>
            <div style="font-size:11px;color:#888;margin-top:4px;">👥 Operatori</div>
        </td>
    </tr>
    </table>
</td></tr>

<!-- Engagement -->
<tr><td style="padding:0 40px 28px 40px;" class="section-pad">
    <h2 style="color:#6B4A1E;margin:0 0 16px 0;font-size:17px;">📬 Engagement Email</h2>
    <table cellpadding="0" cellspacing="0" border="0" width="100%%">
    <tr>
        <td width="180" align="center" style="vertical-align:top;">{donut}</td>
        <td style="vertical-align:top;padding-left:20px;">{eng_legend}</td>
    </tr>
    </table>
</td></tr>

<!-- Top Countries -->
<tr><td style="padding:0 40px 28px 40px;" class="section-pad">
    <h2 style="color:#6B4A1E;margin:0 0 12px 0;font-size:16px;">🌍 Top Paesi</h2>
    {country_chart}
</td></tr>

<!-- Operators -->
<tr><td style="padding:0 40px 28px 40px;" class="section-pad">
    <h2 style="color:#6B4A1E;margin:0 0 12px 0;font-size:16px;">🧑‍💼 Operatori</h2>
    {operators_table}
</td></tr>

<!-- Hot Leads -->
<tr><td style="padding:0 40px 28px 40px;" class="section-pad">
    <h2 style="color:#6B4A1E;margin:0 0 12px 0;font-size:16px;">🔥 Top 5 Lead Hot</h2>
    {hot_leads_table}
</td></tr>

<!-- Pipeline -->
<tr><td style="padding:0 40px 28px 40px;" class="section-pad">
    <h2 style="color:#6B4A1E;margin:0 0 12px 0;font-size:16px;">📊 Pipeline Stages</h2>
    {pipeline_chart}
</td></tr>

<!-- Action Items -->
<tr><td style="padding:0 40px 28px 40px;" class="section-pad">
    <h2 style="color:#6B4A1E;margin:0 0 12px 0;font-size:16px;">⚡ Action Items</h2>
    <table cellpadding="0" cellspacing="0" border="0" width="100%%" style="font-size:13px;">
        <tr><td style="padding:8px 0;">🔥 <strong>{hot_no_activity}</strong> lead caldi senza attività follow-up</td></tr>
        <tr><td style="padding:8px 0;">📞 <strong>{open_activities}</strong> attività aperte sui lead fiera</td></tr>
        <tr><td style="padding:8px 0;">❌ <strong>{bounced_count}</strong> email bounced — {bounced_list}</td></tr>
        <tr><td style="padding:8px 0;">🟡 <strong>{no_open_48h}</strong> contatti senza apertura dopo 48h</td></tr>
    </table>
</td></tr>

<!-- All Contacts -->
<tr><td style="padding:0 40px 28px 40px;" class="section-pad">
    {contacts_table}
</td></tr>

<!-- Footer -->
<tr><td style="padding:24px 40px;background:#f7f5f1;border-top:1px solid #e5e0d5;" class="section-pad">
    <table cellpadding="0" cellspacing="0" border="0">
    <tr>
        <td style="padding-right:10px;">
            <a href="https://erp.casafolino.com/odoo/crm?search_default_tag={tag_id}"
               style="display:inline-block;padding:12px 20px;background:#6B4A1E;color:#fff;
                      text-decoration:none;border-radius:4px;font-size:13px;font-weight:bold;">
                Apri pipeline completa →
            </a>
        </td>
        <td>
            <a href="https://erp.casafolino.com/odoo/email-marketing"
               style="display:inline-block;padding:12px 20px;background:#C8A43A;color:#fff;
                      text-decoration:none;border-radius:4px;font-size:13px;font-weight:bold;">
                Email Marketing →
            </a>
        </td>
    </tr>
    </table>
    <p style="font-size:11px;color:#999;margin:16px 0 0 0;">
        Casa Folino 1962 · Report generato automaticamente
    </p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>
""".format(
            fair_name=self.name,
            date_range='%s — %s' % (
                self.date_start.strftime('%d/%m/%Y') if self.date_start else '?',
                self.date_end.strftime('%d/%m/%Y') if self.date_end else '?',
            ),
            now=now_str,
            scanned=vol['scanned'],
            leads=vol['leads'],
            mails_sent=vol['mails_sent'],
            operators=vol['operators'],
            donut=donut,
            eng_legend=eng_legend(),
            country_chart=country_chart,
            operators_table=operators_table(),
            hot_leads_table=hot_leads_table(),
            pipeline_chart=pipeline_chart,
            hot_no_activity=ai['hot_no_activity'],
            open_activities=ai['open_activities'],
            bounced_count=len(ai['bounced_emails']),
            bounced_list=bounced_list,
            no_open_48h=ai['no_open_48h'],
            contacts_table=contacts_table(),
            tag_id=tag_id,
        )

        return markupsafe.Markup(html)
