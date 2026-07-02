from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class HrLeaveESS(models.Model):
    _inherit = 'hr.leave'


    state = fields.Selection(tracking=False)

    def _track_subtype(self, init_values):
        return False

    def activity_update(self):
        return super(HrLeaveESS, self.with_context(mail_dont_send=True)).activity_update()

    def message_post(self, **kwargs):

        body = kwargs.get('body') or ''
        if isinstance(body, str) and (
            'has been accepted' in body or 'has been refused' in body
        ):
            kwargs.pop('partner_ids', None)
            kwargs['mail_auto_delete'] = True
            self = self.with_context(
                mail_create_nosubscribe=True,
                mail_dont_send=True,
                mail_notify_force_send=False,
            )
        return super(HrLeaveESS, self).message_post(**kwargs)

    def _notify_manager(self):

        return


    def _ess_send_mail(self, template_xmlid, email_to, email_cc=None):
        if not email_to:
            return
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            return
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        cc = [e for e in (email_cc or []) if e]
        for leave in self:
            vals = {'email_to': email_to}
            if cc:
                vals['email_cc'] = ','.join(cc)

            template.with_context(base_url=base_url, mail_dont_send=False).sudo().send_mail(
                leave.id, force_send=True, email_values=vals
            )

    def action_validate(self):
        res = super().action_validate()
        for leave in self:
            if leave.state == 'validate':
                if not leave.env.context.get('_ess_approved_sent') and leave.employee_id.work_email:
                    leave._ess_send_mail(
                        'employee_self_service_portal.email_template_leave_approved',
                        leave.employee_id.work_email,
                    )
                if not leave.env.context.get('_ess_negative_hr_sent'):
                    leave._ess_notify_hr_if_negative()
        return res

    def action_approve(self):
        res = super().action_approve()
        for leave in self:
            if leave.state == 'validate':
                if leave.employee_id.work_email:
                    leave.with_context(_ess_approved_sent=True)._ess_send_mail(
                        'employee_self_service_portal.email_template_leave_approved',
                        leave.employee_id.work_email,
                    )
                leave.with_context(_ess_negative_hr_sent=True)._ess_notify_hr_if_negative()
        return res

    def action_refuse(self):
        res = super().action_refuse()
        for leave in self:
            if leave.employee_id.work_email:
                leave._ess_send_mail(
                    'employee_self_service_portal.email_template_leave_rejected',
                    leave.employee_id.work_email,
                )
        return res



    def _ess_notify_hr_if_negative(self):

        for leave in self:
            lt = leave.holiday_status_id


            has_accrual = self.env['hr.leave.allocation'].sudo().search_count([
                ('employee_id', '=', leave.employee_id.id),
                ('holiday_status_id', '=', lt.id),
                ('state', '=', 'validate'),
                ('allocation_type', '=', 'accrual'),
            ]) > 0
            if not has_accrual:
                continue

            balance = lt.sudo().with_context(
                employee_id=leave.employee_id.id
            ).virtual_remaining_leaves

            if balance < 0:
                hr_emails = [e for e in lt.responsible_ids.mapped('email') if e]
                if hr_emails:
                    leave._ess_send_mail(
                        'employee_self_service_portal.email_template_leave_negative_hr',
                        ','.join(hr_emails),
                    )
                else:
                    _logger.warning(
                        "ESS Leave: accrual balance %.2f negative for leave %s "
                        "but no HR on type %s", balance, leave.id, lt.name
                    )

    def _ess_simple_balance(self, leave):

        emp = leave.employee_id
        lt = leave.holiday_status_id

        allocations = self.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', emp.id),
            ('holiday_status_id', '=', lt.id),
            ('state', '=', 'validate'),
        ])
        total_allocated = sum(allocations.mapped('number_of_days'))

        taken = self.env['hr.leave'].sudo().search([
            ('employee_id', '=', emp.id),
            ('holiday_status_id', '=', lt.id),
            ('state', '=', 'validate'),
        ])
        total_taken = sum(taken.mapped('number_of_days'))

        return total_allocated - total_taken


class HrLeaveAllocationESS(models.Model):
    _inherit = 'hr.leave.allocation'

    def message_post(self, **kwargs):
        kwargs['mail_auto_delete'] = True
        self = self.with_context(
            mail_create_nosubscribe=True,
            mail_dont_send=True,
            mail_notify_force_send=False,
        )
        return super().message_post(**kwargs)

    def activity_update(self):
        return super(HrLeaveAllocationESS,
                     self.with_context(mail_dont_send=True)).activity_update()