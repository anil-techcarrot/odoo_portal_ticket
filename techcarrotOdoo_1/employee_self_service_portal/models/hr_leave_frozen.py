from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class HrLeaveTypeFrozen(models.Model):
    _inherit = 'hr.leave.type'

    x_is_frozen = fields.Boolean(
        string="Frozen Leave",
        compute='_compute_is_frozen',
        store=True,
    )

    @api.depends('name')
    def _compute_is_frozen(self):
        for lt in self:
            lt.x_is_frozen = (lt.name or '').strip().lower() == 'frozen leave'


class HrLeaveAllocationFrozen(models.Model):
    _inherit = 'hr.leave.allocation'

    x_frozen_unlocked = fields.Boolean(
        string="Unlock Frozen Leave",
        help="When enabled, the employee can apply for this frozen leave type."
    )
    x_type_is_frozen = fields.Boolean(
        related='holiday_status_id.x_is_frozen',
        string="Is Frozen Type",
        store=False,
    )