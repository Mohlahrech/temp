# -*- coding: utf-8 -*-

from odoo import models, fields, api


class FsmKpiDashboardFilter(models.TransientModel):
    _name = 'fsm.kpi.dashboard.filter'
    _description = 'FSM KPI Dashboard User Filter'

    filter_user_id = fields.Many2one(
        'res.users',
        string='Filter by User',
        help='Select a user to filter the dashboard KPIs. Leave empty to show all users.'
    )

    def action_apply_filter(self):
        """Apply the user filter to all active KPI records and refresh the dashboard"""
        self.ensure_one()
        filter_user_id = self.filter_user_id.id if self.filter_user_id else False
        
        # Apply filter to all active KPI dashboard records
        dashboard_model = self.env['fsm.kpi.dashboard']
        active_records = dashboard_model.search([('active', '=', True)])
        
        if filter_user_id:
            active_records.write({'filter_user_id': filter_user_id})
        else:
            active_records.write({'filter_user_id': False})
        
        # Invalidate cache to recompute values
        active_records.invalidate_cache(['value', 'previous_value', 'trend', 'trend_percentage'])
        
        # Return action to reload the dashboard view
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    def action_clear_filter(self):
        """Clear the user filter"""
        self.ensure_one()
        self.filter_user_id = False
        return self.action_apply_filter()

