from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools.mail import html2plaintext


class MailComposer(models.TransientModel):
    _name = 'mail.compose.message'
    _inherit = ['mail.composer.mixin', 'mail.compose.message']
    _description = 'Email composition wizard'
    _log_access = True

    send_whatsapp = fields.Boolean()
    whatsapp_account_id = fields.Many2one(
        'wa.account',
        string="WhatsApp Account",
        required=True,
        help="Select the WhatsApp account to use for sending the message."
    )

    @api.model
    def default_get(self, fields):
        """
        Set the default WhatsApp account based on the current company.
        """
        res = super(MailComposer, self).default_get(fields)
        default_account = self.env['wa.account'].search([('company_id', '=', self.env.company.id)], limit=1)
        if default_account:
            res['whatsapp_account_id'] = default_account.id
        return res
    
    def action_send_only_whatsapp(self):
        """
        Override the send mail action to send both WhatsApp and email messages if `send_whatsapp` is True.
        """
        if self.send_whatsapp:
            # Validate WhatsApp account
            if not self.whatsapp_account_id:
                raise UserError(_("Invalid WhatsApp account specified."))

            # Validate partners
            if not self.partner_ids:
                raise UserError(_("No partner is associated with this message."))

            # Convert the `body` field (HTML) to plain text
            message_content = html2plaintext(self.body)
            if not message_content:
                raise UserError(_("Message content is empty. Please provide a message."))

            # Fetch res_model and res_id from the context
            res_model = self.env.context.get('active_model')
            res_id = self.env.context.get('active_id')
            if not res_model or not res_id:
                raise UserError(_("No associated record found to log the WhatsApp message."))

            account = self.whatsapp_account_id
            attachments = self.attachment_ids or []

            # Send to all partners and all attachments
            for partner in self.partner_ids:
                if not partner.mobile:
                    continue  # skip partners without mobile
                recipient_number = partner.mobile
                if attachments:
                    for attachment in attachments:
                        account.send_media(
                            mobile=recipient_number,
                            caption=message_content,
                            b64=attachment.datas,
                            mime=attachment.mimetype or 'application/octet-stream',
                            filename=attachment.name
                        )
                        self._log_whatsapp_message(partner, message_content, res_model, res_id, success=True)
                else:
                    account.send_text(
                        mobile=recipient_number,
                        message=message_content
                    )
                    self._log_whatsapp_message(partner, message_content, res_model, res_id, success=True)

    def _log_whatsapp_message(self, partner, message_content, res_model, res_id, success=True, error=None):
        """
        Log WhatsApp message for mail compose wizard.
        """
        whatsapp_icon = '<i class="fa fa-whatsapp" style="color:{};"></i>'.format('green' if success else 'red')
        message_body = f'{whatsapp_icon} {message_content}'
        if not success and error:
            message_body += f'<br/><span style="color:red;">{error}</span>'
        self.env['mail.message'].create({
            'body': message_body,
            'model': res_model,
            'res_id': res_id,
        })

    def action_send_mail(self):
        """
        Override the send mail action to send both WhatsApp and email messages if `send_whatsapp` is True.
        """
        self.action_send_only_whatsapp()
        # Call the parent method to send the email
        return super().action_send_mail()
