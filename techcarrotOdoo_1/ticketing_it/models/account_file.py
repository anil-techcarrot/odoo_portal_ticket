import io
import zipfile
import base64
from odoo import models

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_print_invoices_as_zip(self):
        report = self.env.ref('account.account_invoices')
        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for move in self:
                pdf_content, _ = report._render_qweb_pdf(report.report_name, [move.id])
                filename = f"{move.name.replace('/', '_')}.pdf"
                zf.writestr(filename, pdf_content)

        buffer.seek(0)
        attachment = self.env['ir.attachment'].create({
            'name': 'Invoices.zip',
            'type': 'binary',
            'datas': base64.b64encode(buffer.read()),
            'mimetype': 'application/zip',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }