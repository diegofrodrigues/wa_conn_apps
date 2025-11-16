from odoo import _, api, fields, models
from odoo.tools.safe_eval import safe_eval


class WACompose(models.TransientModel):
    _name = 'wa.compose'
    _description = 'WhatsApp Compose Message'

    wa_account_id = fields.Many2one(
        'wa.account',
        string="WA Account",
        required=True,
        help="Select the WA account to use for sending the message."
    )
    partner_ids = fields.Many2many(
        'res.partner',
        string="Recipients",
        help="Select the recipients for the WA message."
    )
    wa_template_id = fields.Many2one(
        'wa.template',
        string="WA Template",
        domain="[('model', '=', res_model)]",
        help="Select a WA template to use for the message."
    )
    wa_message = fields.Text(string="WA Message", required=True, help="Enter the WA message.")
    wa_media = fields.Binary(string="Media File", help="Attach a media file to send.")
    wa_media_filename = fields.Char(string="Media Filename", help="Filename of the media file.")
    res_model = fields.Char(string="Related Document Model", help="The model of the related document.")
    model = fields.Char(
        string="Technical Model Name",
        compute='_compute_model',
        readonly=False,
        store=True,
        help="Technical field: model name of the related document (auto-computed)."
    )
    res_id = fields.Integer(string="Related Document ID", help="The ID of the related document.")

    @api.depends('res_model')
    def _compute_model(self):
        """
        Compute the technical model field from res_model or context.
        """
        for wizard in self:
            wizard.model = wizard.res_model or self.env.context.get('default_res_model')

    @api.model
    def default_get(self, fields):
        """
        Set the default WhatsApp account and context for dynamic placeholder rendering.
        """
        res = super(WACompose, self).default_get(fields)
        default_account = self.env['wa.account'].search([('company_id', '=', self.env.company.id)], limit=1)
        if default_account:
            res['wa_account_id'] = default_account.id

        partner_id = self.env.context.get('default_partner_id')
        if not partner_id:
            res_model = self.env.context.get('default_res_model')
            res_id = self.env.context.get('default_res_id')
            if res_model and res_id:
                record = self.env[res_model].browse(res_id)
                if hasattr(record, 'partner_id') and record.partner_id:
                    partner_id = record.partner_id.id
        if partner_id:
            res['partner_ids'] = [(6, 0, [partner_id])]
        return res

    @api.onchange('wa_template_id', 'res_id', 'res_model')
    def _onchange_wa_template_id(self):
        """
        Render the template using the selected record and fill the message field.
        """
        if self.wa_template_id:
            record = None
            if self.res_model and self.res_id:
                record = self.env[self.res_model].browse(self.res_id)
                if not record or not record.exists():
                    record = None
            if record:
                try:
                    message = self.wa_template_id.render_template('wa_message', record)
                    if not isinstance(message, str):
                        message = str(message) if message is not None else ''
                    self.wa_message = message or ''
                    self.wa_media = self.wa_template_id.wa_media
                    self.wa_media_filename = self.wa_template_id.wa_media_filename
                except Exception:
                    self.wa_message = 'error'
                    self.wa_media = self.wa_template_id.wa_media
                    self.wa_media_filename = self.wa_template_id.wa_media_filename
            else:
                self.wa_message = self.wa_template_id.wa_message or ''
                self.wa_media = self.wa_template_id.wa_media
                self.wa_media_filename = self.wa_template_id.wa_media_filename
        else:
            self.wa_message = False
            self.wa_media = False
            self.wa_media_filename = False

    def send_message(self):
        """
        Send the WA message to the selected recipients using wa_account methods.
        """
        if not self.partner_ids:
            raise ValueError(_("Please select at least one recipient."))

        account = self.wa_account_id
        for partner in self.partner_ids:
            if not partner.mobile:
                raise ValueError(_("The partner %s does not have a mobile number.") % partner.name)

            # Se tem mídia, usa send_media; senão, send_text
            if self.wa_media:
                result = account.send_media(
                    mobile=partner.mobile,
                    caption=self.wa_message,
                    b64=self.wa_media,
                    filename=self.wa_media_filename,
                )
            else:
                result = account.send_text(
                    mobile=partner.mobile,
                    message=self.wa_message,
                )
            # Log da mensagem
            self._log_wa_message(partner, success=result.get('ok', True), error=result.get('error'))
    
    def _log_wa_message(self, partner, success=True, error=None):
        """
        Log WhatsApp message with optional attachment.
        """
        wa_icon = '<i class="fa fa-whatsapp" style="color:{};"></i>'.format('green' if success else 'red')
        message_body = f'{wa_icon} {self.wa_message}'
        attachment = None
        if self.wa_media:
            mime_type = 'application/octet-stream'
            if self.wa_media_filename and self.wa_media_filename.lower().endswith(('jpg', 'jpeg', 'png', 'gif', 'webp')):
                mime_type = 'image/jpeg'
            attachment = self.env['ir.attachment'].create({
                'name': self.wa_media_filename or 'file',
                'type': 'binary',
                'datas': self.wa_media,
                'res_model': self.res_model,
                'res_id': self.res_id,
                'mimetype': mime_type,
            })
            if mime_type.startswith('image/'):
                message_body += f'<br/><img src="/web/content/{attachment.id}" alt="{self.wa_media_filename}" style="max-width: 300px; max-height: 300px;"/>'
            else:
                message_body += f'<br/><a href="/web/content/{attachment.id}" target="_blank">{self.wa_media_filename}</a>'
        if not success and error:
            message_body += f'<br/><span style="color:red;">{error}</span>'
        self.env['mail.message'].create({
            'body': message_body,
            'model': self.res_model,
            'res_id': self.res_id,
        })
