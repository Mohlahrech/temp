# -*- coding: utf-8 -*-
from odoo import models, fields

class HistoriqueMaintenance(models.Model):
    _name = 'historique.maintenance'
    _description = 'Vehicle Maintenance History'
    _order = 'date desc' # Order by date descending by default

    vehicule_id = fields.Many2one(
        'agence.vehicule',
        string='Vehicle',
        required=True,
        ondelete='cascade' # If the vehicle is deleted, delete its history
    )
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    type_maintenance = fields.Many2one(
        'rent.maintenance',
        string='Repair Type',
        required=True
    )
    kilometrage = fields.Integer(string='Mileage at Maintenance')
    note = fields.Text(string='Notes')

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.vehicule_id.display_name} - {record.date} - {record.type_maintenance.name}"
            result.append((record.id, name))
        return result