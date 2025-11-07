# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import calendar


class ResPartner(models.Model):
    _inherit = 'res.partner'

    potential = fields.Selection([
        ('potentiel_a', 'Potentiel A'),
        ('potentiel_b', 'Potentiel B'),
        ('potentiel_c', 'Potentiel C'),
    ], string='Potential', help='Partner potential level')

    region = fields.Selection([
        ('centre', 'Centre'),
        ('est', 'Est'),
        ('sud', 'Sud'),
        ('ouest', 'Ouest'),
    ], string='Région', help='Région géographique du partenaire')

    responsible_delegue = fields.Many2one(
        'res.users',
        string='Délégué responsable',
        help='Utilisateur responsable de ce partenaire'
    )

    frequence_visite = fields.Integer(
        string='Fréquence de visite',
        help='Fréquence de visite prévue pour ce partenaire'
    )

    monthly_visits_count = fields.Integer(
        string='Visites ce mois',
        compute='_compute_monthly_visits_count',
        help='Nombre de visites planifiées ce mois par le délégué responsable'
    )

    @api.depends('responsible_delegue')
    def _compute_monthly_visits_count(self):
        """Compute the number of project.task records for this month where:
        - partner_id matches this partner
        - planned_date_begin is in current month/year
        - user_ids contains the responsible_delegue
        """
        for partner in self:
            count = 0
            if partner.responsible_delegue:
                # Get current month and year
                now = datetime.now()
                month_start = datetime(now.year, now.month, 1)
                # Get last day of current month
                last_day = calendar.monthrange(now.year, now.month)[1]
                month_end = datetime(now.year, now.month, last_day, 23, 59, 59)
                
                # Search for project.task records
                tasks = self.env['project.task'].search([
                    ('partner_id', '=', partner.id),
                    ('planned_date_begin', '>=', month_start),
                    ('planned_date_begin', '<=', month_end),
                    ('user_ids', 'in', [partner.responsible_delegue.id])
                ])
                count = len(tasks)
            
            partner.monthly_visits_count = count

    def action_partner_navigate(self):
        self.ensure_one()
        if not self.partner_latitude or not self.partner_longitude:
            self.geo_localize()
        url = "https://www.google.com/maps/dir/?api=1&destination=%s,%s" % (self.partner_latitude, self.partner_longitude)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new'
        }

