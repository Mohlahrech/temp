# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class TempPartner(models.Model):
    _name = 'temp.partner'
    _description = 'Temporary Partner Creation Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Partner Name', required=True)
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, readonly=True)
    request_date = fields.Datetime(string='Request Date', default=fields.Datetime.now, readonly=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='pending', readonly=True, tracking=True)
    
    # Additional optional fields that could be useful
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    city = fields.Char(string='City')
    notes = fields.Text(string='Additional Notes')
    
    # Link to the created partner once approved
    partner_id = fields.Many2one('res.partner', string='Created Partner', readonly=True)
    
    # Link to the task that triggered the request
    task_id = fields.Many2one('project.task', string='Related Task')
    
    def action_approve(self):
        """Approve the partner creation request and create the actual partner"""
        self.ensure_one()
        if self.state != 'pending':
            return
            
        # Create the actual partner
        partner_vals = {
            'name': self.name,
            'is_company': True,
            'customer_rank': 1,
            'supplier_rank': 0,
        }
        
        # Add optional fields if provided
        if self.phone:
            partner_vals['phone'] = self.phone
        if self.email:
            partner_vals['email'] = self.email
        if self.city:
            partner_vals['city'] = self.city
            
        partner = self.env['res.partner'].create(partner_vals)
        
        # Update the temp partner record
        self.write({
            'state': 'approved',
            'partner_id': partner.id,
        })
        
        # Post message to chatter
        self.message_post(
            body=_('Partner creation request approved. Partner "%s" has been created with ID %s.') % (self.name, partner.id),
            message_type='notification'
        )
        
        # If there's a related task, update its partner_id and refresh status
        if self.task_id:
            self.task_id.write({'partner_id': partner.id})
            self.task_id._compute_has_pending_partner_request()
            self.task_id._compute_partner_creation_warning()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Partner "%s" has been created successfully!') % self.name,
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_reject(self):
        """Reject the partner creation request"""
        self.ensure_one()
        if self.state != 'pending':
            return
            
        self.write({'state': 'rejected'})
        
        # Post message to chatter
        self.message_post(
            body=_('Partner creation request rejected.'),
            message_type='notification'
        )
        
        # Update the task's pending request status
        if self.task_id:
            self.task_id._compute_has_pending_partner_request()
            self.task_id._compute_partner_creation_warning()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Request Rejected'),
                'message': _('Partner creation request for "%s" has been rejected.') % self.name,
                'type': 'info',
                'sticky': False,
            }
        }
