from odoo import http
from odoo.http import request


class TodoController(http.Controller):

    @http.route('/casafolino/todo/create', type='json', auth='user', methods=['POST'])
    def todo_create(self, name, task_id=None, initiative_id=None,
                    assigned_user_id=None, **kw):
        if not task_id and not initiative_id:
            return {'error': 'task_id or initiative_id required'}

        vals = {'name': name.strip()}

        if task_id:
            task = request.env['project.task'].browse(task_id)
            if not task.exists():
                return {'error': 'Task not found'}
            vals['task_id'] = task_id
            vals['sequence'] = max(
                [t.sequence for t in task.cf_todo_ids] or [0]) + 10
        else:
            vals['initiative_id'] = initiative_id
            # Compute next sequence for standalone todos
            existing = request.env['cf.todo'].search([
                ('initiative_id', '=', initiative_id),
                ('task_id', '=', False),
            ])
            vals['sequence'] = max(
                [t.sequence for t in existing] or [0]) + 10

        if assigned_user_id:
            vals['assigned_user_id'] = assigned_user_id

        todo = request.env['cf.todo'].create(vals)
        return self._serialize(todo)

    @http.route('/casafolino/todo/update', type='json', auth='user', methods=['POST'])
    def todo_update(self, id, **kw):
        todo = request.env['cf.todo'].browse(id)
        if not todo.exists():
            return {'error': 'Todo not found'}
        write_vals = {}
        for field in ('name', 'done', 'assigned_user_id', 'sequence'):
            if field in kw:
                write_vals[field] = kw[field]
        if write_vals:
            todo.write(write_vals)
        return self._serialize(todo)

    @http.route('/casafolino/todo/delete', type='json', auth='user', methods=['POST'])
    def todo_delete(self, id, **kw):
        todo = request.env['cf.todo'].browse(id)
        if not todo.exists():
            return {'error': 'Todo not found'}
        todo.unlink()
        return {'success': True}

    @http.route('/casafolino/todo/reorder', type='json', auth='user', methods=['POST'])
    def todo_reorder(self, task_id=None, initiative_id=None, ordered_ids=None, **kw):
        if not ordered_ids:
            return {'success': True}
        for seq, todo_id in enumerate(ordered_ids):
            request.env['cf.todo'].browse(todo_id).write(
                {'sequence': (seq + 1) * 10})
        return {'success': True}

    def _serialize(self, todo):
        return {
            'id': todo.id,
            'name': todo.name,
            'done': todo.done,
            'done_date': todo.done_date.isoformat() if todo.done_date else None,
            'assigned_user_id': todo.assigned_user_id.id if todo.assigned_user_id else None,
            'assigned_user_name': todo.assigned_user_id.name if todo.assigned_user_id else None,
            'sequence': todo.sequence,
            'task_id': todo.task_id.id if todo.task_id else None,
            'initiative_id': todo.initiative_id.id if todo.initiative_id else None,
        }
