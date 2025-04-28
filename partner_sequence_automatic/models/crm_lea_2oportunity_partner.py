# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _




class CustomLead2OpportunityPartner(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'



    name = fields.Selection([
        ('convert', 'Convert to opportunity'),
        ('merge', 'Merge with existing opportunities')
    ], 'Conversion Action', readonly=True, store=True, default="convert")
    action = fields.Selection([
        ('create', 'Create a new customer'),
        ('exist', 'Link to an existing customer'),
        ('nothing', 'Do not link to a customer')
    ], string='Related Customer', readonly=True, store=True, default="nothing")

    user_id = fields.Many2one(
        'res.users', 'Salesperson',
        readonly=True, store=True, compute_sudo=False)
    team_id = fields.Many2one(
        'crm.team', 'Sales Team',
         readonly=True, store=True, compute_sudo=False)

    def action_apply(self):
        """
        Override action_apply to check for duplicate leads, perform conversion/merge,
        show a notification, and then redirect to the 'crm.crm_lead_all_leads' action view.
        """
        self.ensure_one()
        CrmLead = self.env['crm.lead']

        current_lead = self.lead_id
        current_phone = current_lead.phone
        current_mobile = current_lead.mobile
        current_lead_id = current_lead.id

        # --- Start Lead Duplication Check ---
        domain_parts = []
        if current_phone:
            domain_parts.append(('phone', '=', current_phone))
            domain_parts.append(('mobile', '=', current_phone))
        if current_mobile:
            domain_parts.append(('mobile', '=', current_mobile))
            domain_parts.append(('phone', '=', current_mobile))

        if domain_parts:
            or_domain = []
            if len(domain_parts) == 1:
                or_domain = [domain_parts[0]]
            elif len(domain_parts) > 1:
                or_domain = ['|'] * (len(domain_parts) - 1)
                for part in domain_parts:
                    or_domain.append(part)

            final_domain = ['&', ('id', '!=', current_lead_id)] + or_domain
            duplicate_lead_count = CrmLead.search_count(final_domain)

            if duplicate_lead_count > 0:
                raise UserError(_("Une autre piste/tracking avec le même numéro de téléphone existe déjà."))
        # --- End Lead Duplication Check ---

        # --- Perform Conversion/Merge ---
        if self.name == 'merge':
            result_opportunity = self._action_merge()
        else:
            result_opportunity = self._action_convert()
        # --- End Conversion/Merge ---

        # --- Prepare Action to Redirect ---
        # Fetch the desired action using its XML ID
        redirect_action = self.env["ir.actions.actions"]._for_xml_id("crm.crm_lead_all_leads")
        # We generally don't need to modify the fetched action unless specific behavior is required.
        # Let's assume 'crm.crm_lead_all_leads' is already configured correctly.
        # --- End Redirection Action Preparation ---

        # --- Return Notification with Redirect as 'next' ---
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Succès'),
                'message': _('Tracking crée'),
                'sticky': False,
                'type': 'success',
                # Set the redirection action as the 'next' step
                'next': redirect_action
            }
        }
        # --- End Notification Return ---


