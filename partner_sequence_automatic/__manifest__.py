# -*- coding: utf-8 -*-
# module template
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Partner Sequence',
    'version': '16.0',
    'category': 'Base',
    'license': 'AGPL-3',
    'author': "Mohamed LAHRECH",
    'website': 'https://www.linkedin.com/in/mohamed-lahrech-787936172/',
    'depends': ['base','crm',
                ],

    'images': ['images/main_screenshot.png'],
    'data': [
              'security/ir.model.access.csv',
             'data/res_partner_sequence.xml',
             'views/hopitaux.xml',
             'views/crm.xml',
              'views/sécurité_sociale.xml',
             'views/pharmacy.xml',
              'views/res_partner.xml',
             'views/call_list.xml',
              'views/product.xml',
              #'views/res_users.xml',
             ],
    'installable': True,
    'application': True,
}
