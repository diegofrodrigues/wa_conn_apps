from odoo import _, models, fields, api
from odoo.exceptions import UserError
from odoo.tools import html2plaintext
import json


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    whatsapp_account_id = fields.Many2one(
        'wa.account',
        string="WhatsApp Account",
        required=False,
        help="Select the WhatsApp account to use for sending the message."
    )

    @api.model
    def default_get(self, fields):
        """
        Set the default WhatsApp account based on the current company.
        """
        res = super(AccountMoveSendWizard, self).default_get(fields)
        default_account = self.env['wa.account'].search([('company_id', '=', self.env.company.id)], limit=1)
        if default_account:
            res['whatsapp_account_id'] = default_account.id
        return res
    
    @api.model
    def _hook_if_success(self, moves_data):
        """ Process (typically send) successful documents. Skip email if only_whatsapp context is set."""
        if self.env.context.get('only_whatsapp'):
            return
        sending_methods = self.sending_method_checkboxes or {}
        if len(sending_methods) == 1 and sending_methods.get('whatsapp', {}).get('checked'):
            return
        else:
            to_send_mail = {
                move: move_data
                for move, move_data in moves_data.items()
                if 'email' in move_data['sending_methods'] and self._is_applicable_to_move('email', move)
            }
            self._send_mails(to_send_mail)
    
    @api.depends('move_id')
    def _compute_sending_method_checkboxes(self):
        super()._compute_sending_method_checkboxes()
        methods = self.env['ir.model.fields'].get_field_selection('res.partner', 'invoice_sending_method')
        for wizard in self:
            preferred_method = self._get_default_sending_method(wizard.move_id)
            need_fallback = not self._is_applicable_to_move(preferred_method, wizard.move_id)
            fallback_method = need_fallback and ('email' if self._is_applicable_to_move('email', wizard.move_id) else 'manual')
            checkboxes = {
                method_key: {
                    'checked': method_key == preferred_method if not need_fallback else method_key == fallback_method,
                    'label': method_label,
                }
                for method_key, method_label in methods if self._is_applicable_to_company(method_key, wizard.company_id)
            }
            checkboxes['whatsapp'] = {
                'checked': False,
                'label': 'WhatsApp',
            }
            wizard.sending_method_checkboxes = checkboxes

    def action_send_only_whatsapp(self):
        """
        Override the send mail action to send WhatsApp messages using WhatsAppMixin.
        """
        sending_methods = self.sending_method_checkboxes or {}
        if sending_methods.get('whatsapp', {}).get('checked'):
            # Validate WhatsApp account
            if not self.whatsapp_account_id:
                raise UserError(_("Please select a valid WhatsApp account."))

            # Validate partners
            if not self.mail_partner_ids:
                raise UserError(_("No partner is associated with this message."))

            # Convert the `mail_body` field (HTML) to plain text
            message_content = html2plaintext(self.mail_body)
            if not message_content:
                raise UserError(_("Message content is empty. Please provide a message."))

            account = self.whatsapp_account_id

            # Prepare attachments
            attachments = []
            if self.mail_attachments_widget:
                attachment_ids = [
                    attachment['id'] for attachment in self.mail_attachments_widget
                    if isinstance(attachment['id'], int)
                ]
                if attachment_ids:
                    attachments = self.env['ir.attachment'].browse(attachment_ids)
                else:
                    # Passa contexto only_whatsapp apenas aqui
                    attachments = self.with_context(only_whatsapp=True)._generate_and_send_invoices(self.move_id)

            # Send to all partners and all attachments
            for partner in self.mail_partner_ids:
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
                        self._log_whatsapp_message(partner, message_content, success=True)
                else:
                    account.send_text(
                        mobile=recipient_number,
                        message=message_content
                    )
                    self._log_whatsapp_message(partner, message_content, success=True)

    def _log_whatsapp_message(self, partner, message_content, success=True, error=None):
        """
        Log WhatsApp message with optional attachment, similar to mixin.
        """
        whatsapp_icon = '<i class="fa fa-whatsapp" style="color:{};"></i>'.format('green' if success else 'red')
        message_body = f'{whatsapp_icon} {message_content}'
        # Attachment logging for wizard context is skipped here (see original logic)
        if not success and error:
            message_body += f'<br/><span style="color:red;">{error}</span>'
        self.env['mail.message'].create({
            'body': message_body,
            'model': 'account.move',
            'res_id': self.move_id.id,
        })

    def action_send_and_print(self):
        sending_methods = self.sending_method_checkboxes or {}
        selected_methods = [method for method, vals in sending_methods.items() if vals.get('checked')]
        if not selected_methods:
            raise UserError("Selecione pelo menos um método de envio.")
        self.sending_methods = list(selected_methods)
        if len(selected_methods) > 1 and 'whatsapp' in selected_methods and 'email' in selected_methods:
            self.action_send_only_whatsapp()
            selected_methods = [m for m in selected_methods if m != 'whatsapp']
            self.sending_methods = selected_methods
            return super(AccountMoveSendWizard, self).action_send_and_print()
        else:
            return super(AccountMoveSendWizard, self).action_send_and_print()

