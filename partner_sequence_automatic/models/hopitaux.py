# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CustomHospital(models.Model):
    _inherit = 'utm.campaign'

    wilaya = fields.Many2one(
        'res.country.state',
        string="Wilaya de l'Hopital",
        domain="[('country_id.code', '=', 'DZ')]",
        help="Wilaya de l'Hopital"
    )

    wilaya2 = fields.Char(string="Wilaya")

    secteur = fields.Selection(
        selection=[
            ('ouest', 'Ouest'),
            ('sud', 'Sud'),
            ('centre', 'Centre'),
            ('est', 'Est')
        ],
        string="Secteur"
    )

    partner_ids = fields.One2many(
        'res.partner',  # Related model
        'hospital_id',  # Field in `res.partner` that links to `utm.campaign`
        string="Linked Partners",
        help="List of partners linked to this hospital."
    )
