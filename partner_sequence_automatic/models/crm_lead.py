from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta


class CrmLead(models.Model):
    _inherit = "crm.lead"

    country_id = fields.Many2one(
        'res.country',
        string='Country',
        default=lambda self: self.env['res.country'].browse(62),
        readonly=False,
        store=True
    )

    constant_one = fields.Integer(string="Constant One", default=1, store=True)
    # the above field was created to count the number ofleads

    user_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        default=lambda self: self.env.user,
        domain="['&', ('share', '=', False), ('company_ids', 'in', user_company_ids), ('partner_id.pfp', '=', True)]",
        check_company=True,
        index=True,
        tracking=True
    )

    secteur = fields.Selection(
        selection=[
            ('ouest', 'Ouest'),
            ('sud', 'Sud'),
            ('centre', 'Centre'),
            ('est', 'Est')
        ],
        string="Secteur"
    )
    # for later
    # hopital = fields.Char(
    #     string="Hopital",
    #     store=True,
    #     readonly=False)

    # @api.onchange('hopital')
    # def _onchange_hopital(self):
    #     if self.hopital:
    #         campaign = self.env['utm.campaign'].search([('name', '=', self.hopital)], limit=1)
    #         if campaign:
    #             self.campaign_id = campaign
    #         else:
    #             self.campaign_id = False


    pharmacie = fields.Char(
        string="Pharmacie concurrente",
        store=True,
        readonly=False)

    pharmacie_id = fields.Many2one(
        "res.partner",
        string="Pharmacie",
        domain=[('is_pharmacie', '=', True)]
    )

    doctor = fields.Char(
        string="Medecin Préscripteur",
        store=True,
        readonly=False)

    has_duplicate_phone = fields.Boolean(
        string="Has Duplicate Phone", compute="_compute_has_duplicate_phone", store=False
    )

    patient_ref = fields.Char(
        string="Patient Reference",
        related="partner_id.ref",
        store=True,
        readonly=False, placeholder="Ce patient n'existe pas.")

    date_of_birth = fields.Date(string='Date de naissance',
                                help='Date of birth of the patient')

    date_of_accord = fields.Date(string='Date Accords Caisse',
                                help='Date of birth of the patient')
    date_adhesion = fields.Date(string='Date Adhésion du patient',
                                help='Date Adhésion du patient')



    wilaya_cnas = fields.Char(
        string="Wilaya Cnas",
        store=True,
        readonly=False)

    wilaya_cnas2 = fields.Many2one(
        "res.country.state",
        string="Wilaya CNAS",
        domain=[("country_id", "=", 62)]  # Filtering for country_id = 62
    )


    antene_caisse = fields.Char(
        string="Antenne caisse",
        store=True,
        readonly=False)

    pathologie = fields.Char(
        string="Pathologie",
        store=True,
        readonly=False)

    cause_pathologie = fields.Char(
        string="Cause de la pathologie",
        store=True,
        readonly=False)

    cause_pathologie2 = fields.Selection([
        ("bm", "Blessure médullaire (BM)"),
        ("sep", "Sclérose en plaque (SEP)"),
        ("sb", "Spina bifida (SB)"),
        ("ruc", "Rétention urinaire chronique (RUC)")
    ], string="Cause de la pathologie")


    call_ids = fields.One2many("crm.call.history", "crm_id", string="Liste des apelles", order="date_recup asc")

    switch_ids = fields.One2many(
        "crm.switch",
        "lead_id",
        string="Switch"
    )

    @api.depends('phone', 'mobile')
    def _compute_has_duplicate_phone(self):
        for lead in self:
            duplicate_partner = 0
            duplicate_partner2 = 0
            duplicate_partner3 = 0
            duplicate_partner4 = 0
            if lead.phone:
                duplicate_partner = self.env['res.partner'].search_count([('phone', '=', lead.phone)])
                duplicate_partner3 = self.env['res.partner'].search_count([('mobile', '=', lead.phone)])

            if lead.mobile:
                duplicate_partner2 = self.env['res.partner'].search_count([('mobile', '=', lead.mobile)])
                duplicate_partner4 = self.env['res.partner'].search_count([('phone', '=', lead.mobile)])

            lead.has_duplicate_phone = duplicate_partner > 0 or duplicate_partner2 > 0 or duplicate_partner3 > 0 or duplicate_partner4 > 0



    @api.depends('partner_id')
    def _compute_contact_name(self):
        # Override the method to do nothing
        pass

    @api.depends('partner_id.phone')
    def _compute_phone(self):
        # Override the method to do nothing
        pass

    def _inverse_phone(self):
        # Override the method to do nothing
        pass

    @api.depends('partner_id')
    def _compute_mobile(self):
        # Override the method to do nothing
        pass

    @api.depends('partner_id')
    def _compute_partner_address_values(self):
        # Override the method to do nothing
        pass




    def create_partner_from_lead(self):
        for lead in self:
            # Check if user_id is defined
            if not lead.user_id:
                raise UserError("Veuillez assigner un PFP avant de créer le patient.")
            if not lead.phone and not lead.mobile:
                raise UserError("Veuillez remplir le numéro de téléphone du patient.")

            if lead.has_duplicate_phone:
                raise UserError("Un client avec le même numéro de téléphone existe déjà.")

            # Collect the values to create the partner
            partner_values = {
                'is_patient': True,
                'name': lead.name,
                'street': lead.street,
                'street2': lead.street2,
                'city': lead.city,
                'state_id': lead.state_id.id if lead.state_id else False,
                'zip': lead.zip,
                'country_id': lead.country_id.id if lead.country_id else False,
                'function': lead.function,
                'phone': lead.phone,
                'mobile': lead.mobile,
                'email': lead.email_from,
                'telecomercial': lead.user_id.id,
                'hospital_id': lead.campaign_id.id,
                'date_of_birth': lead.date_of_birth,
                'securite_id': lead.source_id.id if lead.source_id else False,
            }

            # Create the partner record
            partner = self.env['res.partner'].create(partner_values)

            # Optionally, link the partner to the lead if needed
            lead.partner_id = partner

        return True



    # all this have been put here just to hide the damn create quotation button and better performance

    sale_amount_total = fields.Monetary(compute='_compute_sale_data', string="Sum of Orders",
                                        help="Untaxed Total of Confirmed Orders", currency_field='company_currency')
    quotation_count = fields.Integer(compute='_compute_sale_data', string="Number of Quotations")
    sale_order_count = fields.Integer(compute='_compute_sale_data', string="Number of Sale Orders")

    bool_lofric = fields.Boolean(string="Lofric", store=True)
    bool_bd = fields.Boolean(string="BD", store=True)
    bool_concurent = fields.Boolean(string="Concurrent", store=True)


    def action_sale_quotations_new(self):
        # Override the method to do nothing
        pass

    def action_view_sale_quotation(self):
        # Override the method to do nothing
        pass

    def action_view_sale_order(self):
        # Override the method to do nothing
        pass



    @api.onchange('stage_id')
    def _onchange_stage_id(self):
        if self.name != False:
            if self.stage_id:
                return {
                    'warning': {
                        'title': "Vous avez changé l'étape",
                        'message': f"Le patient: '{self.name}' a été changé vers '{self.stage_id.name}'.",
                    }
                }





    def action_create_activity(self):
        """Delete existing activities of type 2 and create three new ones based on the latest call date + 30, 60, and 80 days."""
        activity_type_id = 2  # Set the activity type ID

        for lead in self:
            if not lead.user_id:
                raise UserError("Veuillez d'abord assigner un pfp.")

            # Get the latest call date from call_ids safely handling False values
            latest_call = max(
                lead.call_ids.filtered(lambda r: r.date_recup),
                key=lambda r: r.date_recup or fields.Date.from_string('1900-01-01'),
                default=False
            )

            if not latest_call:
                raise UserError("Aucune date de récupération n'a été trouvée.")

            # Find and delete existing activities of the specified type for this lead
            existing_activities_to_delete = self.env['mail.activity'].search([
                ('res_model_id', '=', self.env['ir.model']._get_id('crm.lead')),
                ('res_id', '=', lead.id),
                ('activity_type_id', '=', activity_type_id),
            ])
            if existing_activities_to_delete:
                existing_activities_to_delete.unlink()

            # Define deadlines for the three activities
            deadlines = [
                latest_call.date_recup + timedelta(days=30),
                latest_call.date_recup + timedelta(days=60),
                latest_call.date_recup + timedelta(days=80),
            ]

            # Create the activities for the defined deadlines
            for deadline in deadlines:
                self.env['mail.activity'].create({
                    'res_model_id': self.env['ir.model']._get_id('crm.lead'),
                    'res_id': lead.id,
                    'activity_type_id': activity_type_id,
                    'user_id': lead.user_id.id,
                    'date_deadline': deadline,
                    'summary': 'Apeller le patient',
                    'note': f'Basée sur date de récuperation + {deadline - latest_call.date_recup}.',
                })


