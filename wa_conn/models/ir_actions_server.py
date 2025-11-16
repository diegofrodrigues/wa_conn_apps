from odoo import api, models, fields, _


class WAServerAction(models.Model):
    _inherit = 'ir.actions.server'
    _description = 'Server Action with WA Integration'

    name = fields.Char(compute='_compute_name', store=True, readonly=False)
    state = fields.Selection(
    selection_add=[('send_wa_message', 'Send WhatsApp')],
    ondelete={'send_wa_message': 'cascade'}
    )
    partner_ids = fields.Many2many(
        'res.partner',
        'ir_actions_server_partner_rel',  # Unique relational table
        'server_action_id',  # Column for this model
        'partner_id',  # Column for the related model
        string="Partners",
    help="Select multiple partners to send WA messages."
    )
    wa_account_id = fields.Many2one(
        'wa.account',
    string="WA Account",
        ondelete='set null',
    help="Select the WA account to use for sending messages."
    )
    wa_template_id = fields.Many2one(
        'wa.template',
    string="WA Template",
    help="Select a WA template to use for the message."
    )
    wa_message = fields.Text(string="WA Message", help="Message to send via WA.")
    wa_media = fields.Binary(string="Media File", help="Media file to send via WA.")
    wa_media_filename = fields.Char(string="Media Filename", help="Filename of the media file.")
    model_partner = fields.Boolean(
        string="Model Partner",
        help="If enabled, the partner linked to the model will also receive the WA message."
    )

    def _run_action_send_wa_message(self, eval_context=None):
        account = self.wa_account_id
        for record in self.env[self.model_id.model].browse(self.env.context.get('active_ids', [])):
            if self.wa_template_id:
                message = self.wa_template_id.render_template('message', record)
                media = self.wa_template_id.wa_media
                media_filename = self.wa_template_id.wa_media_filename
            else:
                message = self.wa_message
                media = self.wa_media
                media_filename = self.wa_media_filename

            # Send to selected partners
            for partner in self.partner_ids:
                if media:
                    account.send_media(
                        mobile=partner.mobile,
                        caption=message,
                        b64=media,
                        mime=None,
                        filename=media_filename
                    )
                else:
                    account.send_text(
                        mobile=partner.mobile,
                        message=message
                    )
            # Optionally send to the partner of the model
            if self.model_partner and hasattr(record, 'partner_id') and record.partner_id:
                if media:
                    account.send_media(
                        mobile=record.partner_id.mobile,
                        caption=message,
                        b64=media,
                        mime=None,
                        filename=media_filename
                    )
                else:
                    account.send_text(
                        mobile=record.partner_id.mobile,
                        message=message
                    )

    def run_action(self, eval_context=None):
        """
    Override the run_action method to handle the 'send_wa_message' action type.
        """
        if self.state == 'send_wa_message':
            self._run_action_send_wa_message(eval_context=eval_context)
        else:
            super(WAServerAction, self).run_action(eval_context=eval_context)

    @api.depends('state')
    def _compute_name(self):
        """
    Generate a name for the 'Send WA Message' action.
        """
        super(WAServerAction, self)._compute_name()
        for action in self:
            if action.state == 'send_wa_message':
                action.name = 'Send Whatsapp'
