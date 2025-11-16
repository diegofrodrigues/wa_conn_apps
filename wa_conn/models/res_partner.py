from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def wa_get_or_create_by_mobile(self, mobile, name=None):
        Partner = self.sudo()
        partner = Partner.search([('mobile', '=', mobile)], limit=1)
        clean_name = (name or '').strip()
        # If provided name equals the mobile (or is empty), treat it as missing
        if clean_name and mobile and clean_name == str(mobile):
            clean_name = ''
        if partner:
            # If partner was previously created with mobile as name or empty/default, update to clean_name
            current = (partner.name or '').strip()
            default_label = _('WhatsApp Contact')
            if clean_name and (not current or current == str(mobile) or current == default_label):
                partner.write({'name': clean_name})
            elif current == str(mobile):
                # No clean_name available but current is mobile: set to default label
                partner.write({'name': default_label})
            return partner
        # Create new partner with a friendly name (prefer clean_name over mobile)
        partner = Partner.create({'name': clean_name or _('WhatsApp Contact'), 'mobile': mobile})
        return partner

    def wa_get_or_create_channel(self, account=None):
        self.ensure_one()
        Channel = self.env['discuss.channel'].sudo()
        domain = [('is_wa', '=', True), ('wa_partner_id', '=', self.id)]
        if account and 'wa_account_id' in Channel._fields:
            domain.append(('wa_account_id', '=', account.id))
        channel = Channel.search(domain, limit=1)
        if channel:
            # If channel exists but has no account set, attach it
            if account and 'wa_account_id' in Channel._fields and not channel.wa_account_id:
                channel.write({'wa_account_id': account.id})
            return channel
        # If an account was provided but an existing channel with a different account exists,
        # do not reuse it; create a dedicated channel for this account.
        vals = {
            'name': self.name,
            'channel_type': 'channel',
            'is_wa': True,
            'wa_partner_id': self.id,
        }
        if account and 'wa_account_id' in Channel._fields:
            vals['wa_account_id'] = account.id
        # seed channel avatar from partner image if available
        if self.image_1920:
            if 'avatar_128' in Channel._fields:
                vals['avatar_128'] = self.image_1920
            if 'image_128' in Channel._fields:
                vals['image_128'] = self.image_1920
        return Channel.create(vals)


    @api.model
    def wa_update_names_from_push(self, mobile, name):
        """
        Atualiza o name do partner e dos canais WhatsApp cujo name == mobile.
        Args:
            mobile (str): número do contato (string, igual ao que será buscado)
            name (str): novo nome a ser aplicado
        """
        if not mobile or not name:
            return False
        Partner = self.env['res.partner'].sudo()
        Channel = self.env['discuss.channel'].sudo()
        # Atualiza partner(s) com name == mobile
        partners = Partner.search([('mobile', '=', mobile), ('name', '=', mobile)])
        print(f"[WA DEBUG] Partners encontrados para mobile={mobile}: {[p.id for p in partners]}")
        for partner in partners:
            try:
                partner.write({'name': name.strip()})
                print(f"[WA DEBUG] Partner {partner.id} atualizado para name={name.strip()}")
            except Exception as e:
                print(f"[WA DEBUG] Falha ao atualizar partner {partner.id}: {e}")
        # Atualiza canais com name == mobile e wa_partner_id correto
        for partner in partners:
            channels = Channel.search([
                ('wa_partner_id', '=', partner.id),
                ('is_wa', '=', True),
                ('name', '=', mobile)
            ])
            print(f"[WA DEBUG] Canais encontrados para partner {partner.id} e name={mobile}: {[c.id for c in channels]}")
            for channel in channels:
                try:
                    channel.write({'name': name.strip()})
                    print(f"[WA DEBUG] Canal {channel.id} atualizado para name={name.strip()}")
                except Exception as e:
                    print(f"[WA DEBUG] Falha ao atualizar canal {channel.id}: {e}")
        return True
