# -*- coding: utf-8 -*-
{
    'name': 'Partner Blacklist',

    'summary': """
        Add blacklist functionality to partners""",

    'description': """
        This module allows you to blacklist partners.
        When a blacklisted partner is selected in a sale order,
        the confirmation will be blocked.
    """,

    'author': "Mohamed LAHRECH",
    'website': "https://www.linkedin.com/in/mohamed-lahrech-787936172/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '16.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale_management', 'sales_team'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
