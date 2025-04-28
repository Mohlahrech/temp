from odoo import models, fields

class ResUsers(models.Model):
    _inherit = "res.users"

    pfp = fields.Boolean(string="PFP", default=False)
