from odoo import models, fields, api
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'


# fonction pour imprimer le contrat relatif a la facture a condition quelle soit payée
    def action_print_sale_report(self):
        # Find related sale order
        sale_order = self.env['sale.order'].search([('invoice_ids', 'in', self.ids)], limit=1)

        if not sale_order:
            raise UserError("No related Sale Order found for this invoice.")

        # Return the report action
        return self.env.ref('rent_management.action_report_crm').report_action(sale_order)
