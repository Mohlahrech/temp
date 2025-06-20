from odoo import models, fields, api, _
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Champs pour "Conducteur 1"
    conducteur1 = fields.Many2one('res.partner', string="Primary Driver")
    nom = fields.Char(string="Last Name", related='conducteur1.nom', store=True)
    prenom = fields.Char(string="First Name", related='conducteur1.prenom', store=True)
    date_naissance = fields.Date(string="Birth Date", related='conducteur1.date_naissance', store=True)
    adresse = fields.Text(string="Address", related='conducteur1.adresse', store=True)
    email = fields.Char(string="Email", related='conducteur1.email', store=True)
    telephone = fields.Char(string="Phone", related='conducteur1.phone', store=True)
    permis_numero = fields.Char(string="License Number", related='conducteur1.permis_numero', store=True)
    permis_date = fields.Date(string="License Issue Date", related='conducteur1.permis_date', store=True)
    permis_lieu = fields.Char(string="Issuing Authority", related='conducteur1.permis_lieu', store=True)
    jeune_conducteur = fields.Boolean(string="New Driver", related='conducteur1.jeune_conducteur', store=True)

    # Champs pour "Conducteur 2"
    conducteur2 = fields.Many2one('res.partner', string="Secondary Driver")
    nom2 = fields.Char(string="Last Name", related='conducteur2.nom', store=True)
    prenom2 = fields.Char(string="First Name", related='conducteur2.prenom', store=True)
    date_naissance2 = fields.Date(string="Birth Date", related='conducteur2.date_naissance', store=True)
    adresse2 = fields.Text(string="Address", related='conducteur2.adresse', store=True)
    email2 = fields.Char(string="Email", related='conducteur2.email', store=True)
    telephone2 = fields.Char(string="Phone", related='conducteur2.phone', store=True)
    permis_numero2 = fields.Char(string="License Number", related='conducteur2.permis_numero', store=True)
    permis_date2 = fields.Date(string="License Issue Date", related='conducteur2.permis_date', store=True)
    permis_lieu2 = fields.Char(string="Issuing Authority", related='conducteur2.permis_lieu', store=True)
    jeune_conducteur2 = fields.Boolean(string="New Driver", related='conducteur2.jeune_conducteur', store=True)

    # Champs pour "Location"
    vehicule_marque = fields.Many2one('agence.vehicule', string="Vehicle Brand")
    nom_marque = fields.Char(string="Brand Name", related='vehicule_marque.marque', store=True)
    vehicule_immatriculation = fields.Char(string="License Plate", related='vehicule_marque.immatriculation',
                                           store=True)
    date_depart = fields.Date(string="Start Date")
    # heure_depart = fields.Selection(
    #     [(f"{h:02d}:{m:02d}", f"{h:02d}:{m:02d}")
    #      for h in range(0, 24)
    #      for m in (0, 15, 30, 45)],
    #     string="Time"
    # )

    nombre_jour = fields.Char(string="Number of Days",compute="_compute_nombre_jour",
        store=True
    )

#Calculer le nombre de jours
    @api.depends("date_depart", "date_retour")
    def _compute_nombre_jour(self):
        for record in self:
            if isinstance(record.date_depart, date) and isinstance(record.date_retour, date):
                delta = (record.date_retour - record.date_depart).days
                record.nombre_jour = str(max(delta, 0))  # Convert to string
            else:
                record.nombre_jour = "0"  # Ensure it's a string
####################

    kilometrage_depart = fields.Integer(string="Start Mileage")
    # niveau_essence_depart = fields.Char(string="Fuel level at departure")
    niveau_fuel_depart = fields.Selection([
        ('0', 'Empty'),
        ('1', '1/4'),
        ('2', 'Half'),
        ('3', '3/4'),
        ('4', 'Full'),
    ], string="Start Fuel Level", default='0')
    niveau_fuel_retour = fields.Selection([
        ('0', 'Empty'),
        ('1', '1/4'),
        ('2', 'Half'),
        ('3', '3/4'),
        ('4', 'Full'),
    ], string="End Fuel Level", default='0')

    kilometrage_retour = fields.Integer(string="End Mileage")
    # niveau_essence_retour = fields.Char(string="Fuel level at return")
    prolongation = fields.Text(string="Extension")

    date_retour = fields.Date(string="End Date")

    start_time = fields.Float(string="Start Time")
    return_time = fields.Float(string="End Time")

    date_signature = fields.Date(string="Signature Date")
    customer_signature_img = fields.Binary(string="Customer Signature", copy=False)

# en cas de prolongation

    is_prolongation = fields.Boolean(string="Is Extension", default=False)

    prolongation_id = fields.One2many("sale.order.prolongation", "sale_order_id", string="Extensions")

    rental_done = fields.Boolean(string="Rental Done", default=False)


    def action_set_prolongation(self):
        """Set is_prolongation to True and update state_location to 'encours'"""
        for record in self:
            record.is_prolongation = True
            record.state_location = 'encours'

    latest_retour_prolongation = fields.Date(
        string="Latest Extension Return",
        compute="_compute_latest_retour_prolongation",
        store=True
    )
#Date du dernier retour de prolongation
    @api.depends("prolongation_id.retour_prolongation")
    def _compute_latest_retour_prolongation(self):
        for order in self:
            if order.prolongation_id:
                latest_prolongation = max(order.prolongation_id, key=lambda p: p.retour_prolongation or date.min)
                order.latest_retour_prolongation = latest_prolongation.retour_prolongation
            else:
                order.latest_retour_prolongation = False  # Default to no value

    # ###############################

    def action_confirm(self):
        # Appeler la méthode originale
        res = super(SaleOrder, self).action_confirm()

        # Créer un événement dans le calendrier
        for order in self:
            description = _("Phone number : %s\nVehicle : %s\nLicence Plate : %s") % (
                order.telephone or _('N/A'),
                order.nom_marque or _('N/A'),
                order.vehicule_immatriculation or _('N/A')
            )

            self.env['calendar.event'].create({
                'name': order.partner_id.name,  # Nom de l'événement = client
                'start': order.date_depart,  # Date de début depuis sale.order
                'stop': order.date_retour,  # Date de fin depuis sale.order
                'partner_ids': [(4, order.partner_id.id)],  # Ajouter le partenaire à l'événement
                'allday': True,  # Indiquer que c'est un événement sur toute la journée
                'description': description,  # Ajouter la description avec les champs demandés
            })

        return res
###################################

    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')

    state_location = fields.Selection([
        ('draft', 'Draft'),
        ('encours', 'In Progress'),
        ('retour', 'For Today'),
        ('retard', 'Late'),
        ('done', 'Done'),
        ('reserve', 'Reserved'),
        ('cancel', 'Cancelled'),
    ], string='Rental Status', compute='_compute_state_location', store=True, readonly=False)

##############"marquer comme fait#####################################################
    # ajouter un moolean pour definir si la commande a des lignes non facturées
    has_uninvoiced_lines = fields.Boolean(
        string="Has Uninvoiced Lines",
        compute="_compute_has_uninvoiced_lines",
        store=True,  # Store the value in the database for faster access
    )

    @api.depends('order_line.invoice_status')
    def _compute_has_uninvoiced_lines(self):
        for record in self:
            # Check if any order line has invoice_status 'no' or 'to invoice'
            if any(
                    line.invoice_status in ('no', 'to invoice')
                    for line in record.order_line
            ):
                record.has_uninvoiced_lines = True
            else:
                record.has_uninvoiced_lines = False

                ########################


    # action pour marquer comme fait
    def action_set_done(self):
        for record in self:
            if not record.kilometrage_retour:
                raise UserError(_("Please insert the End Mileage."))

            today = fields.Date.today()

            if record.state_location == 'retard':
                if record.is_prolongation:
                    if record.latest_retour_prolongation and record.latest_retour_prolongation < today:
                        raise UserError(_("Please add an extension for the late days."))
                    else:
                        raise UserError(_("Please add an extension for the late days."))

                else:
                    raise UserError(_("Please add an extension for the late days."))

            # ✅ verifier si il'nya pas de lignes non facturés
            if record.has_uninvoiced_lines:
                raise UserError(
                    _("Unable to close the contract: some order lines are not invoiced."))

            # Set rental_done to True to override the automatic computation
            record.rental_done = True

            # Mettre à jour le kilométrage du véhicule lié
            if record.vehicule_marque:
                record.vehicule_marque.kilometrage_vehicule = record.kilometrage_retour

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self._name,
            'target': 'current',
            'res_id': self.id,
            'effect': {
                'fadeout': 'slow',
                'message': _("The rent contract has been closed successfully ✅"),
                'type': 'rainbow_man',
            }
        }
    #########################################"

# Champ pour Etat de la location

    def action_test_notification(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Warning!'),
                'message': _('This contract is late!'),
                'type': 'warning',
                'sticky': True,
            }
        }

    # jai ajouté ce bouton pour imprimer un message lors de limpression avec une condition que la facture lié soit payé gg

    has_paid_invoice = fields.Boolean(
        string="Has Paid Invoice",
        compute="_compute_has_paid_invoice",
        store=True
    )

    @api.depends('invoice_ids.payment_state')
    def _compute_has_paid_invoice(self):
        for order in self:
            order.has_paid_invoice = any(order.invoice_ids.filtered(lambda inv: inv.payment_state == 'paid'))



# faire en sorte que user noublie pas dajouter la prolongatin dans lesl ignes de commande

    @api.constrains('order_line', 'prolongation_id')
    def _check_order_lines_vs_prolongation(self):
        for order in self:
            num_prolongations = len(order.prolongation_id)
            num_order_lines = len(order.order_line)

            # Ne pas appliquer la restriction s'il n'y a aucune prolongation
            if num_prolongations == 0:
                continue

                # Calcul du nombre minimal requis d'order_lines
            min_order_lines = 3 + max(0,
                                      num_prolongations - 1)  # 3 pour la première + 1 par prolongation supplémentaire

            if num_order_lines < min_order_lines:
                raise ValidationError(
                    _("Please add an additional order line related to the extension that has been added."
                ))



# faire en sorte que les contrats qui sont finis disparaisse du calendrier

# class CalendarEvent(models.Model):
#     _inherit = 'calendar.event'
#
#     active = fields.Boolean(default=True)  # Ensure the field is there

    # @api.model
    # def _deactivate_old_events(self):
    #     """Automatically deactivate events whose stop date is in the past."""
    #     today = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    #     old_events = self.search([('stop', '<', today), ('active', '=', True)])
    #     old_events.write({'active': False})


    @api.depends('state', 'is_prolongation', 'prolongation_id.retour_prolongation', 'date_retour', 'rental_done', 'date_depart')
    def _compute_state_location(self):
        for record in self:
            today = fields.Date.context_today(record)
            date_depart = record.date_depart
            previous_state = record.state_location  # Store previous state before computation

            if record.rental_done:
                record.state_location = 'done'
                continue

            if record.state in ['draft', 'sent']:
                record.state_location = 'draft'
                continue
            elif record.state == 'cancel':
                record.state_location = 'cancel'
                continue

            if record.state in ['sale', 'done']:
                if record.is_prolongation and record.prolongation_id:
                    latest_prolongation = max(record.prolongation_id,
                                              key=lambda p: p.retour_prolongation or fields.Date.to_date('1900-01-01'))
                    retour_date = latest_prolongation.retour_prolongation
                else:
                    retour_date = record.date_retour

                if retour_date:
                    retour_date = fields.Date.to_date(retour_date)
                    if retour_date == today:
                        record.state_location = 'retour'
                    elif retour_date > today and date_depart > today:
                        record.state_location = 'reserve'
                    elif retour_date > today and date_depart <= today:
                        record.state_location = 'encours'
                    else:
                        record.state_location = 'retard'
                else:
                    record.state_location = 'draft'

            # If state changed to 'retard', create CRM activity
            if record.state_location == 'retard' and previous_state != 'retard':
                record.action_create_activity()



    def action_create_activity(self):
        """Create a CRM activity when state_location is set to 'retard' if it doesn't already exist."""
        activity_type_id = self.env.ref('mail.mail_activity_data_todo').id  # Default 'To Do' activity type

        for order in self:

            if order.state_location == 'retard':  # Only process records in 'retard' state
                deadline = fields.Date.today()  # Activity deadline set to today

                # Check if an activity already exists for this record and user
                existing_activity = self.env['mail.activity'].search([
                    ('res_model', '=', self._name),
                    ('res_id', '=', order.id),
                    ('activity_type_id', '=', activity_type_id),
                    ('user_id', '=', order.user_id.id),
                    ('summary', '=', 'Late contract'),
                ], limit=1)

                if not existing_activity:
                    # Create the activity if it doesn't exist
                    self.env['mail.activity'].create({
                        'res_model_id': self.env['ir.model']._get_id(self._name),
                        'res_id': order.id,
                        'activity_type_id': activity_type_id,
                        'user_id': order.user_id.id,
                        'date_deadline': deadline,
                        'summary': 'Late',
                        'note': 'This notification was automatically generated because the return date has been exceeded.',
                    })

    # cette fonction me sert a avoir par defaut le bon kilometrage
    @api.onchange('vehicule_marque')
    def _onchange_vehicule_marque_set_kilometrage(self):
        if self.vehicule_marque and not self.kilometrage_depart:
            vehicule = self.env['agence.vehicule'].browse(self.vehicule_marque.id)
            self.kilometrage_depart = vehicule.kilometrage_vehicule