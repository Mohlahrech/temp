# -*- coding: utf-8 -*-
# from odoo import http


# class BlacklistPartner(http.Controller):
#     @http.route('/blacklist_partner/blacklist_partner', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/blacklist_partner/blacklist_partner/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('blacklist_partner.listing', {
#             'root': '/blacklist_partner/blacklist_partner',
#             'objects': http.request.env['blacklist_partner.blacklist_partner'].search([]),
#         })

#     @http.route('/blacklist_partner/blacklist_partner/objects/<model("blacklist_partner.blacklist_partner"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('blacklist_partner.object', {
#             'object': obj
#         })
