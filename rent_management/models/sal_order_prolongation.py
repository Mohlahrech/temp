from odoo import models, fields, api
from datetime import date

class SaleOrderProlongation(models.Model):
    _name = "sale.order.prolongation"
    _description = "Sale Order Prolongation"

    sale_order_id = fields.Many2one("sale.order", string="Sale Order", required=True, ondelete="cascade")
    # is_prolongation = fields.Boolean(string="Prolongation", default=False)
    depart_prolongation = fields.Date(string="Date de départ (Prolongation)")
    retour_prolongation = fields.Date(string="Date de retour (Prolongation)")
    nombre_jour_prolongation = fields.Integer(
        string="Nombre de jours (Prolongation)",
        compute="_compute_nombre_jour_prolongation",
        store=True
    )

    @api.depends("depart_prolongation", "retour_prolongation")
    def _compute_nombre_jour_prolongation(self):
        for record in self:
            if isinstance(record.depart_prolongation, date) and isinstance(record.retour_prolongation, date):
                delta = (record.retour_prolongation - record.depart_prolongation).days
                record.nombre_jour_prolongation = max(delta, 0)
            else:
                record.nombre_jour_prolongation = 0  # Default value to avoid errors


    def create_calendar_event(self):
        for prolongation in self:
            # Prepare the description with the relevant information
            description = f"Phone : {prolongation.sale_order_id.telephone or 'N/A'}\n"
            description += f"Véhicle brand : {prolongation.sale_order_id.nom_marque or 'N/A'}\n"
            description += f"Plate number : {prolongation.sale_order_id.vehicule_immatriculation or 'N/A'}"

            # Create the calendar event
            self.env['calendar.event'].create({
                'name': f"Extension for: {prolongation.sale_order_id.partner_id.name}",  # Client's name
                'start': prolongation.depart_prolongation,  # Start date from sale.order
                'stop': prolongation.retour_prolongation,  # End date from sale.order
                'partner_ids': [(4, prolongation.sale_order_id.partner_id.id)],  # Add partner to event
                'allday': True,  # Full-day event
                'description': description,  # Event description with required fields
            })

    @api.model
    def create(self, vals):
        record = super(SaleOrderProlongation, self).create(vals)
        record.create_calendar_event()  # Trigger calendar event creation
        return record


    def unlink_line(self):
        for record in self:
            record.unlink()
