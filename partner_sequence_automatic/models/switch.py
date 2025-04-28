from odoo import models, fields

class CrmSwitch(models.Model):
    _name = "crm.switch"
    _description = "CRM Switch Record"

    Date = fields.Date(string="Date")
    name = fields.Char(string="Nom")
    product_rec = fields.Many2one(
        "product.product",
        string="Produit récupéré",
        domain=[("bd_lofric", "!=", False)]
    )
    product_qty = fields.Float(
        string="Quantité récupérée"
    )
    pharmacie = fields.Char(
        string="Pharmacie",
        store=True,
        readonly=False
    )
    commentaire = fields.Text(
        string="Commentaire"
    )
    lead_id = fields.Many2one(
        "crm.lead",
        string="Patient",readonly=True
    ) 