
from odoo import _, api, fields, models
try:
    from odoo.tools import html2plaintext as _html2plaintext
except Exception:  # safe fallback
    def _html2plaintext(html):
        import re
        text = re.sub(r'<[^>]+>', '', html or '')
        return text.replace('&nbsp;', ' ').replace('&amp;', '&')

class MailMessage(models.Model):
    _inherit = 'mail.message'


    message_type = fields.Selection(
        selection_add=[('whatsapp', 'whatsapp')],
        ondelete={'whatsapp': 'set default'}
    )
    message_derection = fields.Selection(
        [('input','iput'),
        ('output','output')],
        # compute ='_comput_message_direction'
    )
    wa_message_id = fields.Char()
    is_wa = fields.Boolean(default=False, store=True, help="Indica se a mensagem é WhatsApp.")

  
    # WhatsApp extra fields
    message_type = fields.Selection(
        selection_add=[('whatsapp', 'whatsapp')],
        ondelete={'whatsapp': 'set default'}
    )
    message_derection = fields.Selection(
        [('input','iput'),
        ('output','output')],
        # compute ='_comput_message_direction'
    )
    wa_message_id = fields.Char()
    is_wa = fields.Boolean(default=False, store=True, help="Indica se a mensagem é WhatsApp.")

    @api.depends('message_type')
    def _comput_message_direction(self):
        if self.message_derection == 'whatsapp':
            self.message_derection = 'output'

    @api.model_create_multi
    def create(self, values_list):
        messages = super(MailMessage, self).create(values_list)
        # Skip WA sending if explicitly requested (e.g., inbound webhook posts)
        if self.env.context.get('wa_skip_send'):
            return messages

        subtype_comment = self.env.ref('mail.mt_comment', raise_if_not_found=False)
        for message in messages:
            # Only handle messages posted on discuss.channel
            if message.model != 'discuss.channel' or not message.res_id:
                continue
            # Only send for allowed message types (comment or whatsapp)
            if message.message_type not in ('comment', 'whatsapp'):
                continue
            # Only send plain comments, ignore join/leave and other system subtypes
            if subtype_comment and message.subtype_id and message.subtype_id.id != subtype_comment.id:
                continue
            # Use sudo to avoid ACL errors when checking the channel, and ensure it exists
            channel = self.env['discuss.channel'].sudo().browse(message.res_id)
            if not channel.exists():
                continue
            # Only send WA for WA-enabled channels
            if not channel.is_wa:
                continue
            # Require an account to send
            account = channel.wa_account_id if 'wa_account_id' in channel._fields else None
            if not account:
                continue
            # Ensure the account-owner consistency if present in context (optional safety)
            ctx_acc = self.env.context.get('wa_account_id')
            if ctx_acc and int(ctx_acc) != account.id:
                continue
            # Determine direction: if the author is the WA partner, it's inbound; do not re-send
            if message.author_id and channel.wa_partner_id and message.author_id.id == channel.wa_partner_id.id:
                message.message_derection = 'input'
                continue

            # Outbound from Odoo to WA: send through account/provider
            try:
                # Convert HTML body to plaintext
                plain = (_html2plaintext(message.body or '') or '').strip()
                reply_to_wa_id = None
                if message.parent_id and message.parent_id.wa_message_id:
                    reply_to_wa_id = message.parent_id.wa_message_id
                if reply_to_wa_id:
                    # Se for reply, use send_reply (provider pode tratar reply threading)
                    response = account.send_reply(
                        mobile=channel.wa_partner_id.mobile,
                        message=plain,
                        reply_to=reply_to_wa_id,
                    )
                    print('WA SEND_REPLY RESPONSE:', response)
                    message.message_derection = 'output'
                    try:
                        wa_id = (
                            response.get('id')
                            or response.get('message_id')
                            or (response.get('raw') or {}).get('id')
                            or (response.get('raw') or {}).get('message_id')
                        )
                        if not wa_id:
                            raw = response.get('raw') or {}
                            key = raw.get('key') if isinstance(raw, dict) else None
                            if key and isinstance(key, dict):
                                wa_id = key.get('id')
                        message.wa_message_id = wa_id
                    except Exception:
                        pass
                elif message.attachment_ids:
                    for attachment in message.attachment_ids:
                        response = account.send_media(
                            mobile=channel.wa_partner_id.mobile,
                            caption=plain,
                            b64=attachment.datas,
                            mime=attachment.mimetype or 'application/octet-stream',
                            filename=attachment.name,
                        )
                        print('WA SEND_MEDIA RESPONSE:', response)
                        message.message_derection = 'output'
                        try:
                            wa_id = (
                                response.get('id')
                                or response.get('message_id')
                                or (response.get('raw') or {}).get('id')
                                or (response.get('raw') or {}).get('message_id')
                            )
                            if not wa_id:
                                raw = response.get('raw') or {}
                                key = raw.get('key') if isinstance(raw, dict) else None
                                if key and isinstance(key, dict):
                                    wa_id = key.get('id')
                            message.wa_message_id = wa_id
                        except Exception:
                            pass
                else:
                    if not plain:
                        continue
                    response = account.send_text(
                        mobile=channel.wa_partner_id.mobile,
                        message=plain,
                    )
                    print('WA SEND_TEXT RESPONSE:', response)
                    message.message_derection = 'output'
                    try:
                        wa_id = (
                            response.get('id')
                            or response.get('message_id')
                            or (response.get('raw') or {}).get('id')
                            or (response.get('raw') or {}).get('message_id')
                        )
                        if not wa_id:
                            raw = response.get('raw') or {}
                            key = raw.get('key') if isinstance(raw, dict) else None
                            if key and isinstance(key, dict):
                                wa_id = key.get('id')
                        message.wa_message_id = wa_id
                    except Exception:
                        pass
            except Exception:
                # swallow WA send errors to not break core message creation
                continue
        return messages


    def _message_reaction(self, content, action, partner, guest, store=None):
        self.ensure_one()
        # Check if this message is from a WhatsApp channel
        if self.model and self.res_id:
            channel = self.env[self.model].browse(self.res_id)
            if channel and getattr(channel, 'is_wa', False):
                account = getattr(channel, 'wa_account_id', None)
                if account:
                    key = {
                        'remoteJid': f"{getattr(channel.wa_partner_id, 'mobile', '')}@s.whatsapp.net",
                        'id': self.wa_message_id,
                        'fromMe': False,
                    }
                    print('DEBUG: _message_reaction WhatsApp', key, content, action)
                    if action == 'add':
                        account.send_reaction(key, content)
                    elif action == 'remove':
                        account.send_reaction(key, '')
        # Call super to keep default behavior
        return super()._message_reaction(content, action, partner, guest, store)


