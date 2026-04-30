import logging
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class LavagnaController(http.Controller):

    @http.route('/casafolino/lavagna/<int:initiative_id>/data',
                type='json', auth='user', methods=['POST'])
    def get_lavagna_data(self, initiative_id, **kwargs):
        initiative = request.env['cf.initiative'].browse(initiative_id)
        if not initiative.exists() or not initiative.lavagna_enabled:
            return {'error': 'Initiative not found or lavagna not enabled'}

        return {
            'initiative': self._get_initiative_header(initiative),
            'kpi': self._get_kpi_values(initiative),
            'kanban': self._get_kanban_data(initiative),
            'today_bar': self._get_today_bar(initiative),
            'panels': self._get_panels_data(initiative),
            'timeline': self._get_timeline_data(initiative),
        }

    def _get_initiative_header(self, init):
        return {
            'id': init.id,
            'name': init.name,
            'family_name': init.family_id.name if init.family_id else '',
            'family_code': init.family_id.code if init.family_id else '',
            'family_icon': init.family_id.icon if init.family_id else '',
            'state': init.state if 'state' in init._fields else 'draft',
            'members': self._get_members(init),
            'lavagna_panels': (init.lavagna_panels or '').split(','),
        }

    def _get_members(self, init):
        projects = request.env['project.project'].search(
            [('initiative_id', '=', init.id)])
        members_set = set()
        for proj in projects:
            for follower in proj.message_follower_ids:
                if follower.partner_id:
                    members_set.add(follower.partner_id.id)
        members = request.env['res.partner'].browse(list(members_set))
        return [{
            'id': p.id,
            'name': p.name,
            'avatar_url': f'/web/image/res.partner/{p.id}/avatar_128',
            'initials': ''.join(
                w[0].upper() for w in (p.name or '').split()[:2]),
        } for p in members]

    def _get_kpi_values(self, init):
        results = []
        projects = request.env['project.project'].search(
            [('initiative_id', '=', init.id)])
        project_ids = projects.ids

        for kpi in init.lavagna_kpi_ids:
            try:
                domain = eval(kpi.domain or '[]')
                model = kpi.target_model
                if model == 'project.task':
                    domain.append(('project_id', 'in', project_ids))
                elif model == 'crm.lead' and 'initiative_id' in request.env[model]._fields:
                    domain.append(('initiative_id', '=', init.id))
                elif model == 'stock.picking' and 'initiative_id' in request.env[model]._fields:
                    domain.append(('initiative_id', '=', init.id))
                elif model == 'mail.message':
                    task_ids = request.env['project.task'].search(
                        [('project_id', 'in', project_ids)]).ids
                    domain.append(('model', '=', 'project.task'))
                    domain.append(('res_id', 'in', task_ids))

                count = request.env[model].search_count(domain)
                results.append({
                    'id': kpi.id,
                    'name': kpi.name,
                    'value': count,
                    'icon': kpi.icon,
                    'color': kpi.color,
                    'target_model': model,
                })
            except Exception as e:
                _logger.warning("KPI %s error: %s", kpi.name, e)
                results.append({
                    'id': kpi.id,
                    'name': kpi.name,
                    'value': 0,
                    'icon': kpi.icon,
                    'color': kpi.color,
                    'error': str(e),
                })
        return results

    def _get_kanban_data(self, init):
        projects = request.env['project.project'].search(
            [('initiative_id', '=', init.id)])
        if not projects:
            return {'stages': [], 'swimlanes': [], 'tasks': []}

        project = projects[0]
        stages = [{
            'id': st.id,
            'name': st.name,
            'sequence': st.sequence,
            'fold': st.fold,
        } for st in project.type_ids.sorted('sequence')]

        swimlanes = []
        if init.lavagna_swimlane_tag_ids:
            swimlanes = [{
                'id': tag.id,
                'name': tag.name,
                'color': tag.color,
                'category': tag.category if hasattr(tag, 'category') else '',
            } for tag in init.lavagna_swimlane_tag_ids]

        tasks_domain = [('project_id', 'in', projects.ids)]
        tasks = request.env['project.task'].search(
            tasks_domain, order='write_date desc', limit=200)

        user_partner_id = request.env.user.partner_id.id
        tasks_data = []
        for t in tasks:
            cf_tags = t.cf_tag_ids
            unread_count = 0
            try:
                unread_count = request.env['mail.notification'].search_count([
                    ('res_partner_id', '=', user_partner_id),
                    ('mail_message_id.model', '=', 'project.task'),
                    ('mail_message_id.res_id', '=', t.id),
                    ('is_read', '=', False),
                ])
            except Exception:
                pass

            mail_count = request.env['mail.message'].search_count([
                ('model', '=', 'project.task'),
                ('res_id', '=', t.id),
                ('message_type', 'in', ['email', 'comment']),
            ])

            tasks_data.append({
                'id': t.id,
                'name': t.name,
                'stage_id': t.stage_id.id if t.stage_id else None,
                'stage_name': t.stage_id.name if t.stage_id else None,
                'cf_tag_ids': cf_tags.ids,
                'cf_tag_names': cf_tags.mapped('name'),
                'partner_id': t.partner_id.id if t.partner_id else None,
                'partner_name': t.partner_id.name if t.partner_id else None,
                'partner_city': t.partner_id.city if t.partner_id else None,
                'user_ids': [{
                    'id': u.id, 'name': u.name,
                    'initials': ''.join(
                        w[0].upper() for w in (u.name or '').split()[:2]),
                } for u in t.user_ids],
                'date_deadline': t.date_deadline.isoformat() if t.date_deadline else None,
                'mail_count': mail_count,
                'unread_count': unread_count,
                'last_activity': t.write_date.isoformat() if t.write_date else None,
                'priority': t.priority,
                'kanban_state': t.kanban_state if hasattr(t, 'kanban_state') else 'normal',
            })

        return {
            'stages': stages,
            'swimlanes': swimlanes,
            'swimlane_category': init.lavagna_swimlane_category or '',
            'tasks': tasks_data,
        }

    def _get_today_bar(self, init):
        items = []
        projects = request.env['project.project'].search(
            [('initiative_id', '=', init.id)])
        if not projects:
            return items

        task_ids = request.env['project.task'].search(
            [('project_id', 'in', projects.ids)]).ids

        # Urgent deadlines
        tomorrow = datetime.now() + timedelta(days=1)
        urgent_tasks = request.env['project.task'].search([
            ('project_id', 'in', projects.ids),
            ('date_deadline', '<=', tomorrow.date()),
            ('date_deadline', '>=', datetime.now().date()),
        ], limit=3)
        for t in urgent_tasks:
            items.append({
                'type': 'deadline',
                'icon': 'fa-calendar',
                'title': f'Scadenza: {t.name}',
                'subtitle': t.partner_id.name if t.partner_id else '',
                'task_id': t.id,
                'priority': 0,
            })

        # Unread mails
        three_days_ago = datetime.now() - timedelta(days=3)
        unread_notifs = request.env['mail.notification'].search([
            ('res_partner_id', '=', request.env.user.partner_id.id),
            ('mail_message_id.model', '=', 'project.task'),
            ('mail_message_id.res_id', 'in', task_ids),
            ('mail_message_id.date', '>=', three_days_ago),
            ('is_read', '=', False),
        ], limit=3)
        for notif in unread_notifs[:2]:
            msg = notif.mail_message_id
            items.append({
                'type': 'mail_unread',
                'icon': 'fa-envelope',
                'title': f'Rispondere a {msg.author_id.name}' if msg.author_id else 'Mail non letta',
                'subtitle': (msg.subject or '')[:80],
                'task_id': msg.res_id,
                'priority': 1,
            })

        return sorted(items, key=lambda x: x.get('priority', 9))[:5]

    def _get_panels_data(self, init):
        projects = request.env['project.project'].search(
            [('initiative_id', '=', init.id)])
        project_ids = projects.ids
        task_ids = request.env['project.task'].search(
            [('project_id', 'in', project_ids)]).ids

        # Mail feed
        mail_msgs = request.env['mail.message'].search([
            ('model', '=', 'project.task'),
            ('res_id', 'in', task_ids),
            ('message_type', 'in', ['email', 'comment']),
        ], limit=10, order='date desc')
        mail_feed = [{
            'id': m.id,
            'subject': m.subject or '(senza oggetto)',
            'preview': (m.body or '')[:150],
            'author_id': m.author_id.id if m.author_id else None,
            'author_name': m.author_id.name if m.author_id else 'Sistema',
            'date': m.date.isoformat() if m.date else None,
            'task_id': m.res_id,
            'message_type': m.message_type,
        } for m in mail_msgs]

        # Todos (proxy: user's tasks)
        todo_tasks = request.env['project.task'].search([
            ('project_id', 'in', project_ids),
            ('user_ids', 'in', request.env.user.id),
        ], limit=10, order='date_deadline asc, priority desc')
        todos = [{
            'id': t.id,
            'name': t.name,
            'date_deadline': t.date_deadline.isoformat() if t.date_deadline else None,
            'priority': t.priority,
            'stage_name': t.stage_id.name if t.stage_id else '',
        } for t in todo_tasks]

        # Activity stream
        activity_msgs = request.env['mail.message'].search([
            ('model', 'in', ['project.task', 'project.project']),
            ('res_id', 'in', task_ids + project_ids),
            ('message_type', '=', 'notification'),
        ], limit=15, order='date desc')
        activity = [{
            'id': m.id,
            'body_short': (m.body or '')[:120],
            'author_name': m.author_id.name if m.author_id else 'Sistema',
            'date': m.date.isoformat() if m.date else None,
            'model': m.model,
            'res_id': m.res_id,
        } for m in activity_msgs]

        # Calendar
        calendar_events = []
        if 'calendar.event' in request.env:
            try:
                upcoming = request.env['calendar.event'].search([
                    ('start', '>=', datetime.now()),
                    ('start', '<=', datetime.now() + timedelta(days=14)),
                    ('user_id', '=', request.env.user.id),
                ], limit=5, order='start asc')
                calendar_events = [{
                    'id': e.id,
                    'name': e.name,
                    'start': e.start.isoformat() if e.start else None,
                    'duration': e.duration,
                    'location': e.location or '',
                } for e in upcoming]
            except Exception:
                pass

        return {
            'mail': mail_feed,
            'todo': todos,
            'activity': activity,
            'calendar': calendar_events,
        }

    def _get_timeline_data(self, init):
        date_start = init.date_start.isoformat() if hasattr(init, 'date_start') and init.date_start else None
        date_end = init.date_end.isoformat() if hasattr(init, 'date_end') and init.date_end else None
        return {
            'date_start': date_start,
            'date_end': date_end,
            'today': datetime.now().date().isoformat(),
        }

    @http.route('/casafolino/lavagna/<int:initiative_id>/move_task',
                type='json', auth='user', methods=['POST'])
    def move_task(self, initiative_id, task_id, new_stage_id, **kwargs):
        task = request.env['project.task'].browse(task_id)
        if not task.exists():
            return {'error': 'Task not found'}
        task.write({'stage_id': new_stage_id})
        return {'ok': True, 'task_id': task.id, 'new_stage_id': new_stage_id}

    @http.route('/casafolino/lavagna/<int:initiative_id>/quick_add_task',
                type='json', auth='user', methods=['POST'])
    def quick_add_task(self, initiative_id, name, stage_id=None,
                       swimlane_tag_id=None, **kwargs):
        projects = request.env['project.project'].search(
            [('initiative_id', '=', initiative_id)], limit=1)
        if not projects:
            return {'error': 'No project linked to initiative'}

        vals = {'name': name, 'project_id': projects[0].id}
        if stage_id:
            vals['stage_id'] = stage_id
        if swimlane_tag_id:
            vals['cf_tag_ids'] = [(4, swimlane_tag_id)]

        task = request.env['project.task'].create(vals)
        return {'ok': True, 'task_id': task.id, 'task_name': task.name}
