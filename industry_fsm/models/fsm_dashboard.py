from odoo import models, fields, api, tools
from datetime import datetime, date, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class FsmDashboard(models.Model):
    _name = 'fsm.dashboard'
    _description = 'FSM Dashboard Statistics'
    _rec_name = 'user_name'

    user_id = fields.Many2one('res.users', string='User', required=True)
    user_name = fields.Char(string='User Name', related='user_id.name', store=True)
    total_visits = fields.Integer(string='Total Visits', compute='_compute_visit_stats')
    missed_visits = fields.Integer(string='Missed Visits', compute='_compute_visit_stats')
    today_visits = fields.Integer(string="Today's Visits", compute='_compute_visit_stats')
    completed_visits = fields.Integer(string='Completed Visits', compute='_compute_visit_stats')
    pending_visits = fields.Integer(string='Pending Visits', compute='_compute_visit_stats')
    completion_rate = fields.Float(string='Completion Rate (%)', compute='_compute_visit_stats')

    @api.depends('user_id')
    def _compute_visit_stats(self):
        """Compute visit statistics for each user"""
        for record in self:
            if not record.user_id:
                record.total_visits = 0
                record.missed_visits = 0
                record.today_visits = 0
                record.completed_visits = 0
                record.pending_visits = 0
                record.completion_rate = 0
                continue
                
            today = date.today()
            
            # Base domain for FSM tasks assigned to this user
            base_domain = [
                ('is_fsm', '=', True),
                ('display_project_id', '!=', False),
                ('user_ids', 'in', [record.user_id.id])
            ]
            
            # Total visits
            record.total_visits = self.env['project.task'].search_count(base_domain)
            
            # Missed visits (planned_date_end < today AND not completed)
            missed_domain = base_domain + [
                ('planned_date_end', '<', today),
                ('stage_id.fold', '=', False)
            ]
            record.missed_visits = self.env['project.task'].search_count(missed_domain)
            
            # Today's visits (planned_date_begin is today)
            today_domain = base_domain + [
                ('planned_date_begin', '>=', today),
                ('planned_date_begin', '<', today + timedelta(days=1))
            ]
            record.today_visits = self.env['project.task'].search_count(today_domain)
            
            # Completed visits
            completed_domain = base_domain + [('stage_id.fold', '=', True)]
            record.completed_visits = self.env['project.task'].search_count(completed_domain)
            
            # Pending visits
            pending_domain = base_domain + [('stage_id.fold', '=', False)]
            record.pending_visits = self.env['project.task'].search_count(pending_domain)
            
            # Completion rate
            if record.total_visits > 0:
                record.completion_rate = round((record.completed_visits * 100.0 / record.total_visits), 2)
            else:
                record.completion_rate = 0

    @api.model
    def create_dashboard_records(self):
        """Create dashboard records for all FSM users"""
        # Get all active users who are not portal users
        fsm_users = self.env['res.users'].search([
            ('active', '=', True),
            ('share', '=', False),  # Not portal users
        ])
        
        existing_records = self.search([])
        existing_user_ids = existing_records.mapped('user_id.id')
        
        # Create records for users who don't have dashboard records yet
        for user in fsm_users:
            if user.id not in existing_user_ids:
                self.create({'user_id': user.id})
        
        # Remove records for users who no longer exist or are inactive
        invalid_records = self.search([
            '|',
            ('user_id.active', '=', False),
            ('user_id.share', '=', True)
        ])
        invalid_records.unlink()
        
        return True

    @api.model
    def refresh_dashboard_data(self):
        """Refresh dashboard data by recreating records"""
        # Delete all existing records
        self.search([]).unlink()
        
        # Create new records for all FSM users
        return self.create_dashboard_records()

    @api.model
    def ensure_all_users_dashboard_records(self):
        """Ensure dashboard records exist for all FSM users (for manager view)"""
        # This method is called when managers access the statistics view
        # to ensure all users have dashboard records
        return self.create_dashboard_records()

    @api.model
    def get_current_user_stats(self):
        """Get statistics for the current user"""
        current_user = self.env.user
        today = date.today()
        
        # Total visits assigned to current user
        total_visits = self.env['project.task'].search_count([
            ('is_fsm', '=', True),
            ('display_project_id', '!=', False),
            ('user_ids', 'in', [current_user.id])
        ])
        
        # Missed visits
        missed_visits = self.env['project.task'].search_count([
            ('is_fsm', '=', True),
            ('display_project_id', '!=', False),
            ('planned_date_end', '<', today),
            ('stage_id.fold', '=', False),
            ('stage_id.name', 'not in', ['Terminée', 'Términée', 'Finished', 'Done', 'Completed']),
            ('user_ids', 'in', [current_user.id])
        ])
        
        # Today's visits
        today_visits = self.env['project.task'].search_count([
            ('is_fsm', '=', True),
            ('display_project_id', '!=', False),
            ('planned_date_begin', '>=', today),
            ('planned_date_begin', '<', today + timedelta(days=1)),
            ('user_ids', 'in', [current_user.id])
        ])
        
        # Completed visits
        completed_visits = self.env['project.task'].search_count([
            ('is_fsm', '=', True),
            ('display_project_id', '!=', False),
            ('stage_id.fold', '=', True),
            ('user_ids', 'in', [current_user.id])
        ])
        
        # Pending visits
        pending_visits = self.env['project.task'].search_count([
            ('is_fsm', '=', True),
            ('display_project_id', '!=', False),
            ('stage_id.fold', '=', False),
            ('user_ids', 'in', [current_user.id])
        ])
        
        # Completion rate
        completion_rate = 0
        if total_visits > 0:
            completion_rate = round((completed_visits * 100.0 / total_visits), 2)
        
        return {
            'user_name': current_user.name,
            'total_visits': total_visits,
            'missed_visits': missed_visits,
            'today_visits': today_visits,
            'completed_visits': completed_visits,
            'pending_visits': pending_visits,
            'completion_rate': completion_rate,
        }
