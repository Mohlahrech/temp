# -*- coding: utf-8 -*-

from odoo import models, fields, api


class FsmAlert(models.Model):
    _name = 'fsm.alert'
    _description = 'FSM Alert'
    _order = 'create_date desc'

    name = fields.Text(
        string='Alert Message',
        required=True,
        help='Content of the alert message'
    )
    
    task_id = fields.Many2one(
        'project.task',
        string='Task',
        required=True,
        ondelete='cascade',
        help='Related project task'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        related='task_id.partner_id',
        store=True,
        readonly=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Created by',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    create_date = fields.Datetime(
        string='Created on',
        readonly=True
    )


class FsmAlertWizard(models.TransientModel):
    _name = 'fsm.alert.wizard'
    _description = 'FSM Alert Wizard'

    alert_message = fields.Text(
        string='Alert Message',
        required=True,
        help='Enter the alert message'
    )
    
    task_id = fields.Many2one(
        'project.task',
        string='Task',
        required=True
    )

    def action_create_alert(self):
        """Create the alert record and close the wizard"""
        self.ensure_one()
        
        # Create the alert record
        alert = self.env['fsm.alert'].create({
            'name': self.alert_message,
            'task_id': self.task_id.id,
        })
        
        # Show a success message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Alert Created',
                'message': 'Alert has been successfully created for this task.',
                'type': 'success',
                'sticky': False,
            }
        }
