# -*- coding: utf-8 -*-

from datetime import timedelta, datetime
import pytz
from collections import defaultdict
from pytz import utc, timezone
from dateutil.relativedelta import relativedelta

from odoo import Command, fields, models, api, _
from odoo.osv import expression


from odoo import Command, fields, models, api, _, _lt
from odoo.exceptions import UserError
from odoo.tools import topological_sort

from odoo.addons.resource.models.resource import Intervals, sum_intervals, string_to_datetime


PROJECT_TASK_WRITABLE_FIELDS = {
    'planned_date_begin',
    'planned_date_end',
}



class Task(models.Model):
    _inherit = "project.task"

    # Override name field to set default value for sequence
    name = fields.Char(
        string='Title',
        required=True,
        index=True,
        default=lambda self: _('New')
    )

    # Related field to display partner function
    partner_function = fields.Char(
        string='Partner Function',
        related='partner_id.function',
        readonly=True,
        store=False
    )

    # Related field to display and edit partner potential
    partner_potential = fields.Selection([
        ('potentiel_a', 'Potentiel A'),
        ('potentiel_b', 'Potentiel B'),
        ('potentiel_c', 'Potentiel C'),
    ], string='Partner Potential', 
       related='partner_id.potential',
       readonly=False,
       store=False)

    # Related field to display partner phone
    partner_phone = fields.Char(
        string='Partner Phone',
        related='partner_id.phone',
        readonly=True,
        store=False
    )

    # Related field to display and edit partner region
    partner_region = fields.Selection([
        ('centre', 'Centre'),
        ('est', 'Est'),
        ('sud', 'Sud'),
        ('ouest', 'Ouest'),
    ], string='Partner Region', 
       related='partner_id.region',
       readonly=False,
       store=False)

    # Related field to get stage fold status for tree view decorations
    stage_fold = fields.Boolean(
        string='Stage Folded',
        related='stage_id.fold',
        readonly=True,
        store=False
    )

    # Three new Html fields for visit management
    objet_visite = fields.Html(
        string='Objet de la visite',
        help='Décrivez l\'objectif et le contexte de cette visite'
    )
    
    compte_rendu = fields.Html(
        string='Ce qui s\'est passé durant la visite',
        help='Détaillez ce qui s\'est déroulé pendant la visite'
    )
    
    objectif_prochaine = fields.Html(
        string='Objectif de la prochaine visite',
        help='Définissez les objectifs pour la prochaine visite'
    )

    # Computed fields for visit alerts
    visite_alert_message = fields.Char(
        string='Visit Alert Message',
        compute='_compute_visite_alert',
        help='Alert message based on monthly visit count vs frequency'
    )
    
    visite_alert_status = fields.Selection([
        ('danger', 'Danger'),
        ('success', 'Success'),
        ('none', 'None')
    ], string='Visit Alert Status',
       compute='_compute_visite_alert',
       help='Status of the visit alert for styling purposes')

    # Computed field to check if partner creation request exists
    has_pending_partner_request = fields.Boolean(
        string='Has Pending Partner Request',
        compute='_compute_has_pending_partner_request',
        help='True if there is already a pending partner creation request for this task'
    )

    # Field for partner creation warning display
    partner_creation_warning = fields.Char(
        string='Partner Creation Warning',
        compute='_compute_partner_creation_warning',
        help='Warning message when partner creation is pending'
    )

    # Boolean field to control warning visibility
    show_partner_creation_warning = fields.Boolean(
        string='Show Partner Creation Warning',
        compute='_compute_partner_creation_warning',
        help='True when partner creation warning should be displayed'
    )

    # Boolean field to track rejected partner creation requests
    has_rejected_partner_request = fields.Boolean(
        string='Has Rejected Partner Request',
        compute='_compute_partner_creation_warning',
        help='True if there is a rejected partner creation request for this task'
    )

    @api.model
    def default_get(self, fields_list):
        result = super(Task, self).default_get(fields_list)
        is_fsm_mode = self._context.get('fsm_mode')
        
        # Set default project_id
        if 'project_id' in fields_list and not result.get('project_id'):
            # Check if a default project_id is provided in context (from FSM action)
            context_project_id = self.env.context.get('default_project_id')
            if context_project_id and is_fsm_mode:
                result['project_id'] = context_project_id
                # Set default stage for this project
                result['stage_id'] = self.stage_find(context_project_id, [('fold', '=', False)])
            elif is_fsm_mode:
                # Fallback to finding FSM project dynamically
                company_id = self.env.context.get('default_company_id') or self.env.company.id
                fsm_project = self.env['project.project'].search([('is_fsm', '=', True), ('company_id', '=', company_id)], order='sequence', limit=1)
                if fsm_project:
                    result['stage_id'] = self.stage_find(fsm_project.id, [('fold', '=', False)])
                    result['project_id'] = fsm_project.id
            else:
                # Set default project_id to the project with name "Visite délégués"
                project = self.env['project.project'].search([('name', '=', "Visite délégués")], limit=1)
                if project:
                    result['project_id'] = project.id

        date_begin = result.get('planned_date_begin')
        date_end = result.get('planned_date_end')
        if is_fsm_mode and (date_begin or date_end):
            if not date_begin:
                date_begin = date_end.replace(hour=0, minute=0, second=1)
            if not date_end:
                date_end = date_begin.replace(hour=23, minute=59, second=59)
            date_diff = date_end - date_begin
            if date_diff.seconds / 3600 > 23.5:
                # if the interval between both dates are more than 23 hours and 30 minutes
                # then we changes those dates to fit with the working schedule of the assigned user or the current company
                # because we assume here, the planned dates are not the ones chosen by the current user.
                user_tz = pytz.timezone(self.env.context.get('tz') or 'UTC')
                date_begin = pytz.utc.localize(date_begin).astimezone(user_tz)
                date_end = pytz.utc.localize(date_end).astimezone(user_tz)
                user_ids_list = [res[2] for res in result.get('user_ids', []) if len(res) == 3 and res[0] == Command.SET]  # user_ids = [(Command.SET, 0, <user_ids>)]
                user_ids = user_ids_list[-1] if user_ids_list else []
                users = self.env['res.users'].sudo().browse(user_ids)
                user = len(users) == 1 and users
                if user and user.employee_id:  # then the default start/end hours correspond to what is configured on the employee calendar
                    resource_calendar = user.resource_calendar_id
                else:  # Otherwise, the default start/end hours correspond to what is configured on the company calendar
                    company = self.env['res.company'].sudo().browse(result.get('company_id')) if result.get(
                        'company_id') else self.env.user.company_id
                    resource_calendar = company.resource_calendar_id
                if resource_calendar:
                    resources_work_intervals = resource_calendar._work_intervals_batch(date_begin, date_end)
                    work_intervals = [(start, stop) for start, stop, meta in resources_work_intervals[False]]
                    if work_intervals:
                        planned_date_begin = work_intervals[0][0]
                        planned_date_end = work_intervals[0][1]
                        for dummy, stop in work_intervals[1:]:
                            if stop.date() != planned_date_begin.date():  # when it is no longer the case we keep the previous stop date.
                                break
                            planned_date_end = stop
                        result['planned_date_begin'] = planned_date_begin.astimezone(pytz.utc).replace(tzinfo=None)
                        result['planned_date_end'] = planned_date_end.astimezone(pytz.utc).replace(tzinfo=None)
                else:
                    result['planned_date_begin'] = date_begin.replace(hour=9, minute=0, second=1).astimezone(pytz.utc).replace(tzinfo=None)
                    result['planned_date_end'] = date_end.astimezone(pytz.utc).replace(tzinfo=None)
        return result

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-populate objet_visite from previous record's objectif_prochaine and validate stage_id"""
        for vals in vals_list:
            # Set default name using sequence if not provided
            if vals.get('name', _('New')) == _('New'):
                # Try to get sequence
                sequence = self.env['ir.sequence'].search([('code', '=', 'project.task.visite')], limit=1)
                if sequence:
                    sequence_name = sequence._next()
                    vals['name'] = sequence_name
                else:
                    # Create sequence if it doesn't exist
                    sequence = self.env['ir.sequence'].create({
                        'name': 'Visite Task Sequence',
                        'code': 'project.task.visite',
                        'prefix': 'Visite ',
                        'padding': 2,
                        'company_id': False,
                    })
                    sequence_name = sequence._next()
                    vals['name'] = sequence_name
            
            # Validate that stage_id is defined
            if not vals.get('stage_id'):
                raise UserError(_('Vauillez atribuer un statut à cette visite.'))
        
        for vals in vals_list:
            partner_id = vals.get('partner_id')
            if partner_id and not vals.get('objet_visite'):
                # Find the latest previous record with the same partner_id
                previous_task = self.search([
                    ('partner_id', '=', partner_id)
                ], order='create_date desc', limit=1)
                
                if previous_task and previous_task.objectif_prochaine:
                    # Populate objet_visite with the previous task's objectif_prochaine
                    # This preserves HTML content including tables and formatting
                    vals['objet_visite'] = previous_task.objectif_prochaine
        
        return super().create(vals_list)

    @api.depends('partner_id.monthly_visits_count', 'partner_id.frequence_visite')
    def _compute_visite_alert(self):
        """Compute visit alert message and status based on monthly visits vs frequency"""
        for task in self:
            if not task.partner_id:
                task.visite_alert_message = False
                task.visite_alert_status = 'none'
                continue
                
            monthly_count = task.partner_id.monthly_visits_count or 0
            frequency = task.partner_id.frequence_visite or 0
            
            if frequency == 0:
                # No frequency set, no alert needed
                task.visite_alert_message = False
                task.visite_alert_status = 'none'
            elif monthly_count < frequency:
                # Still needs visits
                remaining = frequency - monthly_count
                task.visite_alert_message = f"⚠ Attention, {remaining} visites de plus sont nécessaires ce mois"
                task.visite_alert_status = 'danger'
            else:
                # Target reached or exceeded
                task.visite_alert_message = "✔ Nombre de visites mensuelles atteint"
                task.visite_alert_status = 'success'

    def _compute_has_pending_partner_request(self):
        """Check if there's already a pending partner creation request for this task"""
        for task in self:
            if not task._origin.id:
                task.has_pending_partner_request = False
                continue
                
            # Check if there's a pending temp partner request for this task
            pending_request = self.env['temp.partner'].search([
                ('task_id', '=', task._origin.id),
                ('state', '=', 'pending')
            ], limit=1)
            
            task.has_pending_partner_request = bool(pending_request)

    @api.depends('partner_id')
    def _compute_partner_creation_warning(self):
        """Compute the partner creation warning message and visibility"""
        for task in self:
            if not task._origin.id:
                task.partner_creation_warning = False
                task.show_partner_creation_warning = False
                task.has_rejected_partner_request = False
                continue
                
            # Check if there's a pending temp partner request for this task
            pending_request = self.env['temp.partner'].search([
                ('task_id', '=', task._origin.id),
                ('state', '=', 'pending')
            ], limit=1)
            
            # Check if there's a rejected temp partner request for this task
            rejected_request = self.env['temp.partner'].search([
                ('task_id', '=', task._origin.id),
                ('state', '=', 'rejected')
            ], limit=1)
            
            if pending_request:
                task.partner_creation_warning = "Cette visite est bloquée en attendant la création du contact par Adel"
                task.show_partner_creation_warning = True
                task.has_rejected_partner_request = False
            elif rejected_request and not task.partner_id:
                # Only show rejected message if no partner is selected
                task.partner_creation_warning = "La demande de création du contact a été rejetée, ce contact existe déjà dans la liste"
                task.show_partner_creation_warning = True
                task.has_rejected_partner_request = True
            else:
                task.partner_creation_warning = False
                task.show_partner_creation_warning = False
                task.has_rejected_partner_request = False

    def action_open_patient_page(self):
        """Open the /patient page from the website"""
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        patient_url = f"{base_url}/patient"
        return {
            'type': 'ir.actions.act_url',
            'url': patient_url,
            'target': 'new',
        }

    def action_request_partner_creation(self):
        """Open wizard to request partner creation"""
        self.ensure_one()
        
        # Validate that planned_date_begin and planned_date_end are filled
        if not self.planned_date_begin or not self.planned_date_end:
            raise UserError(_('Veuillez ajouter la date de début et la date de fin, avant de continuer'))
        
        return {
            'name': _('Demander création partenaire'),
            'type': 'ir.actions.act_window',
            'res_model': 'partner.creation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_task_id': self.id},
        }

    allow_worksheets = fields.Boolean(related='project_id.allow_worksheets')
    is_fsm = fields.Boolean(related='project_id.is_fsm', search='_search_is_fsm')
    fsm_done = fields.Boolean("Task Done", compute='_compute_fsm_done', readonly=False, store=True, copy=False)
    partner_id = fields.Many2one(group_expand='_read_group_partner_id')
    project_id = fields.Many2one(group_expand='_read_group_project_id')
    user_ids = fields.Many2many(group_expand='_read_group_user_ids')
    # Use to count conditions between : time, worksheet and materials
    # If 2 over 3 are enabled for the project, the required count = 2
    # If 1 over 3 is met (enabled + encoded), the satisfied count = 2
    display_enabled_conditions_count = fields.Integer(compute='_compute_display_conditions_count')
    display_satisfied_conditions_count = fields.Integer(compute='_compute_display_conditions_count')
    display_mark_as_done_primary = fields.Boolean(compute='_compute_mark_as_done_buttons')
    display_mark_as_done_secondary = fields.Boolean(compute='_compute_mark_as_done_buttons')
    display_sign_report_primary = fields.Boolean(compute='_compute_display_sign_report_buttons')
    display_sign_report_secondary = fields.Boolean(compute='_compute_display_sign_report_buttons')
    display_send_report_primary = fields.Boolean(compute='_compute_display_send_report_buttons')
    display_send_report_secondary = fields.Boolean(compute='_compute_display_send_report_buttons')
    worksheet_signature = fields.Binary('Signature', copy=False, attachment=True)
    worksheet_signed_by = fields.Char('Signed By', copy=False)
    fsm_is_sent = fields.Boolean('Is Worksheet sent', readonly=True)
    comment = fields.Html(string='Comments', copy=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS | {'allow_worksheets',
                                              'is_fsm',
                                              'planned_date_begin',
                                              'planned_date_end',
                                              'fsm_done',
                                              'partner_phone',
                                              'partner_city',}

    @api.depends(
        'fsm_done', 'is_fsm', 'timer_start',
        'display_enabled_conditions_count', 'display_satisfied_conditions_count')
    def _compute_mark_as_done_buttons(self):
        for task in self:
            primary, secondary = True, True
            if task.fsm_done or not task.is_fsm or task.timer_start:
                primary, secondary = False, False
            else:
                if task.display_enabled_conditions_count == task.display_satisfied_conditions_count:
                    secondary = False
                else:
                    primary = False
            task.update({
                'display_mark_as_done_primary': primary,
                'display_mark_as_done_secondary': secondary,
            })

    @api.depends('allow_worksheets', 'project_id.allow_timesheets', 'total_hours_spent', 'comment')
    def _compute_display_conditions_count(self):
        for task in self:
            enabled = 1 if task.project_id.allow_timesheets else 0
            satisfied = 1 if enabled and task.total_hours_spent else 0
            enabled += 1 if task.allow_worksheets else 0
            satisfied += 1 if task.allow_worksheets and task.comment else 0
            task.update({
                'display_enabled_conditions_count': enabled,
                'display_satisfied_conditions_count': satisfied
            })

    @api.depends('fsm_done', 'display_timesheet_timer', 'timer_start', 'total_hours_spent')
    def _compute_display_timer_buttons(self):
        fsm_done_tasks = self.filtered(lambda task: task.fsm_done)
        fsm_done_tasks.update({
            'display_timer_start_primary': False,
            'display_timer_start_secondary': False,
            'display_timer_stop': False,
            'display_timer_pause': False,
            'display_timer_resume': False,
        })
        super(Task, self - fsm_done_tasks)._compute_display_timer_buttons()

    def _hide_sign_button(self):
        self.ensure_one()
        return not self.allow_worksheets or self.timer_start or self.worksheet_signature \
            or not self.display_satisfied_conditions_count

    @api.depends(
        'allow_worksheets', 'timer_start', 'worksheet_signature',
        'display_satisfied_conditions_count', 'display_enabled_conditions_count')
    def _compute_display_sign_report_buttons(self):
        for task in self:
            sign_p, sign_s = True, True
            if task._hide_sign_button():
                sign_p, sign_s = False, False
            else:
                if task.display_enabled_conditions_count == task.display_satisfied_conditions_count:
                    sign_s = False
                else:
                    sign_p = False
            task.update({
                'display_sign_report_primary': sign_p,
                'display_sign_report_secondary': sign_s,
            })

    def _hide_send_report_button(self):
        self.ensure_one()
        return not self.allow_worksheets or self.timer_start or not self.display_satisfied_conditions_count \
            or self.fsm_is_sent

    @api.depends(
        'allow_worksheets', 'timer_start',
        'display_satisfied_conditions_count', 'display_enabled_conditions_count',
        'fsm_is_sent')
    def _compute_display_send_report_buttons(self):
        for task in self:
            send_p, send_s = True, True
            if task._hide_send_report_button():
                send_p, send_s = False, False
            else:
                if task.display_enabled_conditions_count == task.display_satisfied_conditions_count:
                    send_s = False
                else:
                    send_p = False
            task.update({
                'display_send_report_primary': send_p,
                'display_send_report_secondary': send_s,
            })

    @api.model
    def _search_is_fsm(self, operator, value):
        query = """
            SELECT p.id
            FROM project_project P
            WHERE P.active = 't' AND P.is_fsm
        """
        operator_new = operator == "=" and "inselect" or "not inselect"
        return [('project_id', operator_new, (query, ()))]

    @api.model
    def _read_group_partner_id(self, partners, domain, order):
        if self._context.get('fsm_mode'):
            dom_tuples = [dom for dom in domain if isinstance(dom, (list, tuple)) and len(dom) == 3]
            if any(d[0] == 'partner_id' and d[1] in ('=', 'ilike', 'child_of') for d in dom_tuples):
                filter_domain = self._expand_domain_m2o_groupby(dom_tuples, 'partner_id')
                return self.env['res.partner'].search(filter_domain, order=order)
        return partners

    @api.model
    def _read_group_project_id(self, projects, domain, order):
        if self._context.get('fsm_mode'):
            dom_tuples = [dom for dom in domain if isinstance(dom, (list, tuple)) and len(dom) == 3]
            if any(d[0] == 'project_id' and d[1] in ('=', 'ilike') for d in dom_tuples):
                filter_domain = self._expand_domain_m2o_groupby(dom_tuples, 'project_id')
                domain = expression.AND([filter_domain, [('is_fsm', '=', True)]])
                return self.env['project.project'].search(domain, order=order)
        return projects

    @api.model
    def _expand_domain_m2o_groupby(self, domain, filter_field):
        filter_domain = []
        for dom in domain:
            if dom[0] == filter_field:
                field = self._fields[dom[0]]
                if field.type == 'many2one' and len(dom) == 3:
                    if dom[1] == '=':
                        filter_domain = expression.OR([filter_domain, [('id', dom[1], dom[2])]])
                    elif dom[1] == 'ilike':
                        rec_name = self.env[field.comodel_name]._rec_name
                        filter_domain = expression.OR([filter_domain, [(rec_name, dom[1], dom[2])]])
                    elif dom[1] == 'child_of':
                        rec_name = self.env[field.comodel_name]._rec_name
                        filter_domain = expression.OR([filter_domain, [(rec_name, 'ilike', dom[2])]])
        return filter_domain

    @api.model
    def _read_group_user_ids(self, users, domain, order):
        if self.env.context.get('fsm_mode'):
            recently_created_tasks = self.env['project.task'].search([
                ('create_date', '>', datetime.now() - timedelta(days=30)),
                ('is_fsm', '=', True),
                ('user_ids', '!=', False)
            ])
            search_domain = ['&', ('company_id', 'in', self.env.companies.ids), '|', '|', ('id', 'in', users.ids), ('groups_id', 'in', self.env.ref('industry_fsm.group_fsm_user').id), ('id', 'in', recently_created_tasks.mapped('user_ids.id'))]
            return users.search(search_domain, order=order)
        return users

    def _compute_fsm_done(self):
        closed_tasks = self.filtered('is_closed')
        closed_tasks.fsm_done = True

    def action_fsm_worksheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'res_id': self.id,
            'view_mode': 'form',
            'context': {'form_view_initial_mode': 'edit', 'task_worksheet_comment': True},
            'views': [[self.env.ref('industry_fsm.fsm_form_view_comment').id, 'form']],
        }

    def action_view_timesheets(self):
        kanban_view = self.env.ref('hr_timesheet.view_kanban_account_analytic_line')
        form_view = self.env.ref('industry_fsm.timesheet_view_form')
        tree_view = self.env.ref('industry_fsm.timesheet_view_tree_user_inherit')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Time'),
            'res_model': 'account.analytic.line',
            'view_mode': 'list,form,kanban',
            'views': [(tree_view.id, 'list'), (kanban_view.id, 'kanban'), (form_view.id, 'form')],
            'domain': [('task_id', '=', self.id), ('project_id', '!=', False)],
            'context': {
                'fsm_mode': True,
                'default_project_id': self.project_id.id,
                'default_task_id': self.id,
            }
        }

    def action_fsm_validate(self, stop_running_timers=False):
        """ Moves Task to next stage.
            If allow billable on task, timesheet product set on project and user has privileges :
            Create SO confirmed with time and material.
        """
        # Validate that required fields are filled before validation
        for task in self:
            if not task.objet_visite or not task.objet_visite.strip() or \
               not task.compte_rendu or not task.compte_rendu.strip() or \
               not task.objectif_prochaine or not task.objectif_prochaine.strip():
                raise UserError(_('Veuillez remplir \'Objectif Visite\', \'Compte Rendu\', et \'Objectif Prochaine\' avant de continuer.'))
        
        Timer = self.env['timer.timer']
        tasks_running_timer_ids = Timer.search([('res_model', '=', 'project.task'), ('res_id', 'in', self.ids)])
        timesheets = self.env['account.analytic.line'].sudo().search([('task_id', 'in', self.ids)])
        timesheets_running_timer_ids = None
        if timesheets:
            timesheets_running_timer_ids = Timer.search([
                ('res_model', '=', 'account.analytic.line'),
                ('res_id', 'in', timesheets.ids)])
        if tasks_running_timer_ids or timesheets_running_timer_ids:
            if stop_running_timers:
                self._stop_all_timers_and_create_timesheets(tasks_running_timer_ids, timesheets_running_timer_ids, timesheets)
            else:
                wizard = self.env['project.task.stop.timers.wizard'].create({
                    'line_ids': [Command.create({'task_id': task.id}) for task in self],
                })
                return {
                    'name': _('Do you want to stop the running timers?'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'view_id': self.env.ref('industry_fsm.view_task_stop_timer_wizard_form').id,
                    'target': 'new',
                    'res_model': 'project.task.stop.timers.wizard',
                    'res_id': wizard.id,
                }

        closed_stage_by_project = {
            project.id:
                project.type_ids.filtered(lambda stage: stage.fold)[:1] or project.type_ids[-1:]
            for project in self.project_id
        }
        for task in self:
            # determine closed stage for task
            closed_stage = closed_stage_by_project.get(self.project_id.id)
            values = {'fsm_done': True}
            if closed_stage:
                values['stage_id'] = closed_stage.id

            task.write(values)

        return True

    @api.model
    def _stop_all_timers_and_create_timesheets(self, tasks_running_timer_ids, timesheets_running_timer_ids, timesheets):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        Timesheet = self.env['account.analytic.line']

        if not tasks_running_timer_ids and not timesheets_running_timer_ids:
            return Timesheet

        result = Timesheet
        minimum_duration = int(ConfigParameter.get_param('timesheet_grid.timesheet_min_duration', 0))
        rounding = int(ConfigParameter.get_param('timesheet_grid.timesheet_rounding', 0))
        if tasks_running_timer_ids:
            task_dict = {task.id: task for task in self}
            timesheets_vals = []
            for timer in tasks_running_timer_ids:
                minutes_spent = timer._get_minutes_spent()
                time_spent = self._timer_rounding(minutes_spent, minimum_duration, rounding) / 60
                task = task_dict[timer.res_id]
                timesheets_vals.append({
                    'task_id': task.id,
                    'project_id': task.project_id.id,
                    'user_id': timer.user_id.id,
                    'unit_amount': time_spent,
                })
            tasks_running_timer_ids.sudo().unlink()
            result += Timesheet.sudo().create(timesheets_vals)

        if timesheets_running_timer_ids:
            timesheets_dict = {timesheet.id: timesheet for timesheet in timesheets}
            for timer in timesheets_running_timer_ids:
                timesheet = timesheets_dict[timer.res_id]
                minutes_spent = timer._get_minutes_spent()
                timesheet._add_timesheet_time(minutes_spent)
                result += timesheet
            timesheets_running_timer_ids.sudo().unlink()

        return result

    def action_fsm_navigate(self):
        if not self.partner_id.city or not self.partner_id.country_id:
            return {
                'name': _('Customer'),
                'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'res_id': self.partner_id.id,
                'view_mode': 'form',
                'view_id': self.env.ref('industry_fsm.view_partner_address_form_industry_fsm').id,
                'target': 'new',
            }
        return self.partner_id.action_partner_navigate()

    def action_preview_worksheet(self):
        self.ensure_one()
        source = 'fsm' if self._context.get('fsm_mode', False) else 'project'
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(query_string=f'&source={source}')
        }

    def action_send_report(self):
        tasks_with_report = self.filtered(lambda task: task._is_fsm_report_available())
        if not tasks_with_report:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("There are no reports to send."),
                    'sticky': False,
                    'type': 'danger',
                }
            }

        template_id = self.env.ref('industry_fsm.mail_template_data_task_report').id
        return {
            'name': _("Send report"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': {
                'default_composition_mode': 'mass_mail' if len(tasks_with_report.ids) > 1 else 'comment',
                'default_model': 'project.task',
                'default_res_id': tasks_with_report.ids[0],
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'fsm_mark_as_sent': True,
                'active_ids': tasks_with_report.ids,
            },
        }

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Worksheet %s - %s' % (self.name, self.partner_id.name)

    def _is_fsm_report_available(self):
        self.ensure_one()
        return self.comment or self.timesheet_ids

    def has_to_be_signed(self):
        self.ensure_one()
        return self._is_fsm_report_available() and not self.worksheet_signature

    @api.model
    def get_views(self, views, options=None):
        options['toolbar'] = not self._context.get('task_worksheet_comment') and options.get('toolbar')
        res = super().get_views(views, options)
        return res

    # ---------------------------------------------------------
    # Business Methods
    # ---------------------------------------------------------

    def _message_post_after_hook(self, message, msg_vals):
        if self.env.context.get('fsm_mark_as_sent') and not self.fsm_is_sent:
            self.fsm_is_sent = True
        return super()._message_post_after_hook(message, msg_vals)





    planned_date_begin = fields.Datetime("Start date", tracking=True, task_dependency_tracking=True)
    planned_date_end = fields.Datetime("End date", tracking=True, task_dependency_tracking=True)
    partner_mobile = fields.Char(related='partner_id.mobile', readonly=False)
    partner_zip = fields.Char(related='partner_id.zip', readonly=False)
    partner_street = fields.Char(related='partner_id.street', readonly=False)
    project_color = fields.Integer('Project color', related='project_id.color')

    # Task Dependencies fields
    display_warning_dependency_in_gantt = fields.Boolean(compute="_compute_display_warning_dependency_in_gantt")
    planning_overlap = fields.Integer(compute='_compute_planning_overlap', search='_search_planning_overlap')
    overlap_warning = fields.Char(compute='_compute_planning_overlap')

    # User names in popovers
    user_names = fields.Char(compute='_compute_user_names')

    # Allocated hours
    allocated_hours = fields.Float("Allocated Hours", compute='_compute_allocated_hours', store=True)
    allocation_type = fields.Selection([
        ('working_hours', 'Working Hours'),
        ('duration', 'Duration'),
    ], default='duration', compute='_compute_allocation_type')
    duration = fields.Float(compute='_compute_duration')

    _sql_constraints = [
        ('planned_dates_check', "CHECK ((planned_date_begin <= planned_date_end))", "The planned start date must be before the planned end date."),
    ]

    # action_gantt_reschedule utils
    _WEB_GANTT_RESCHEDULE_WORK_INTERVALS_CACHE_KEY = 'work_intervals'
    _WEB_GANTT_RESCHEDULE_RESOURCE_VALIDITY_CACHE_KEY = 'resource_validity'

    @property
    def SELF_WRITABLE_FIELDS(self):
        return super().SELF_WRITABLE_FIELDS | PROJECT_TASK_WRITABLE_FIELDS

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        planned_date_begin = result.get('planned_date_begin', self.env.context.get('planned_date_begin', False))
        planned_date_end = result.get('planned_date_end', self.env.context.get('planned_date_end', False))
        if planned_date_begin and planned_date_end and not self.env.context.get('fsm_mode', False):
            user_id = result.get('user_id', None)
            planned_date_begin, planned_date_end = self._calculate_planned_dates(planned_date_begin, planned_date_end, user_id)
            result.update(planned_date_begin=planned_date_begin, planned_date_end=planned_date_end)
        return result

    def action_unschedule_task(self):
        self.write({
            'planned_date_begin': False,
            'planned_date_end': False
        })

    @api.depends('stage_id')
    def _compute_display_warning_dependency_in_gantt(self):
        for task in self:
            task.display_warning_dependency_in_gantt = not task.is_closed

    def _get_planning_overlap_per_task(self):
        if not self.ids:
            return {}
        self.flush_model(['active', 'planned_date_begin', 'planned_date_end', 'user_ids', 'project_id', 'is_closed'])
        query = """
            SELECT T.id, COUNT(T2.id)
              FROM project_task T
        INNER JOIN project_task_user_rel U1 ON T.id = U1.task_id
        INNER JOIN project_task T2 ON T.id != T2.id
               AND T2.active = 't'
               And T2.is_closed IS FALSE
               AND T2.planned_date_begin IS NOT NULL
               AND T2.planned_date_end IS NOT NULL
               AND T2.planned_date_end > NOW()
               AND T2.project_id IS NOT NULL
               AND (T.planned_date_begin::TIMESTAMP, T.planned_date_end::TIMESTAMP)
          OVERLAPS (T2.planned_date_begin::TIMESTAMP, T2.planned_date_end::TIMESTAMP)
        INNER JOIN project_task_user_rel U2 ON T2.id = U2.task_id
               AND U2.user_id = U1.user_id
             WHERE T.id IN %s
               AND T.active = 't'
               And T.is_closed IS FALSE
               AND T.planned_date_begin IS NOT NULL
               AND T.planned_date_end IS NOT NULL
               AND T.planned_date_end > NOW()
               AND T.project_id IS NOT NULL
          GROUP BY T.id
        """
        self.env.cr.execute(query, (tuple(self.ids),))
        raw_data = self.env.cr.dictfetchall()
        return dict(map(lambda d: d.values(), raw_data))

    @api.depends('planned_date_begin', 'planned_date_end', 'user_ids')
    def _compute_planning_overlap(self):
        overlap_mapping = self._get_planning_overlap_per_task()
        if overlap_mapping:
            for task in self:
                overlaps = overlap_mapping.get(task.id, 0)
                task.planning_overlap = overlaps
                task.overlap_warning = _("%s other task(s) for the same employee at the same time.") % overlaps if overlaps else False
        else:
            self.planning_overlap = 0
            self.overlap_warning = False

    @api.model
    def _search_planning_overlap(self, operator, value):
        if operator not in ['=', '>'] or not isinstance(value, int) or value != 0:
            raise NotImplementedError(_('Operation not supported, you should always compare planning_overlap to 0 value with = or > operator.'))

        query = """
            SELECT T1.id
            FROM project_task T1
            INNER JOIN project_task T2 ON T1.id <> T2.id
            INNER JOIN project_task_user_rel U1 ON T1.id = U1.task_id
            INNER JOIN project_task_user_rel U2 ON T2.id = U2.task_id
                AND U1.user_id = U2.user_id
            WHERE
                T1.planned_date_begin < T2.planned_date_end
                AND T1.planned_date_end > T2.planned_date_begin
                AND T1.planned_date_begin IS NOT NULL
                AND T1.planned_date_end IS NOT NULL
                AND T1.planned_date_end > NOW()
                AND T1.active = 't'
                AND T1.is_closed IS FALSE
                AND T1.project_id IS NOT NULL
                AND T2.planned_date_begin IS NOT NULL
                AND T2.planned_date_end IS NOT NULL
                AND T2.planned_date_end > NOW()
                AND T2.project_id IS NOT NULL
                AND T2.active = 't'
                AND T2.is_closed IS FALSE
        """
        operator_new = (operator == ">") and "inselect" or "not inselect"
        return [('id', operator_new, (query, ()))]

    def _compute_user_names(self):
        for task in self:
            task.user_names = ', '.join(task.user_ids.mapped('name'))

    @api.depends('planned_date_begin', 'planned_date_end', 'company_id.resource_calendar_id', 'user_ids')
    def _compute_allocated_hours(self):
        task_working_hours = self.filtered(lambda s: s.allocation_type == 'working_hours' and (s.user_ids or s.company_id))
        task_duration = self - task_working_hours
        for task in task_duration:
            # for each planning slot, compute the duration
            task.allocated_hours = task.duration * (len(task.user_ids) or 1)
        # This part of the code comes in major parts from planning, with adaptations.
        # Compute the conjunction of the task user's work intervals and the task.
        if not task_working_hours:
            return
        # if there are at least one task having start or end date, call the _get_valid_work_intervals
        start_utc = utc.localize(min(task_working_hours.mapped('planned_date_begin')))
        end_utc = utc.localize(max(task_working_hours.mapped('planned_date_end')))
        # work intervals per user/per calendar are retrieved with a batch
        resources = task_working_hours.user_ids.mapped('resource_ids').filtered(lambda r: r.company_id.id == self.env.company.id)
        user_work_intervals, calendar_work_intervals = resources._get_valid_work_intervals(
            start_utc, end_utc, calendars=task_working_hours.company_id.resource_calendar_id
        )
        for task in task_working_hours:
            start = max(start_utc, utc.localize(task.planned_date_begin))
            end = min(end_utc, utc.localize(task.planned_date_end))
            interval = Intervals([(
                start, end, self.env['resource.calendar.attendance']
            )])
            sum_allocated_hours = 0.0
            if task.user_ids:
                # we sum up the allocated hours for each user's resource
                for user in task.user_ids:
                    user_resources = user.resource_ids.filtered(lambda r: r.company_id.id == self.env.company.id)
                    for resource in user_resources:
                        if resource.id in user_work_intervals:
                            sum_allocated_hours += sum_intervals(user_work_intervals[resource.id] & interval)
            else:
                sum_allocated_hours += sum_intervals(calendar_work_intervals[task.company_id.resource_calendar_id.id] & interval)
            task.allocated_hours = sum_allocated_hours

    @api.depends('planned_date_begin', 'planned_date_end')
    def _compute_allocation_type(self):
        for task in self:
            if task.duration < 24:
                task.allocation_type = 'duration'
            else:
                task.allocation_type = 'working_hours'

    @api.depends('planned_date_begin', 'planned_date_end')
    def _compute_duration(self):
        for task in self:
            if not (task.planned_date_begin and task.planned_date_end):
                task.duration = 0.0
            else:
                task.duration = (task.planned_date_end - task.planned_date_begin).total_seconds() / 3600.0

    @api.model
    def _calculate_planned_dates(self, date_start, date_stop, user_id=None, calendar=None):
        if not (date_start and date_stop):
            raise UserError(_('One parameter is missing to use this method. You should give a start and end dates.'))
        start, stop = date_start, date_stop
        if isinstance(start, str):
            start = fields.Datetime.from_string(start)
        if isinstance(stop, str):
            stop = fields.Datetime.from_string(stop)

        if not calendar:
            user = self.env['res.users'].sudo().browse(user_id) if user_id and user_id != self.env.user.id else self.env.user
            calendar = user.resource_calendar_id or self.env.company.resource_calendar_id
            if not calendar:  # Then we stop and return the dates given in parameter.
                return date_start, date_stop

        if not start.tzinfo:
            start = start.replace(tzinfo=utc)
        if not stop.tzinfo:
            stop = stop.replace(tzinfo=utc)

        intervals = calendar._work_intervals_batch(start, stop)[False]
        if not intervals:  # Then we stop and return the dates given in parameter
            return date_start, date_stop
        list_intervals = [(start, stop) for start, stop, records in intervals]  # Convert intervals in interval list
        start = list_intervals[0][0].astimezone(utc).replace(tzinfo=None)  # We take the first date in the interval list
        stop = list_intervals[-1][1].astimezone(utc).replace(tzinfo=None)  # We take the last date in the interval list
        return start, stop

    def _get_tasks_by_resource_calendar_dict(self):
        """
            Returns a dict of:
                key = 'resource.calendar'
                value = recordset of 'project.task'
        """
        default_calendar = self.env.company.resource_calendar_id

        calendar_by_user_dict = {  # key: user_id, value: resource.calendar instance
            user.id:
                user.resource_calendar_id or default_calendar
            for user in self.mapped('user_ids')
        }

        tasks_by_resource_calendar_dict = defaultdict(
            lambda: self.env[self._name])  # key = resource_calendar instance, value = tasks
        for task in self:
            if len(task.user_ids) == 1:
                tasks_by_resource_calendar_dict[calendar_by_user_dict[task.user_ids.id]] |= task
            else:
                tasks_by_resource_calendar_dict[default_calendar] |= task

        return tasks_by_resource_calendar_dict

    def write(self, vals):
        compute_default_planned_dates = None
        if not self._context.get('fsm_mode', False) \
           and not self._context.get('smart_task_scheduling', False) \
           and 'planned_date_begin' in vals and 'planned_date_end' in vals:  # if fsm_mode=True then the processing in industry_fsm module is done for these dates.
            compute_default_planned_dates = self.filtered(lambda task: not task.planned_date_begin and not task.planned_date_end)

        res = super().write(vals)

        if compute_default_planned_dates:
            # Take the default planned dates
            planned_date_begin = vals.get('planned_date_begin', False)
            planned_date_end = vals.get('planned_date_end', False)

            # Then sort the tasks by resource_calendar and finally compute the planned dates
            tasks_by_resource_calendar_dict = compute_default_planned_dates._get_tasks_by_resource_calendar_dict()
            for (calendar, tasks) in tasks_by_resource_calendar_dict.items():
                date_start, date_stop = self._calculate_planned_dates(planned_date_begin, planned_date_end, calendar=calendar)
                tasks.write({
                    'planned_date_begin': date_start,
                    'planned_date_end': date_stop,
                })

        return res

    # -------------------------------------
    # Business Methods : Smart Scheduling
    # -------------------------------------
    def schedule_tasks(self, vals):
        """ Compute the start and end planned date for each task in the recordset.

            This computation is made according to the schedule of the employee the tasks
            are assigned to, as well as the task already planned for the user.
            The function schedules the tasks order by dependencies, priority.
            The transitivity of the tasks is respected in the recordset, but is not guaranteed
            once the tasks are planned for some specific use case. This function ensures that
            no tasks planned by it are concurrent with another.
            If this function is used to plan tasks for the company and not an employee,
            the tasks are planned with the company calendar, and have the same starting date.
            Their end date is computed based on their timesheet only.
            Concurrent or dependent tasks are irrelevant.

            :return: empty dict if some data were missing for the computation
                or if no action and no warning to display.
                Else, return a dict { 'action': action, 'warnings'; warning_list } where action is
                the action to launch if some planification need the user confirmation to be applied,
                and warning_list the warning message to show if needed.
        """
        required_written_fields = {'planned_date_begin', 'planned_date_end'}
        if not self.env.context.get('last_date_view') or len(self.project_id) != 1 \
           or any(key not in vals for key in required_written_fields):
            self.write(vals)
            return {}

        discarded_task_vals = []
        tasks_to_write = {}
        warnings = {}

        user = self.env['res.users']
        calendar = self.project_id.resource_calendar_id
        company = self.company_id if len(self.company_id) == 1 else self.project_id.company_id
        tz_info = calendar.tz
        sorted_tasks = self.sorted('priority', reverse=True)
        if (vals.get('user_ids') and len(vals['user_ids']) == 1) or ('user_ids' not in vals and len(self.user_ids) == 1):
            user = self.env['res.users'].browse(vals.get('user_ids', self.user_ids.ids))
            tz_info = user.tz or self._context.get('tz', 'UTC')
            dependencies_dict = {  # contains a task as key and the list of tasks before this one as values
                task:
                    [t for t in self if t != task and t in task.depend_on_ids]
                    if task.depend_on_ids
                    else []
                for task in sorted_tasks
            }
            sorted_tasks = topological_sort(dependencies_dict)

        max_date_start = datetime.strptime(self.env.context.get('last_date_view'), '%Y-%m-%d %H:%M:%S').astimezone(timezone(tz_info))
        init_date_start = datetime.strptime(vals["planned_date_begin"], '%Y-%m-%d %H:%M:%S').astimezone(timezone(tz_info))
        fetch_date_start = init_date_start
        fetch_date_end = max_date_start
        current_date_start = init_date_start
        end_loop = init_date_start + relativedelta(day=31, month=12, years=1)  # end_loop will be the end of the next year.

        invalid_intervals, schedule = self._compute_schedule(user, calendar, fetch_date_start, fetch_date_end, company)
        concurrent_tasks_intervals = self._fetch_concurrent_tasks_intervals_for_employee(fetch_date_start, fetch_date_end, user, tz_info)
        dependent_tasks_end_dates = self._fetch_last_date_end_from_dependent_task_for_all_tasks(tz_info)

        for task in sorted_tasks:
            if task._get_hours_to_plan() <= 0:
                continue
            hours_to_plan = task._get_hours_to_plan()
            compute_date_start = compute_date_end = False
            last_date_end = dependent_tasks_end_dates.get(task.id)
            # The 'user' condition is added to avoid changing the starting date based on the tasks dependencies of
            # the tasks to plan when the working schedule of company is used to schedule the tasks.
            if last_date_end and user:
                current_date_start = last_date_end
            # In case working intervals were added to the schedule in the previous iteration, set the curr_schedule to schedule
            curr_schedule = schedule
            while (not compute_date_start or not compute_date_end) and (current_date_start < end_loop):
                for start_date, end_date, dummy in curr_schedule:
                    if end_date <= current_date_start:
                        continue
                    hours_to_plan -= (end_date - start_date).total_seconds() / 3600
                    if not compute_date_start:
                        compute_date_start = start_date

                    if hours_to_plan <= 0:
                        compute_date_end = end_date + relativedelta(seconds=hours_to_plan * 3600)
                        break
                if hours_to_plan <= 0:  # the compute_date_end was found, we check if the candidates start and end date are valid
                    current_date_start = self._check_concurrent_tasks(compute_date_start, compute_date_end, concurrent_tasks_intervals)
                    # an already planned task is concurrent with the candidate dates. reset the values and keep searching for new candidate dates
                    if current_date_start:
                        compute_date_start = False
                        compute_date_end = False
                        hours_to_plan = task._get_hours_to_plan()
                        end_interval = self._get_end_interval(current_date_start, curr_schedule)
                        # removed the part already checked in the working schedule
                        curr_schedule = schedule - Intervals([(init_date_start, end_interval, task)])
                    # no concurrent tasks were found, we reset the current date start
                    else:
                        current_date_start = schedule._items[0][0]
                        # if the task is assigned to a user, add the working interval of the task to the concurrent tasks
                        if user:
                            concurrent_tasks_intervals |= Intervals([(compute_date_start, compute_date_end, task)])

                else:  # no date end candidate was found, update the schedule and keep searching
                    fetch_date_start = fetch_date_end
                    fetch_date_end = (fetch_date_end + relativedelta(days=1)) + relativedelta(months=1, day=1)
                    new_invalid_intervals, curr_schedule = task._compute_schedule(user, calendar, fetch_date_start, fetch_date_end, task.company_id or company)
                    # schedule is not used in this iteration but we are using this variable to keep the fetched intervals to avoid refetching it later
                    schedule |= curr_schedule
                    invalid_intervals |= new_invalid_intervals
                    concurrent_tasks_intervals |= self._fetch_concurrent_tasks_intervals_for_employee(fetch_date_start, fetch_date_end, user, tz_info)

            # remove the task from the record to avoid unnecessary write
            self -= task
            # this is a security break to avoid infinite loop. It is very unlikely to be of used in a real use case.
            if current_date_start > end_loop:
                if 'loop_break' not in warnings:
                    warnings['loop_break'] = _lt("Some tasks weren't planned because the closest available starting date was too far ahead in the future")
                current_date_start = schedule._items[0][0]
                continue

            start_no_utc = compute_date_start.astimezone(utc).replace(tzinfo=None)
            end_no_utc = compute_date_end.astimezone(utc).replace(tzinfo=None)
            company_schedule = False
            # if the working interval for the task has overlap with 'invalid_intervals', we set the warning message accordingly
            if start_no_utc > datetime.now() and len(Intervals([(compute_date_start, compute_date_end, task)]) & invalid_intervals) > 0:
                company_schedule = True
            if compute_date_start <= max_date_start:
                tasks_to_write[task] = {'start': start_no_utc, 'end': end_no_utc}
            else:
                if company_schedule and 'company_schedule' not in warnings:
                    warnings['company_schedule'] = _lt('This employee does not have a running contract during the selected period.\nThe working hours of the company were used as a reference instead.')
                discarded_task_vals.append((task.id, start_no_utc, end_no_utc, company_schedule))

        self.write(vals)
        for task in tasks_to_write:
            task_vals = {
                'planned_date_begin': tasks_to_write[task]['start'],
                'planned_date_end': tasks_to_write[task]['end'],
                'user_ids': user.ids,
            }
            if user:
                task_vals['user_ids'] = user.ids
            task.with_context(smart_task_scheduling=True).write(task_vals)
        response = {}
        if discarded_task_vals:
            wizard = self.env["project.task.confirm.schedule.wizard"].create({
                'line_ids': [
                    Command.create({
                        'task_id': task_id,
                        'date_begin': start,
                        'date_end': end,
                        'warning': warnings['company_schedule'] if warning else False,
                    }) for task_id, start, end, warning in discarded_task_vals],
                'user_id': user.id,
            })
            if 'company_schedule' in warnings:  # this warning is displayed in the wizard, no need to display it as notification
                del warnings['company_schedule']
            action = {
                'name': _('Caution: some tasks have not been scheduled'),
                'type': 'ir.actions.act_window',
                'res_model': 'project.task.confirm.schedule.wizard',
                'views': [[False, 'form']],
                'view_id': 'view_task_confirm_schedule_wizard_form',
                'target': 'new',
                'res_id': wizard.id,
            }
            response['action'] = action
        if warnings:
            response['warnings'] = list(warnings.values())
        return response

    def _get_hours_to_plan(self):
        return self.planned_hours

    @api.model
    def _compute_schedule(self, user, calendar, date_start, date_end, company=None):
        """ Compute the working intervals available for the employee
            fill the empty schedule slot between contract with the company schedule.
        """
        if user:
            user_resources = user.resource_ids.filtered(lambda r: r.company_id.id == (company.id if company else self.env.company.id))
            if user_resources:
                resource = user_resources[0]  # Take the first valid resource
                employees_work_days_data, dummy = resource.sudo()._get_valid_work_intervals(date_start, date_end)
                schedule = employees_work_days_data.get(resource.id) or Intervals([])
            else:
                schedule = Intervals([])
            # We are using this function to get the intervals for which the schedule of the employee is invalid. Those data are needed to check if we must fallback on the
            # company schedule. The validity_intervals['valid'] does not contain the work intervals needed, it simply contains large intervals with validity time period
            # ex of return value : ['valid'] = 01-01-2000 00:00:00 to 11-01-2000 23:59:59; ['invalid'] = 11-02-2000 00:00:00 to 12-31-2000 23:59:59
            dummy, validity_intervals = self._web_gantt_reschedule_get_resource_calendars_validity(
                date_start, date_end,
                resource=user._get_project_task_resource(),
                company=company)
            for start, stop, dummy in validity_intervals['invalid']:
                schedule |= calendar._work_intervals_batch(start, stop)[False]

            return validity_intervals['invalid'], schedule
        else:
            return Intervals([]), calendar._work_intervals_batch(date_start, date_end)[False]

    def _fetch_last_date_end_from_dependent_task_for_all_tasks(self, tz_info):
        """
            return: return a dict with task.id as key, and the latest date end from all the dependent task of that task
        """
        query = """
                    SELECT task.id as id,
                           MAX(depends_on.planned_date_end) as date
                      FROM project_task task
                      JOIN task_dependencies_rel rel
                        ON rel.task_id = task.id
                      JOIN project_task depends_on
                        ON depends_on.id != task.id
                       AND depends_on.id = rel.depends_on_id
                       AND depends_on.planned_date_end is not null
                     WHERE task.id = any(%s)
                  GROUP BY task.id
                """
        self.env.cr.execute(query, [self.ids])
        return {res['id']: res['date'].astimezone(timezone(tz_info)) for res in self.env.cr.dictfetchall()}

    @api.model
    def _fetch_concurrent_tasks_intervals_for_employee(self, date_begin, date_end, user, tz_info):
        concurrent_tasks = self.env['project.task']
        if user:
            concurrent_tasks = self.env['project.task'].search(
                [('user_ids', '=', user.id),
                 ('planned_date_end', '>=', date_begin),
                 ('planned_date_begin', '<=', date_end)],
                order='planned_date_end',
            )

        return Intervals([
            (t.planned_date_begin.astimezone(timezone(tz_info)),
             t.planned_date_end.astimezone(timezone(tz_info)),
             t)
            for t in concurrent_tasks
        ])

    def _check_concurrent_tasks(self, date_begin, date_end, concurrent_tasks):
        current_date_end = None
        for start, stop, dummy in concurrent_tasks:
            if start <= date_end and stop >= date_begin:
                current_date_end = stop
            elif start > date_end:
                break
        return current_date_end

    def _get_end_interval(self, date, intervals):
        for start, stop, dummy in intervals:
            if start <= date <= stop:
                return stop
        return date

    # -------------------------------------
    # Business Methods : Auto-shift
    # -------------------------------------

    @api.model
    def _web_gantt_reschedule_get_empty_cache(self):
        """ Get an empty object that would be used in order to prevent successive database calls during the
            rescheduling process.

            :return: An object that contains reusable information in the context of gantt record rescheduling.
                     The elements added to the cache are:
                     * A dict which caches the work intervals per company or resource. The reason why the key is type
                       mixed is due to the fact that a company has no resource associated.
                       The work intervals are resource dependant, and we will "query" this work interval rather than
                       calling _work_intervals_batch to save some db queries.
                     * A dict with resource's intervals of validity/invalidity per company or resource. The intervals
                       where the resource is "valid", i.e. under contract for an employee, and "invalid", i.e.
                       intervals where the employee was not already there or has been fired. When an interval is in the
                       invalid interval of a resource, then there is a fallback on its company intervals
                       (see _update_work_intervals).
            :rtype: dict
        """
        empty_cache = super()._web_gantt_reschedule_get_empty_cache()
        empty_cache.update({
            self._WEB_GANTT_RESCHEDULE_WORK_INTERVALS_CACHE_KEY: defaultdict(Intervals),
            self._WEB_GANTT_RESCHEDULE_RESOURCE_VALIDITY_CACHE_KEY: defaultdict(
                lambda: {'valid': Intervals(), 'invalid': Intervals()}
            ),
        })
        return empty_cache

    def _web_gantt_reschedule_get_resource(self):
        """ Get the resource linked to the task. """
        self.ensure_one()
        return self.user_ids._get_project_task_resource() if len(self.user_ids) == 1 else self.env['resource.resource']

    def _web_gantt_reschedule_get_resource_entity(self):
        """ Get the resource entity linked to the task.
            The resource entity is either a company, either a resource to cope with resource invalidity
            (i.e. not under contract, not yet created...)
            This is used as key to keep information in the rescheduling business methods.
        """
        self.ensure_one()
        return self._web_gantt_reschedule_get_resource() or self.company_id or self.project_id.company_id

    def _web_gantt_reschedule_get_resource_calendars_validity(
            self, date_start, date_end, intervals_to_search=None, resource=None, company=None
    ):
        """ Get the calendars and resources (for instance to later get the work intervals for the provided date_start
            and date_end).

            :param date_start: A start date for the search
            :param date_end: A end date fot the search
            :param intervals_to_search: If given, the periods for which the calendars validity must be retrieved.
            :param resource: If given, it overrides the resource in self._get_resource
            :return: a dict `resource_calendar_validity` with calendars as keys and their validity as values,
                     a dict `resource_validity` with 'valid' and 'invalid' keys, with the intervals where the resource
                     has a valid calendar (resp. no calendar)
            :rtype: tuple(defaultdict(), dict())
        """
        interval = Intervals([(date_start, date_end, self.env['resource.calendar.attendance'])])
        if intervals_to_search:
            interval &= intervals_to_search
        invalid_interval = interval
        resource = self._web_gantt_reschedule_get_resource() if resource is None else resource
        default_company = company or self.company_id or self.project_id.company_id
        resource_calendar_validity = resource.sudo()._get_calendars_validity_within_period(
            date_start, date_end, default_company=default_company
        )[resource.id]
        for calendar in resource_calendar_validity:
            resource_calendar_validity[calendar] &= interval
            invalid_interval -= resource_calendar_validity[calendar]
        resource_validity = {
            'valid': interval - invalid_interval,
            'invalid': invalid_interval,
        }
        return resource_calendar_validity, resource_validity

    def _web_gantt_reschedule_update_work_intervals(
            self, interval_to_search, cache, resource=None, resource_entity=None
    ):
        """ Update intervals cache if the interval to search for hasn't already been requested for work intervals.

            If the resource_entity has some parts of the interval_to_search which is unknown yet, then the calendar
            of the resource_entity must be retrieved and queried to have the work intervals. If the resource_entity
            is invalid (i.e. was not yet created, not under contract or fired)

            :param interval_to_search: Intervals for which we need to update the work_intervals if the interval
                   is not already searched
            :param cache: An object that contains reusable information in the context of gantt record rescheduling.
        """
        resource = self._web_gantt_reschedule_get_resource() if resource is None else resource
        resource_entity = self._web_gantt_reschedule_get_resource_entity() if resource_entity is None else resource_entity
        work_intervals, resource_validity = self._web_gantt_reschedule_extract_cache_info(cache)
        intervals_not_searched = interval_to_search - resource_validity[resource_entity]['valid'] \
            - resource_validity[resource_entity]['invalid']

        if not intervals_not_searched:
            return

        # For at least a part of the task, we don't have the work information of the resource
        # The interval between the very first date of the interval_to_search to the very last must be explored
        resource_calendar_validity_delta, resource_validity_tmp = self._web_gantt_reschedule_get_resource_calendars_validity(
            intervals_not_searched._items[0][0],
            intervals_not_searched._items[-1][1],
            intervals_to_search=intervals_not_searched, resource=resource,
            company=self.company_id or self.project_id.company_id
        )
        for calendar in resource_calendar_validity_delta:
            if not resource_calendar_validity_delta[calendar]:
                continue
            work_intervals[resource_entity] |= calendar._work_intervals_batch(
                resource_calendar_validity_delta[calendar]._items[0][0],
                resource_calendar_validity_delta[calendar]._items[-1][1],
                resources=resource
            )[resource.id] & resource_calendar_validity_delta[calendar]
        resource_validity[resource_entity]['valid'] |= resource_validity_tmp['valid']
        if resource_validity_tmp['invalid']:
            # If the resource is not valid for a given period (not yet created, not under contract...)
            # There is a fallback on its company calendar.
            resource_validity[resource_entity]['invalid'] |= resource_validity_tmp['invalid']
            company = self.company_id or self.project_id.company_id
            self._web_gantt_reschedule_update_work_intervals(
                interval_to_search, cache,
                resource=self.env['resource.resource'], resource_entity=company
            )
            # Fill the intervals cache of the resource entity with the intervals of the company.
            work_intervals[resource_entity] |= resource_validity_tmp['invalid'] & work_intervals[company]

    @api.model
    def _web_gantt_reschedule_get_interval_auto_shift(self, current, delta):
        """ Get the Intervals from current and current + delta, and in the right order.

            :param current: Baseline of the interval, its start if search_forward is true, its stop otherwise
            :param delta: Timedelta duration of the interval, expected to be positive if search_forward is True,
                          False otherwise
            :param search_forward: Interval direction, forward if True, backward otherwise.
        """
        start, stop = sorted([current, current + delta])
        return Intervals([(start, stop, self.env['resource.calendar.attendance'])])

    @api.model
    def _web_gantt_reschedule_extract_cache_info(self, cache):
        """ Extract the work_intervals and resource_validity

            :param cache: An object that contains reusable information in the context of gantt record rescheduling.
            :return: a tuple (work_intervals, resource_validity) where:
                     * work_intervals is a dict which caches the work intervals per company or resource. The reason why
                       the key is type mixed is due to the fact that a company has no resource associated.
                       The work intervals are resource dependant, and we will "query" this work interval rather than
                       calling _work_intervals_batch to save some db queries.
                     * resource_validity is a dict with resource's intervals of validity/invalidity per company or
                       resource. The intervals where the resource is "valid", i.e. under contract for an employee,
                       and "invalid", i.e. intervals where the employee was not already there or has been fired.
                       When an interval is in the invalid interval of a resource, then there is a fallback on its
                       company intervals (see _update_work_intervals).

        """
        return cache[self._WEB_GANTT_RESCHEDULE_WORK_INTERVALS_CACHE_KEY], \
            cache[self._WEB_GANTT_RESCHEDULE_RESOURCE_VALIDITY_CACHE_KEY]

    def _web_gantt_reschedule_get_first_working_datetime(self, date_candidate, cache, search_forward=True):
        """ Find and return the first work datetime for the provided work_intervals that matches the date_candidate
            and search_forward criteria. If there is no match in the work_intervals, the cache is updated and filled
            with work intervals for a larger date range.

            :param date_candidate: The date the work interval is searched for. If no exact match can be done,
                                   the closest is returned.
            :param cache: An object that contains reusable information in the context of gantt record rescheduling.
            :param search_forward: The search direction.
                                   Having search_forward truthy causes the search to be made chronologically,
                                   looking for an interval that matches interval_start <= date_time < interval_end.
                                   Having search_forward falsy causes the search to be made reverse chronologically,
                                   looking for an interval that matches interval_start < date_time <= interval_end.
            :return: datetime. The closest datetime that matches the search criteria and the
                     work_intervals updated with the data fetched from the database if any.
        """
        self.ensure_one()
        assert date_candidate.tzinfo
        delta = (1 if search_forward else -1) * relativedelta(months=1)
        date_to_search = date_candidate
        resource_entity = self._web_gantt_reschedule_get_resource_entity()

        interval_to_search = self._web_gantt_reschedule_get_interval_auto_shift(date_to_search, delta)

        work_intervals, dummy = self._web_gantt_reschedule_extract_cache_info(cache)
        interval = work_intervals[resource_entity] & interval_to_search
        while not interval:
            self._web_gantt_reschedule_update_work_intervals(interval_to_search, cache)
            interval = work_intervals[resource_entity] & interval_to_search
            date_to_search += delta
            interval_to_search = self._web_gantt_reschedule_get_interval_auto_shift(date_to_search, delta)

        return interval._items[0][0] if search_forward else interval._items[-1][1]

    @api.model
    def _web_gantt_reschedule_plan_hours_auto_shift(self, intervals, hours_to_plan, searched_date, search_forward=True):
        """ Get datetime after having planned hours from a searched date, in the future (search_forward) or in the
            past (not search_forward) given the intervals.

            :param intervals: The intervals to browse.
            :param : The remaining hours to plan.
            :param searched_date: The current value of the search_date.
            :param search_forward: The search direction. Having search_forward truthy causes the search to be made
                                   chronologically.
                                   Having search_forward falsy causes the search to be made reverse chronologically.
            :return: tuple ``(planned_hours, searched_date)``.
        """
        if not intervals:
            return hours_to_plan, searched_date
        if search_forward:
            interval = (searched_date, intervals._items[-1][1], self.env['resource.calendar.attendance'])
            intervals_to_browse = Intervals([interval]) & intervals
        else:
            interval = (intervals._items[0][0], searched_date, self.env['resource.calendar.attendance'])
            intervals_to_browse = reversed(Intervals([interval]) & intervals)
        new_planned_date = searched_date
        for interval in intervals_to_browse:
            delta = min(hours_to_plan, interval[1] - interval[0])
            new_planned_date = interval[0] + delta if search_forward else interval[1] - delta
            hours_to_plan -= delta
            if hours_to_plan <= timedelta(hours=0.0):
                break
        return hours_to_plan, new_planned_date

    def _web_gantt_reschedule_compute_dates(
            self, date_candidate, search_forward, start_date_field_name, stop_date_field_name, cache
    ):
        """ Compute start_date and end_date according to the provided arguments.
            This method is meant to be overridden when we need to add constraints that have to be taken into account
            in the computing of the start_date and end_date.

            :param date_candidate: The optimal date, which does not take any constraint into account.
            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :param cache: An object that contains reusable information in the context of gantt record rescheduling.
            :return: a tuple of (start_date, end_date)
            :rtype: tuple(datetime, datetime)
        """

        first_datetime = self._web_gantt_reschedule_get_first_working_datetime(
            date_candidate, cache, search_forward=search_forward
        )

        search_factor = 1 if search_forward else -1
        if not self.planned_hours:
            # If there are no planned hours, keep the current duration
            duration = search_factor * (self[stop_date_field_name] - self[start_date_field_name])
            return sorted([first_datetime, first_datetime + duration])

        searched_date = current = first_datetime
        planned_hours = timedelta(hours=self.planned_hours)

        # Keeps track of the hours that have already been covered.
        hours_to_plan = planned_hours
        MIN_NUMB_OF_WEEKS = 1
        MAX_ELAPSED_TIME = timedelta(weeks=53)
        resource_entity = self._web_gantt_reschedule_get_resource_entity()
        work_intervals, dummy = self._web_gantt_reschedule_extract_cache_info(cache)
        while hours_to_plan > timedelta(hours=0.0) and search_factor * (current - first_datetime) < MAX_ELAPSED_TIME:
            # Look for the missing intervals with min search of 1 week
            delta = search_factor * max(hours_to_plan * 3, timedelta(weeks=MIN_NUMB_OF_WEEKS))
            task_interval = self._web_gantt_reschedule_get_interval_auto_shift(current, delta)
            self._web_gantt_reschedule_update_work_intervals(task_interval, cache)
            work_intervals_entry = work_intervals[resource_entity] & task_interval
            hours_to_plan, searched_date = self._web_gantt_reschedule_plan_hours_auto_shift(
                work_intervals_entry, hours_to_plan, searched_date, search_forward
            )
            current += delta

        if hours_to_plan > timedelta(hours=0.0):
            # Reached max iterations
            return False, False

        return sorted([first_datetime, searched_date])

    @api.model
    def _web_gantt_reschedule_is_record_candidate(self, start_date_field_name, stop_date_field_name):
        """ Get whether the record is a candidate for the rescheduling. This method is meant to be overridden when
            we need to add a constraint in order to prevent some records to be rescheduled. This method focuses on the
            record itself (if you need to have information on the relation (master and slave) rather override
            _web_gantt_reschedule_is_relation_candidate).

            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :return: True if record can be rescheduled, False if not.
            :rtype: bool
        """
        is_record_candidate = super()._web_gantt_reschedule_is_record_candidate(start_date_field_name, stop_date_field_name)
        return is_record_candidate and self.project_id.allow_task_dependencies and not self.is_closed

    @api.model
    def _web_gantt_reschedule_is_relation_candidate(self, master, slave, start_date_field_name, stop_date_field_name):
        """ Get whether the relation between master and slave is a candidate for the rescheduling. This method is meant
            to be overridden when we need to add a constraint in order to prevent some records to be rescheduled.
            This method focuses on the relation between records (if your logic is rather on one record, rather override
            _web_gantt_reschedule_is_record_candidate).

            :param master: The master record we need to evaluate whether it is a candidate for rescheduling or not.
            :param slave: The slave record.
            :param start_date_field_name: The start date field used in the gantt view.
            :param stop_date_field_name: The stop date field used in the gantt view.
            :return: True if record can be rescheduled, False if not.
            :rtype: bool
        """
        is_relative_candidate = super()._web_gantt_reschedule_is_relation_candidate(
            master, slave,
            start_date_field_name, stop_date_field_name
        )
        return is_relative_candidate and master.project_id == slave.project_id

    # ----------------------------------------------------
    # Overlapping tasks
    # ----------------------------------------------------

    def action_fsm_view_overlapping_tasks(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('project.action_view_all_task')
        if 'views' in action:
            gantt_view = self.env.ref("project_enterprise.project_task_dependency_view_gantt")
            map_view = self.env.ref('project_enterprise.project_task_map_view_no_title')
            action['views'] = [(gantt_view.id, 'gantt'), (map_view.id, 'map')] + [(state, view) for state, view in action['views'] if view not in ['gantt', 'map']]
        action.update({
            'name': _('Overlapping Tasks'),
            'context': {
                'fsm_mode': False,
                'task_nameget_with_hours': False,
                'initialDate': self.planned_date_begin,
                'search_default_conflict_task': True,
                'search_default_planned_date_begin': self.planned_date_begin,
                'search_default_planned_date_end': self.planned_date_end,
                'search_default_user_ids': self.user_ids.ids,
            }
        })
        return action

    # ----------------------------------------------------
    # Gantt view
    # ----------------------------------------------------

    @api.model
    def gantt_unavailability(self, start_date, end_date, scale, group_bys=None, rows=None):
        start_datetime = fields.Datetime.from_string(start_date)
        end_datetime = fields.Datetime.from_string(end_date)
        user_ids = set()

        # function to "mark" top level rows concerning users
        # the propagation of that user_id to subrows is taken care of in the traverse function below
        def tag_user_rows(rows):
            for row in rows:
                group_bys = row.get('groupedBy')
                res_id = row.get('resId')
                if group_bys:
                    # if user_ids is the first grouping attribute
                    if group_bys[0] == 'user_ids' and res_id:
                        user_id = res_id
                        user_ids.add(user_id)
                        row['user_id'] = user_id
                    # else we recursively traverse the rows
                    elif 'user_ids' in group_bys:
                        tag_user_rows(row.get('rows'))

        tag_user_rows(rows)
        resources = self.env['res.users'].browse(user_ids).mapped('resource_ids').filtered(lambda r: r.company_id.id == self.env.company.id)
        # we reverse sort the resources by date to keep the first one created in the dictionary
        # to anticipate the case of a resource added later for the same employee and company
        user_resource_mapping = {resource.user_id.id: resource.id for resource in resources.sorted('create_date', True)}
        leaves_mapping = resources._get_unavailable_intervals(start_datetime, end_datetime)
        company_leaves = self.env.company.resource_calendar_id._unavailable_intervals(start_datetime.replace(tzinfo=utc), end_datetime.replace(tzinfo=utc))

        # function to recursively replace subrows with the ones returned by func
        def traverse(func, row):
            new_row = dict(row)
            if new_row.get('user_id'):
                for sub_row in new_row.get('rows'):
                    sub_row['user_id'] = new_row['user_id']
            new_row['rows'] = [traverse(func, row) for row in new_row.get('rows')]
            return func(new_row)

        cell_dt = timedelta(hours=1) if scale in ['day', 'week'] else timedelta(hours=12)

        # for a single row, inject unavailability data
        def inject_unavailability(row):
            new_row = dict(row)
            user_id = row.get('user_id')
            calendar = company_leaves
            if user_id:
                resource_id = user_resource_mapping.get(user_id)
                if resource_id:
                    calendar = leaves_mapping[resource_id]

            # remove intervals smaller than a cell, as they will cause half a cell to turn grey
            # ie: when looking at a week, a employee start everyday at 8, so there is a unavailability
            # like: 2019-05-22 20:00 -> 2019-05-23 08:00 which will make the first half of the 23's cell grey
            notable_intervals = filter(lambda interval: interval[1] - interval[0] >= cell_dt, calendar)
            new_row['unavailabilities'] = [{'start': interval[0], 'stop': interval[1]} for interval in notable_intervals]
            return new_row

        return [traverse(inject_unavailability, row) for row in rows]

    def _get_recurrence_start_date(self):
        self.ensure_one()
        return self.planned_date_begin.date() if self.planned_date_begin else fields.Date.today()

    @api.depends('planned_date_begin')
    def _compute_recurrence_message(self):
        return super(Task, self)._compute_recurrence_message()

    def action_dependent_tasks(self):
        action = super().action_dependent_tasks()
        action['view_mode'] = 'tree,form,kanban,calendar,pivot,graph,gantt,activity,map'
        return action

    def action_recurring_tasks(self):
        action = super().action_recurring_tasks()
        action['view_mode'] = 'tree,form,kanban,calendar,pivot,graph,gantt,activity,map'
        return action

    def _gantt_progress_bar_user_ids(self, res_ids, start, stop):
        start_naive, stop_naive = start.replace(tzinfo=None), stop.replace(tzinfo=None)
        users = self.env['res.users'].search([('id', 'in', res_ids)])
        self.env['project.task'].check_access_rights('read')

        project_tasks = self.env['project.task'].sudo().search([
            ('user_ids', 'in', res_ids),
            ('planned_date_begin', '<=', stop_naive),
            ('planned_date_end', '>=', start_naive),
        ])

        planned_hours_mapped = defaultdict(float)
        resources = users.mapped('resource_ids').filtered(lambda r: r.company_id.id == self.env.company.id)
        user_work_intervals, _dummy = resources.sudo()._get_valid_work_intervals(start, stop)
        for task in project_tasks:
            # if the task goes over the gantt period, compute the duration only within
            # the gantt period
            max_start = max(start, utc.localize(task.planned_date_begin))
            min_end = min(stop, utc.localize(task.planned_date_end))
            # for forecast tasks, use the conjunction between work intervals and task.
            interval = Intervals([(
                max_start, min_end, self.env['resource.calendar.attendance']
            )])
            nb_hours_per_user = (sum_intervals(interval) / (len(task.user_ids) or 1)) if task.allocation_type == 'duration' else 0.0
            for user in task.user_ids:
                if task.allocation_type == 'duration':
                    planned_hours_mapped[user.id] += nb_hours_per_user
                else:
                    user_resources = user.resource_ids.filtered(lambda r: r.company_id.id == self.env.company.id)
                    for resource in user_resources:
                        if resource.id in user_work_intervals:
                            work_intervals = interval & user_work_intervals[resource.id]
                            planned_hours_mapped[user.id] += sum_intervals(work_intervals)
        # Compute employee work hours based on its work intervals.
        # Map resource work intervals back to users
        work_hours = defaultdict(float)
        for user in users:
            user_resources = user.resource_ids.filtered(lambda r: r.company_id.id == self.env.company.id)
            for resource in user_resources:
                if resource.id in user_work_intervals:
                    work_hours[user.id] += sum_intervals(user_work_intervals[resource.id])
        return {
            user.id: {
                'value': planned_hours_mapped[user.id],
                'max_value': work_hours.get(user.id, 0.0),
            }
            for user in users
        }

    def _gantt_progress_bar(self, field, res_ids, start, stop):
        if field == 'user_ids':
            return dict(
                self._gantt_progress_bar_user_ids(res_ids, start, stop),
                warning=_("This user isn't expected to have task during this period. Planned hours :"),
            )
        raise NotImplementedError(_("This Progress Bar is not implemented."))

    @api.model
    def gantt_progress_bar(self, fields, res_ids, date_start_str, date_stop_str):
        if not self.user_has_groups("project.group_project_user"):
            return {field: {} for field in fields}
        start_utc, stop_utc = string_to_datetime(date_start_str), string_to_datetime(date_stop_str)

        progress_bars = {}
        for field in fields:
            progress_bars[field] = self._gantt_progress_bar(field, res_ids[field], start_utc, stop_utc)

        return progress_bars






