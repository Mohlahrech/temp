from odoo import models, fields, api


class FsmDashboardWizard(models.TransientModel):
    _name = 'fsm.dashboard.wizard'
    _description = 'FSM Dashboard User Selection Wizard'

    user_ids = fields.Many2many(
        'res.users', 
        string='Select Users',
        domain=[('active', '=', True), ('share', '=', False)],
        help='Select users whose dashboards you want to view'
    )
    
    include_current_user = fields.Boolean(
        string='Include My Dashboard',
        default=True,
        help='Include your own dashboard in the results'
    )
    
    @api.model
    def default_get(self, fields_list):
        """Set current user as default"""
        result = super().default_get(fields_list)
        if 'user_ids' in fields_list:
            result['user_ids'] = [(6, 0, [self.env.user.id])]
        return result

    def action_view_selected_dashboards(self):
        """Open dashboard view with selected users"""
        self.ensure_one()
        
        # Get selected user IDs
        user_ids = self.user_ids.ids
        
        # Add current user if requested
        if self.include_current_user and self.env.user.id not in user_ids:
            user_ids.append(self.env.user.id)
        
        # If no users selected, default to current user
        if not user_ids:
            user_ids = [self.env.user.id]
        
        # Create dashboard records for selected users if they don't exist
        dashboard_model = self.env['fsm.dashboard']
        for user_id in user_ids:
            existing = dashboard_model.search([('user_id', '=', user_id)], limit=1)
            if not existing:
                dashboard_model.create({'user_id': user_id})
        
        # Return action to view selected dashboards
        return {
            'name': 'Selected Users Dashboard',
            'type': 'ir.actions.act_window',
            'res_model': 'fsm.dashboard',
            'view_mode': 'kanban,tree',
            'domain': [('user_id', 'in', user_ids)],
            'context': {
                'create': False,
                'edit': False,
                'delete': False,
            },
            'target': 'current',
        }

    def action_view_all_dashboards(self):
        """Open dashboard view with all users"""
        # Create dashboard records for all users
        self.env['fsm.dashboard'].create_dashboard_records()
        
        return {
            'name': 'All Users Dashboard',
            'type': 'ir.actions.act_window',
            'res_model': 'fsm.dashboard',
            'view_mode': 'kanban,tree',
            'domain': [],
            'context': {
                'create': False,
                'edit': False,
                'delete': False,
            },
            'target': 'current',
        }
