# -*- coding: utf-8 -*-

from odoo import models, fields


class ITTicketRejectWizard(models.TransientModel):
    _name = 'it.ticket.reject.wizard'
    _description = 'Reject Ticket Wizard'

    # Ticket that is being rejected through this wizard
    ticket_id = fields.Many2one('it.ticket', 'Ticket', required=True)

    # Reason provided by user for rejecting the ticket
    rejection_reason = fields.Text('Rejection Reason', required=True)

    def action_reject(self):
        """Execute rejection workflow and close the wizard."""

        # Capture this BEFORE do_reject() runs — the state changes to
        # 'rejected' as a result of the call below, and HR loses read
        # access to the ticket the instant it leaves 'hr_approval'
        # (by design). If we check state after the fact, it's already gone.
        was_hr = self.ticket_id.state == 'hr_approval'

        # Call main ticket reject logic with sudo to ensure access safety
        self.ticket_id.sudo().do_reject(self.rejection_reason)

        # ── SAFE REDIRECT ────────────────────────────────────────────────
        # If HR just rejected, closing the wizard would make Odoo try to
        # re-render the ticket form behind it — and fail with an Access
        # Error, even though the rejection itself succeeded (same issue
        # fixed in approve_wizard.py). Redirect HR to the "Pending HR
        # Approval" list instead of the now-inaccessible record.
        if was_hr:
            action = self.env.ref('ticketing_it.action_it_ticket_pending_hr_approval', raise_if_not_found=False)
            if action:
                return {
                    'type': 'ir.actions.act_window',
                    'name': action.name,
                    'res_model': 'it.ticket',
                    'view_mode': 'list,form',
                    'views': [(False, 'list'), (False, 'form')],
                    'domain': [('state', '=', 'hr_approval')],
                    'target': 'main',
                }

        # Close wizard after rejection is processed
        return {'type': 'ir.actions.act_window_close'}