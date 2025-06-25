# -*- coding: utf-8 -*-
{
    "name": "Security User Roles",
    "version": "16.0.1.0",
    "category": "Extra Tools",
    "author": "faOtools",
    "website": "https://faotools.com/apps/16.0/security-user-roles-734",
    "license": "Other proprietary",
    "application": True,
    "installable": True,
    "auto_install": False,
    "depends": [
        "base"
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/data.xml",
        "data/cron.xml",
        "views/res_users.xml",
        "views/security_role.xml"
    ],
    "assets": {},
    "demo": [
        
    ],
    "external_dependencies": {},
    "summary": "800_Secuirty_user_roles_R_D_R16.0.1.0_R31-5-2023 Group access management ",
    "description": """For the full details look at static/description/index.html
* Features * 
- Temporary user blocking and activation
#odootools_proprietary""",
    "images": [
        "static/description/main.png"
    ],
    "price": "36.0",
    "currency": "EUR",
    "post_init_hook": "post_init_hook",
    "live_test_url": "https://faotools.com/my/tickets/newticket?&url_app_id=99&ticket_version=16.0&url_type_id=3",
}
