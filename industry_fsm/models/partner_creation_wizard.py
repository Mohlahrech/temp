# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PartnerCreationWizard(models.TransientModel):
    _name = 'partner.creation.wizard'
    _description = 'Partner Creation Request Wizard'
    
    name = fields.Char(string='Partner Name', required=True, placeholder='Enter the partner name...')
    phone = fields.Char(string='Phone', placeholder='Optional phone number...')
    email = fields.Char(string='Email', placeholder='Optional email address...')
    city = fields.Char(string='City', placeholder='Optional city...')
    notes = fields.Text(string='Additional Notes', placeholder='Any additional information...')
    task_id = fields.Many2one('project.task', string='Related Task', required=True)
    
    def action_submit_request(self):
        """Submit the partner creation request"""
        self.ensure_one()
        
        # Create the temp partner record
        temp_partner = self.env['temp.partner'].create({
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'city': self.city,
            'notes': self.notes,
            'task_id': self.task_id.id,
        })
        
        # Update the pending request status
        self.task_id._compute_has_pending_partner_request()
        self.task_id._compute_partner_creation_warning()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
