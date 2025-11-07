# -*- coding: utf-8 -*-

from odoo import fields, models


class TaskStopRunningTimersConfirmation(models.TransientModel):
    _name = 'project.task.stop.timers.wizard'
    _description = 'Task stop running timers confirmation wizard'

    line_ids = fields.One2many('project.task.stop.timers.wizard.line', 'wizard_id', required=True)

    def action_confirm(self):
        self.line_ids.task_id.action_fsm_validate(stop_running_timers=True)


class TaskStopRunningTimersConfirmationLine(models.TransientModel):
    _name = 'project.task.stop.timers.wizard.line'
    _description = 'Task stop running timers confirmation wizard line'

    wizard_id = fields.Many2one('project.task.stop.timers.wizard')
    task_id = fields.Many2one('project.task', required=True)
