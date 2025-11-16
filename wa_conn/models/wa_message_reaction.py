from odoo import models, fields, api



class WaMessageReaction(models.Model):
    _inherit = 'mail.message.reaction'


    @api.model
    def add_reaction(self, message_id, content, partner=None):
        """
        Adiciona uma reação a uma mensagem WhatsApp e envia para o provider se canal for WhatsApp.
        """
        message = self.env['mail.message'].browse(message_id)
        if not message or not message.model or not message.res_id:
            return False
        channel = self.env[message.model].browse(message.res_id)
        if not channel or not getattr(channel, 'is_wa', False):
            return False
        partner = partner or self.env.user.partner_id
        guest = self.env['mail.guest']
        # Envia para o provider
        account = channel.wa_account_id if 'wa_account_id' in channel._fields else None
        if account:
            key = {
                'remoteJid': f"{channel.wa_partner_id.mobile}@s.whatsapp.net",
                'id': message.wa_message_id,  # Char do WhatsApp
                'fromMe': False,
            }
            print('DEBUG: Chamando send_reaction', key, content)
            account.send_reaction(key, content)
        message._message_reaction(content, "add", partner, guest)
        return True


    @api.model
    def remove_reaction(self, message_id, content, partner=None):
        """
        Remove uma reação de uma mensagem WhatsApp e envia para o provider se canal for WhatsApp.
        """
        message = self.env['mail.message'].browse(message_id)
        if not message or not message.model or not message.res_id:
            return False
        channel = self.env[message.model].browse(message.res_id)
        if not channel or not getattr(channel, 'is_wa', False):
            return False
        partner = partner or self.env.user.partner_id
        guest = self.env['mail.guest']
        # Envia para o provider
        account = channel.wa_account_id if 'wa_account_id' in channel._fields else None
        if account:
            key = {
                'remoteJid': f"{channel.wa_partner_id.mobile}@s.whatsapp.net",
                'id': message.wa_message_id,  # Char do WhatsApp
                'fromMe': False,
            }
            print('DEBUG: Chamando send_reaction', key, content)
            account.send_reaction(key, content or '')
        if content:
            message._message_reaction(content, "remove", partner, guest)
        else:
            # Remove todas as reações do parceiro para essa mensagem
            reactions = self.search([
                ('message_id', '=', message.id),
                ('partner_id', '=', partner.id),
            ])
            reactions.unlink()
        return True
