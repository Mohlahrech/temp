# -*- coding: utf-8 -*-

from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    est_maintenance = fields.Boolean(string='Is a Repair Service')
    kilometrage_produit = fields.Integer(string="Repair Interval (km)")
    maintenance_type = fields.Selection([
        ('none', 'Not Applicable'),
        ('vidange', 'Periodic'),
        ('changement_courroie', 'Other')],
        string="Repair Type", default='none'
    )