# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = "res.partner"
    _description = "Res Partner Sequences"

    # @api.model
    # def create(self, vals):
    #     vals['ref'] = self.env['ir.sequence'].next_by_code('res.partner') or '/'
    #     return super(ResPartner, self).create(vals)

    is_patient = fields.Boolean(string="Is Patient", default=False, help="Indicates whether the partner is a patient."
                                , store=True)

    pfp = fields.Boolean(string="PFP", default=False)

    is_pharmacie = fields.Boolean(string="Pharmacie", default=False, help="Indicates whether the partner is a pharmacy."
                                ,store=True)

    telecomercial = fields.Many2one(
        'res.users', string='Télécommercial',
        readonly=False, store=True, domain="[('partner_id.pfp', '=', True)]",
        help='The second internal user in charge of this contact.')


    hospital_id = fields.Many2one(
        'utm.campaign', string='Hopital',
        readonly=False, store=True,
        help='Hopital du patient.')

    securite_id = fields.Many2one(
        'utm.source', string='Sécurité sociale',
        readonly=False, store=True,
        help='Sécurité sociale du patient.')

    date_of_birth = fields.Date(string='Date de naissance',
                                help='Date of birth of the patient')

    crm_call_history_ids = fields.One2many(
        "crm.call.history",
        "partner_id",
        string="Historique des appels CRM"
    )


# Créer une séquence pour le patient
    ref = fields.Char(string="Reference", compute="_compute_ref", store=True, readonly=True)
    sequence_id = fields.Char(string="Sequence", readonly=True)  # No default value

    @api.depends('sequence_id', 'telecomercial')
    def _compute_ref(self):
        for record in self:
            telecomercial_prefix = record.telecomercial.name[
                                   :3].upper() if record.telecomercial and record.telecomercial.name else ''
            record.ref = f"{telecomercial_prefix}/{record.sequence_id}" if record.sequence_id else ''

    @api.model
    def create(self, vals):
        # Assign sequence only when record is created
        vals['sequence_id'] = self.env['ir.sequence'].next_by_code('res.partner') or '/'
        partner = super(ResPartner, self).create(vals)
        partner._compute_ref()  # Ensure `ref` is updated after creation
        return partner
    # @api.model
    # def create(self, vals):
    #     # Check for duplicate phone numbers
    #     if vals.get('phone'):
    #         existing_partner = self.search([('phone', '=', vals['phone'])], limit=1)
    #         if existing_partner:
    #             raise ValidationError(
    #                 f"Un partenaire avec le même numéro {vals['phone']} existe déja: {existing_partner.ref}."
    #             )
    #
    #     # Generate the sequence only on creation
    #     if not vals.get('sequence_id'):
    #         vals['sequence_id'] = self.env['ir.sequence'].next_by_code('res.partner') or '/'
    #
    #     return super(ResPartner, self).create(vals)

