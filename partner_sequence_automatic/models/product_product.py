from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = "product.product"

    bd_lofric = fields.Boolean(string="Affiché au CRM", default=False)
