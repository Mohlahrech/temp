# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta


class FsmKpiDashboard(models.Model):
    _name = 'fsm.kpi.dashboard'
    _description = 'FSM KPI Dashboard'
    _order = 'sequence, id'
    _rec_name = 'kpi_name'

    kpi_name = fields.Char(string='KPI Name', required=True)
    kpi_code = fields.Char(string='KPI Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    filter_user_id = fields.Many2one('res.users', string='Filter by User', 
                                      help='Filter KPIs by assigned user. Leave empty to show all users.')
    value = fields.Float(string='Value', compute='_compute_kpi_value', store=False)
    previous_value = fields.Float(string='Previous Period Value', compute='_compute_kpi_value', store=False)
    trend = fields.Char(string='Trend', compute='_compute_kpi_value', store=False)
    trend_percentage = fields.Float(string='Trend %', compute='_compute_kpi_value', store=False)
    icon = fields.Char(string='Icon', default='fa-bar-chart')
    color = fields.Char(string='Color', default='#667eea')
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

    def action_apply_filter(self):
        """Apply the user filter to all active KPI records and refresh the dashboard"""
        # Get the filter_user_id from the first record (since all should have the same filter)
        records = self if self else self.search([('active', '=', True)], limit=1)
        if records:
            filter_user_id = records[0].filter_user_id.id if records[0].filter_user_id else False
        else:
            filter_user_id = False
        
        # Apply filter to all active records
        self._apply_user_filter_to_all(filter_user_id)
        
        # Return action to reload the view
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    def action_clear_filter_header(self):
        """Clear the user filter from header"""
        # Clear filter from all active records
        self._apply_user_filter_to_all(False)
        
        # Return action to reload the view
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def _apply_user_filter_to_all(self, user_id):
        """Apply user filter to all active KPI records"""
        # Use super().search() to bypass the override and prevent recursion
        active_records = super(FsmKpiDashboard, self).search([('active', '=', True)])
        if user_id:
            active_records.write({'filter_user_id': user_id})
        else:
            active_records.write({'filter_user_id': False})
        # Invalidate cache to recompute values
        active_records.invalidate_cache(['value', 'previous_value', 'trend', 'trend_percentage'])
        return True

    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        """Override search to apply user filter from context when filters are used"""
        # Use a context flag to prevent recursion
        if self._context.get('_applying_user_filter'):
            # Already applying filter, bypass to prevent recursion
            return super().search(domain, offset=offset, limit=limit, order=order)
        
        # Check if we need to apply user filter from context (from filter buttons)
        apply_user_filter = self._context.get('apply_user_filter')
        if apply_user_filter is not None:
            # Set flag to prevent recursion
            self_with_flag = self.with_context(_applying_user_filter=True)
            self_with_flag._apply_user_filter_to_all(apply_user_filter)
        else:
            # Check if user is filtering by filter_user_id in domain
            # Extract filter_user_id from domain if present and apply to all records
            # Then remove the filter_user_id condition from domain so all records are shown
            filter_user_id_value = None
            new_domain = []
            for condition in domain:
                if isinstance(condition, (list, tuple)) and len(condition) >= 3:
                    field, operator, value = condition[0], condition[1], condition[2]
                    if field == 'filter_user_id' and operator == '=' and value:
                        # Store the user filter value to apply to all records
                        filter_user_id_value = value
                        # Don't add this condition to new_domain - we want all records
                        continue
                new_domain.append(condition)
            
            if filter_user_id_value is not None:
                # Set flag to prevent recursion
                self_with_flag = self.with_context(_applying_user_filter=True)
                self_with_flag._apply_user_filter_to_all(filter_user_id_value)
                # Return search with modified domain (without filter_user_id condition)
                return super().search(new_domain, offset=offset, limit=limit, order=order)
        
        return super().search(domain, offset=offset, limit=limit, order=order)

    @api.depends('kpi_code', 'filter_user_id')
    def _compute_kpi_value(self):
        """Compute KPI values based on kpi_code"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        week_start = today - timedelta(days=today.weekday())
        last_week_start = week_start - timedelta(days=7)
        month_start = today.replace(day=1)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)
        
        Task = self.env['project.task']
        base_domain = [('is_fsm', '=', True)]
        
        for record in self:
            # Get user filter from record (can be set via search filter or bulk update)
            filter_user_id = record.filter_user_id
            # Add user filter if specified
            user_domain = []
            if filter_user_id:
                user_domain = [('user_ids', 'in', [filter_user_id.id])]
            
            # Combine base domain with user filter
            task_domain = base_domain + user_domain
            value = 0.0
            previous_value = 0.0
            
            if record.kpi_code == 'tasks_today':
                # Tasks scheduled for today
                value = Task.search_count(task_domain + [
                    ('planned_date_begin', '>=', today),
                    ('planned_date_begin', '<', today + timedelta(days=1))
                ])
                previous_value = Task.search_count(task_domain + [
                    ('planned_date_begin', '>=', yesterday),
                    ('planned_date_begin', '<', yesterday + timedelta(days=1))
                ])
                
            elif record.kpi_code == 'tasks_unassigned':
                # Unassigned tasks
                value = Task.search_count(task_domain + [
                    ('user_ids', '=', False),
                    ('stage_id.fold', '=', False)
                ])
                
            elif record.kpi_code == 'tasks_completed_today':
                # Completed tasks today (using write_date)
                today_start = datetime.combine(today, datetime.min.time())
                today_end = datetime.combine(today, datetime.max.time())
                value = Task.search_count(task_domain + [
                    ('stage_id.fold', '=', True),
                    ('write_date', '>=', today_start),
                    ('write_date', '<=', today_end)
                ])
                yesterday_start = datetime.combine(yesterday, datetime.min.time())
                yesterday_end = datetime.combine(yesterday, datetime.max.time())
                previous_value = Task.search_count(task_domain + [
                    ('stage_id.fold', '=', True),
                    ('write_date', '>=', yesterday_start),
                    ('write_date', '<=', yesterday_end)
                ])
                
            elif record.kpi_code == 'tasks_completed_week':
                # Completed tasks this week
                week_start_dt = datetime.combine(week_start, datetime.min.time())
                value = Task.search_count(task_domain + [
                    ('stage_id.fold', '=', True),
                    ('write_date', '>=', week_start_dt)
                ])
                last_week_start_dt = datetime.combine(last_week_start, datetime.min.time())
                week_start_dt_prev = datetime.combine(week_start, datetime.min.time())
                previous_value = Task.search_count(task_domain + [
                    ('stage_id.fold', '=', True),
                    ('write_date', '>=', last_week_start_dt),
                    ('write_date', '<', week_start_dt_prev)
                ])
                
            elif record.kpi_code == 'tasks_overdue':
                # Overdue tasks (planned_date_end < today and not completed)
                value = Task.search_count(task_domain + [
                    ('planned_date_end', '<', today),
                    ('stage_id.fold', '=', False)
                ])
                
            elif record.kpi_code == 'tasks_pending':
                # Pending tasks (not completed)
                value = Task.search_count(task_domain + [
                    ('stage_id.fold', '=', False)
                ])
                
            elif record.kpi_code == 'tasks_total':
                # Total active tasks
                value = Task.search_count(task_domain)
                
            elif record.kpi_code == 'completion_rate':
                # Completion rate percentage
                total = Task.search_count(task_domain)
                completed = Task.search_count(task_domain + [('stage_id.fold', '=', True)])
                if total > 0:
                    value = round((completed * 100.0 / total), 2)
                else:
                    value = 0.0
                    
                # Previous period (last month)
                last_month_start_dt = datetime.combine(last_month_start, datetime.min.time())
                month_start_dt = datetime.combine(month_start, datetime.min.time())
                last_month_total = Task.search_count(task_domain + [
                    ('create_date', '>=', last_month_start_dt),
                    ('create_date', '<', month_start_dt)
                ])
                last_month_completed = Task.search_count(task_domain + [
                    ('stage_id.fold', '=', True),
                    ('write_date', '>=', last_month_start_dt),
                    ('write_date', '<', month_start_dt)
                ])
                if last_month_total > 0:
                    previous_value = round((last_month_completed * 100.0 / last_month_total), 2)
                    
            elif record.kpi_code == 'active_users':
                # Active FSM users (users with tasks assigned)
                # If filtering by user, show 1 if user has tasks, 0 otherwise
                if filter_user_id:
                    value = 1 if Task.search_count(task_domain) > 0 else 0
                else:
                    tasks_with_users = Task.search(task_domain + [('user_ids', '!=', False)])
                    user_ids = tasks_with_users.mapped('user_ids').ids
                    value = len(set(user_ids))
                
            elif record.kpi_code == 'tasks_this_week':
                # Tasks scheduled this week
                week_end = week_start + timedelta(days=7)
                value = Task.search_count(task_domain + [
                    ('planned_date_begin', '>=', week_start),
                    ('planned_date_begin', '<', week_end)
                ])
                last_week_end = last_week_start + timedelta(days=7)
                previous_value = Task.search_count(task_domain + [
                    ('planned_date_begin', '>=', last_week_start),
                    ('planned_date_begin', '<', last_week_end)
                ])
                
            elif record.kpi_code == 'tasks_this_month':
                # Tasks scheduled this month
                next_month = month_start + relativedelta(months=1)
                value = Task.search_count(task_domain + [
                    ('planned_date_begin', '>=', month_start),
                    ('planned_date_begin', '<', next_month)
                ])
                last_month_end = month_start
                previous_value = Task.search_count(task_domain + [
                    ('planned_date_begin', '>=', last_month_start),
                    ('planned_date_begin', '<', last_month_end)
                ])
            
            record.value = value
            record.previous_value = previous_value
            
            # Calculate trend
            if previous_value > 0:
                trend_pct = ((value - previous_value) / previous_value) * 100
                record.trend_percentage = round(trend_pct, 2)
                if trend_pct > 0:
                    record.trend = 'up'
                elif trend_pct < 0:
                    record.trend = 'down'
                else:
                    record.trend = 'stable'
            else:
                record.trend_percentage = 0.0
                if value > 0:
                    record.trend = 'up'
                else:
                    record.trend = 'stable'

