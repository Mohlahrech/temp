from odoo import fields, models, api, _
from odoo.exceptions import UserError


class res_groups(models.Model):
    _inherit = 'res.groups'
    
    def write(self, vals):
        res = super(res_groups, self).write(vals)
        obj = self.env['access.management'].search([])
        for access in obj:
            access._access_user_group()
        return res