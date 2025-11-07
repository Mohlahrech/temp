# -*- coding: utf-8 -*-

from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    assigned_partner_ids = fields.One2many(
        'res.partner',
        'responsible_delegue',
        string='Partenaires assignés',
        help='Partenaires dont cet utilisateur est le délégué responsable'
    )

    assigned_partners_count = fields.Integer(
        string='Nombre de partenaires',
        compute='_compute_assigned_partners_count',
        help='Nombre de partenaires assignés à cet utilisateur'
    )

    def _compute_assigned_partners_count(self):
        """Compute the number of assigned partners"""
        for user in self:
            user.assigned_partners_count = len(user.assigned_partner_ids)

    def action_view_assigned_partners(self):
        """Action to view assigned partners"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Partenaires assignés',
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('responsible_delegue', '=', self.id)],
            'context': {'default_responsible_delegue': self.id},
        }
