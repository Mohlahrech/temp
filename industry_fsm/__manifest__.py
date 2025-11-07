# -*- coding: utf-8 -*-
{
    'name': "Planning délégués",
    'summary': "Schedule and track onsite operations, time and material",
    'description': """
Field Services Management
=========================
This module adds the features needed for a modern Field service management.
It installs the following apps:
- Project
- Timesheet

Adds the following options:
- reports on tasks
- FSM app with custom view for onsite worker
- add products on tasks

    """,
    'category': 'Services/Field Service',
    'sequence': 170,
    'version': '1.0',
    'depends': ['timesheet_grid', 'base_geolocalize', 'mail'],
    'data': [
        'report/worksheet_custom_report_templates.xml',
        'report/worksheet_custom_reports.xml',
        'data/fsm_data.xml',
        'data/fsm_dashboard_data.xml',
        'data/fsm_manager_dashboard_data.xml',
        'data/fsm_kpi_dashboard_data.xml',
        'data/mail_template_data.xml',
        'security/fsm_security.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'report/project_report_views.xml',
        'views/hr_timesheet_views.xml',
        'views/fsm_dashboard_wizard_views.xml',
        'views/fsm_kpi_dashboard_filter_views.xml',
        'views/fsm_kpi_dashboard_views.xml',
        'views/fsm_dashboard_views.xml',
        'views/fsm_views.xml',
        'views/fsm_alert_views.xml',
        'views/fsm_manager_views.xml',
        'views/temp_partner_views.xml',
        'views/project_task_views.xml',
        'views/res_partner_views.xml',
        'views/res_users_views.xml',
        'views/project_sharing_views.xml',
        'views/project_portal_templates.xml',
        'wizard/task_stop_timer_wizard_views.xml'
    ],
    'application': True,
    'demo': ['data/fsm_demo.xml'],
    'post_init_hook': 'create_field_service_project',
    'assets': {
        'web.assets_backend': [
            'industry_fsm/static/src/**/*',
        ],
        'web.assets_frontend': [
            'industry_fsm/static/src/js/tours/**/*',
        ],
    },

}
