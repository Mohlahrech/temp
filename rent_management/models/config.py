from odoo import models, fields, api, _
from odoo.exceptions import UserError



class AgenceVehicule(models.Model):
    _name = 'agence.vehicule'
    _description = 'Vehicle Information'
    _rec_name = 'display_name'

    # Basic Information
    marque = fields.Char(string="Brand", required=True)
    modele = fields.Char(string="Model")
    immatriculation = fields.Char(string="License Plate", required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, readonly=True)

    # Technical Specifications
    annee = fields.Integer(string="Year")
    cylindre = fields.Char(string="Engine Size")
    numerochassis = fields.Char(string="Chassis Number")
    permis_required = fields.Boolean(string="Special License Required")

    disponibilite = fields.Selection([
        ('disponible', 'Available'),
        ('en_location', 'Rented')],
        string="Availability",
        compute='_compute_disponibilite',
        store=True
    )

    # Dépendance sur l'état stocké des commandes liées
    @api.depends('sale_order_ids.state_location')
    def _compute_disponibilite(self):
        busy_states = {'retour', 'encours', 'retard', 'reserve'}
        for record in self:
            # Par défaut, le véhicule est disponible
            is_en_location = False
            # Vérifier si une des commandes liées a un état "occupé"
            for order in record.sale_order_ids:
                if order.state_location in busy_states:
                    is_en_location = True
                    break  # Pas besoin de vérifier les autres commandes pour ce véhicule
            # Assigner l'état
            record.disponibilite = 'en_location' if is_en_location else 'disponible'




    # Add relation field to access sale orders
    sale_order_ids = fields.One2many('sale.order', 'vehicule_marque', string='Rental Orders')

    # Additional Info
    notes = fields.Text(string="Additional Notes")

    # Computed display name
    display_name = fields.Char(string="Display Name", compute="_compute_display_name", store=True)



    @api.depends('marque', 'modele')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.marque} - {rec.modele}" if rec.modele else rec.marque

    def action_view_reservations(self):
        self.ensure_one()
        return {
            'name': _("Reservations for %s") % self.marque,
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('rent_management.view_quotation_tree_inherit').id, 'list'),
                (False, 'form'),
            ],
            'domain': [('vehicule_marque', '=', self.id)],
            'context': {
                'default_vehicule_marque': self.id,
                'search_default_vehicule_marque': self.id,
            },
            'target': 'current',
        }

    def action_view_repairs(self):
        self.ensure_one()
        return {
            'name': _("Repairs for %s") % self.marque,
            'type': 'ir.actions.act_window',
            'res_model': 'historique.maintenance',
            'view_mode': 'list,form',
            'domain': [('vehicule_id', '=', self.id)],
            'context': {
                'default_vehicule_id': self.id,
                'search_default_vehicule_id': self.id
            },
            'target': 'current',
        }




    #maintenance#####################################

    type_maintenance_selection = fields.Many2one(
        'rent.maintenance',
        string="Type of Maintenance"
    )

    # type_maintenance_selection = fields.Selection([
    #     ('oil_change', 'Oil Change'),
    #     ('brake_service', 'Brake Service'),
    #     ('tire_service', 'Tire Service'),
    #     ('engine_repair', 'Engine Repair'),
    #     ('transmission_repair', 'Transmission Repair'),
    #     ('suspension_repair', 'Suspension Repair'),
    #     ('battery_replacement', 'Battery Replacement'),
    #     ('cooling_system', 'Cooling System Repair'),
    #     ('air_conditioning', 'A/C Service'),
    #     ('electrical_system', 'Electrical System Repair'),
    #     ('exhaust_system', 'Exhaust System Repair'),
    #     ('belt_and_hoses', 'Belts and Hoses Replacement'),
    #     ('wheel_alignment', 'Wheel Alignment'),
    #     ('diagnostics', 'Diagnostics'),
    #     ('state_inspection', 'State Inspection'),
    #     ('body_repair', 'Body or Paint Repair'),
    # ], string="Repair Type")

    maintenance_note = fields.Text(string="Repair Description")
    a_maintenir = fields.Boolean(
        string="Maintenance Required",
        compute='_compute_a_maintenir',
        store=True,
        default=False,
        tracking=True
    )
    maintenance_message = fields.Char(compute='_compute_a_maintenir', store=True)
    historique_maintenance_ids = fields.One2many(
        'historique.maintenance',
        'vehicule_id',
        string='Repairs history'
    )
    kilometrage_vehicule = fields.Integer(string="Actual Mileage")

    @api.depends('kilometrage_vehicule', 'historique_maintenance_ids')
    def _compute_a_maintenir(self):
        for record in self:
            last_maintenances = {}
            for maintenance_record in record.historique_maintenance_ids:
                m_type = maintenance_record.type_maintenance
                if not m_type:
                    continue

                if m_type.id not in last_maintenances or \
                   maintenance_record.kilometrage > last_maintenances[m_type.id].kilometrage:
                    last_maintenances[m_type.id] = maintenance_record

            needed_maintenances = []
            for m_id, last_maintenance_record in last_maintenances.items():
                mileage_to_notify = last_maintenance_record.type_maintenance.mileage_to_notify
                if mileage_to_notify and mileage_to_notify > 0:
                    mileage_since_last = record.kilometrage_vehicule - last_maintenance_record.kilometrage
                    if mileage_since_last >= mileage_to_notify:
                        needed_maintenances.append(last_maintenance_record.type_maintenance.name)

            if needed_maintenances:
                record.a_maintenir = True
                record.maintenance_message = _("This vehicle needs maintenance for: %s.") % ", ".join(needed_maintenances)
            else:
                record.a_maintenir = False
                record.maintenance_message = ""

    def action_faire_maintenance(self):
        self.ensure_one()
        maintenance_type = self.type_maintenance_selection
        current_mileage = self.kilometrage_vehicule
        today_date = fields.Date.today()

        if not maintenance_type:
            raise UserError(_("Please select a maintenance to perform."))

        # Create maintenance history record
        self.env['historique.maintenance'].create({
            'vehicule_id': self.id,
            'date': today_date,
            'type_maintenance': maintenance_type.id,
            'kilometrage': current_mileage,
            'note': self.maintenance_note
        })

        # Retourner une action pour recharger la vue actuelle
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,  # Nom du modèle courant
            'res_id': self.id,  # ID de l'enregistrement courant
            'view_mode': 'form',  # Afficher la vue formulaire
            'views': [(False, 'form')],  # Spécifier la vue form
            'target': 'current',  # Recharger dans la vue actuelle
        }


