# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _description = 'Partner Blacklist'

    is_blacklisted = fields.Boolean(
        string='Blacklisted',
        default=False,
        tracking=True,
        store=True,
        groups="blacklist_partner.group_blacklist_user",
        help='Check this box to mark the partner as blacklisted. '
             'Sales orders cannot be confirmed for blacklisted customers.'
    )

    def action_blacklist_partner(self):
        self.ensure_one()
        if not self.env.user.has_group('blacklist_partner.group_blacklist_manager'):
            raise AccessError(_('Only Blacklist Managers can blacklist partners.'))

        _logger.info("Attempting to blacklist partner: %s (ID: %s)", self.name, self.id)
        try:
            self.write({'is_blacklisted': True})
            self.env.cr.commit()
            _logger.info("Successfully blacklisted partner: %s", self.name)
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        except Exception as e:
            _logger.error("Failed to blacklist partner: %s. Error: %s", self.name, str(e))
            raise UserError(_('Failed to blacklist partner. Please try again.'))

    def action_unblacklist_partner(self):
        self.ensure_one()
        if not self.env.user.has_group('blacklist_partner.group_blacklist_manager'):
            raise AccessError(_('Only Blacklist Managers can remove partners from blacklist.'))

        _logger.info("Attempting to remove partner from blacklist: %s (ID: %s)", self.name, self.id)
        try:
            self.write({'is_blacklisted': False})
            self.env.cr.commit()
            _logger.info("Successfully removed partner from blacklist: %s", self.name)
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        except Exception as e:
            _logger.error("Failed to remove partner from blacklist: %s. Error: %s", self.name, str(e))
            raise UserError(_('Failed to remove partner from blacklist. Please try again.'))


class SaleOrder(models.Model):
    _inherit = 'account.move'

    @api.constrains('partner_id')
    def _check_partner_blacklist(self):
        for order in self:
            if order.partner_id.is_blacklisted:
                raise UserError(_(
                    'Ce contact (%s) a été blacklisté.'
                    'Vous ne pouvez pas crée de factures pour un contact blacklisté (Veuillez demander à Sofiane).'
                ) % order.partner_id.name)
