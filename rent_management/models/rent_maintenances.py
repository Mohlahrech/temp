from odoo import models, fields

class RentMaintenance(models.Model):
    _name = 'rent.maintenance'
    _description = 'Maintenance Types'

    name = fields.Char(string="Maintenance Type", required=True)
    code = fields.Char(string="Internal Code", required=True, index=True)
    mileage_to_notify = fields.Integer(string="Mileage for Notification")
