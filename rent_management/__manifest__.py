# -*- coding: utf-8 -*-
{
    'name' : 'Rent CAR / BIKE Management',

    'summary': """
        Complete rental management solution for cars and motorcycles with automated tracking and contract handling.""",

    'description': """
              This module provides a fully integrated system for managing vehicle rentals, covering everything from contract creation to tracking returns. It automates notifications for overdue rentals, handles contract extensions, and ensures compliance with return deadlines. The system includes automatic calendar integration to follow contract durations and scheduled returns while also allowing users to generate printable contracts. Access controls and user restrictions ensure that only authorized personnel can modify or validate key rental operations. Designed for both single and multi-company environments, this module is a complete, ready-to-use solution for efficient rental management. 
    """,

    'author': "RAG Solutions",
    'price': 60.00,
    'currency': 'EUR',
    'website': "https://www.linkedin.com/in/mohamed-lahrech-787936172/",
    'category': 'Industries',
    'version': '18.0.1.0.0',
    'license': 'LGPL-3',
    'depends' : ['sale','account','contacts','calendar'],
    'data': [
        'data/rent_maintenance_data.xml',
        'security/ir_rule.xml',
        'security/ir.model.access.csv',
        'security/groups.xml',
        'views/sale_order_tree.xml',
        'views/menu_assurance.xml',
        'views/partner_view.xml',
        'views/menus.xml',
        'views/dashboard_views.xml',
        'views/view_vehicules.xml',   
        'views/sale_order_form.xml',
        'views/account_move.xml',
        'views/historique_maintenance_views.xml',
        'views/rent_maintenance_views.xml',
        'report/format_paper.xml',
        'report/internal_layout.xml',
        'report/crm_team.xml',
        'views/product_template_views.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'rent_management/static/src/js/rental_dashboard.js',
            'rent_management/static/src/css/rental_dashboard.css',
            'rent_management/static/src/xml/rental_dashboard_templates.xml',
        ],
    },
    'demo': [
    ],
    'qweb': [
    ],

    'images': [
            'static/description/banner.gif'
    ],


    'installable': True,
    'application': True,
}
