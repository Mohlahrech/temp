from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    nom = fields.Char(string="Last Name", required=True)
    prenom = fields.Char(string="First Name", required=True)
    date_naissance = fields.Date(string="Birth Date")
    adresse = fields.Text(string="Address")
    email = fields.Char(string="Email")
    telephone = fields.Char(string="Phone")
    permis_numero = fields.Char(string="License Number")
    permis_date = fields.Date(string="License Issue Date")
    permis_lieu = fields.Char(string="Issuing Authority")
    jeune_conducteur = fields.Boolean(string="New Driver")
    is_customer = fields.Boolean(string="Is a Rental Customer", default=False)