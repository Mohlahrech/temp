{
    "name": "Main Menu Animated",
    "version": "1.1.0",
    "summary": "Enhanced animated navigation module for Odoo V18 Community Edition.",
    "description": """
        This module provides a centralized and animated main menu for Odoo Community Edition, allowing users to quickly access core modules and enhance their workflow. 
        It features widget functionality for displaying the current date and posting announcements, which can be managed by administrators. 
        Users can create bookmarks for quick access to essential menus, as well as external links, improving overall navigation efficiency.
    """,
     'author': "RAG Solutions",
     'website': "https://www.linkedin.com/in/mohamed-lahrech-787936172/",
     'category': 'Sales/Sales',
     'version': '18.0.1.0.0',
     'license': 'LGPL-3',

    "category": "Technical/Technical",
    "depends": [
        "web",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/main_menu_views.xml",
        "views/menu_bookmark_views.xml",
        "views/res_config_setting_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "main_menu_animated/static/src/components/**/*",
            "main_menu_animated/static/src/webclient/**/*",
        ],
    },
    "images": [
        "static/description/banner.png",
    ],
    "auto_install": True,
    "application": True,
    "installable": True,
}
