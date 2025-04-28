from odoo import models, fields, api
from odoo.exceptions import UserError



class CrmStageConfirmation(models.TransientModel):
    _name = 'crm.stage.confirmation'
    _description = 'Stage Change Confirmation'

    lead_id = fields.Many2one('crm.lead', string="Lead", required=True)
    stage_id = fields.Many2one('crm.stage', string="Stage", required=True)

    def action_confirm(self):
        self.lead_id.write({'stage_id': self.stage_id.id})

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
