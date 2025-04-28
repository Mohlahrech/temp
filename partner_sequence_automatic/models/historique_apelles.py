# -*- coding: utf-8 -*-
from odoo import models, fields, _, api


class HistoriqueAppels(models.Model):
    _name = 'crm.call.history'
    _description = 'CRM Call History'
    _order = "date_call desc"

    partner_id = fields.Many2one(
        "res.partner",
        string="Client",
        related="crm_id.partner_id",
        required=True
    )
    crm_id = fields.Many2one(
        "crm.lead",
        string="Tracking",
        required=True
    )
    partner_code_id = fields.Char(
        string="Code patient",
        related="partner_id.ref",
        readonly=True
    )
    date_call = fields.Datetime(
    string="Date du call", 
    default=lambda self: fields.Datetime.now()
)
    date_recup = fields.Date(
        string="Date de récuperation"
    )
    commentaire = fields.Text(
        string="Commentaire"
    )
    product_id = fields.Many2one(
        "product.product",
        string="Produit utilisé",domain=[("bd_lofric", "!=", False)]
    )
    
    product_qty = fields.Float(
        string="Quantité utilisée"
    )
    product_id2 = fields.Many2one(
        "product.product",
        string="Produit récupéré",domain=[("bd_lofric", "!=", False)]
    )

    product_id4 = fields.Char(
        string="Produit du concurrent", store=True
    )

    product_id5 = fields.Many2one(
        "product.product",
        string="Produit concurent",domain=[("bd_lofric", "!=", False)])
    product_id6 = fields.Many2one(
        "product.product",
        string="Produit concurent",domain=[("bd_lofric", "!=", False)])

    product_id7 = fields.Many2one(
        "crm.tag",
        string="Produit concurent")

    product_id8 = fields.Many2one(
        "crm.tag",
        string="Produit concurent")

    product_qty2 = fields.Float(
        string="Quantité récupérée"
    )
    pharmacie = fields.Char(
        string="Pharmacie concurrente",
        store=True,
        readonly=False)
    pharmacie2 = fields.Char(
        string="Pharmacie concurrente",
        store=True,
        readonly=False)
    pharmacie_id = fields.Many2one(
        "res.partner",
        string="Pharmacie",
        domain=[('is_pharmacie', '=', True)]
    )
    pharmacie_id2 = fields.Many2one(
        "res.partner",
        string="Pharmacie",
        domain=[('is_pharmacie', '=', True)]
    )


    # fonction pour déclancher la creation d'activité si un call et crée avec un date récup set

    # @api.model
    # def create(self, vals):
    #     """Override the create method to trigger activity creation automatically when a call is created with date_recup."""
    #     record = super(HistoriqueAppels, self).create(vals)
    #
    #     # Check if the 'date_recup' field is set, and if so, call the action_create_activity method in crm.lead
    #     if record.date_recup:
    #         record.crm_id.action_create_activity()
    #
    #     return record









