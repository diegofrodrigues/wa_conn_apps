from odoo import _, api, fields, models
import base64


class Channel(models.Model):
    _inherit = 'discuss.channel'

    channel_type = fields.Selection(
        selection_add=[('whatsapp', 'whatsapp')],
        ondelete={'whatsapp': 'cascade'})
    is_wa = fields.Boolean(default=False)
    wa_partner_id = fields.Many2one('res.partner',)
    wa_account_id = fields.Many2one('wa.account', string='WA Account', help='Account used to send WhatsApp messages for this channel')
    stage_id = fields.Many2one(
        'wa.channel.stage',
        string='Stage',
        group_expand='_read_group_stage_ids',
        default=lambda self: self.env.ref('wa_conn.wa_channel_stage_new').id,
    )
    member_names = fields.Char(string='Members names', compute='_compute_member_names')
    sequence = fields.Integer(string='Sequence', default=10, index=True, help='Manual ordering within kanban column')
    tag_ids = fields.Many2many(
        'wa.channel.tag',
        'wa_channel_tag_rel',
        'channel_id',
        'tag_id',
        string='Tags',
        help='Labels to categorize WhatsApp channels.'
    )
    note = fields.Html(string="Nota", help="Observações ou anotações do canal.")
    wa_user_ids = fields.Many2many(
        'res.users',
        compute='_compute_wa_user_ids',
        string='Usuários do Canal',
        store=False,
        help='Usuários (res.users) associados ao canal via membros.'
    )
    wa_unread_count = fields.Integer(
        string='WA Unread Count',
        compute='_compute_wa_unread_count',
        store=True,
        help='Total de mensagens do canal quando não há user joined.'
    )
    wa_unread_member_count = fields.Integer(string='WA Unread Member Count', compute='_compute_wa_unread_member_count')

    @api.depends('channel_member_ids.partner_id.user_ids')
    def _compute_wa_unread_count(self):
        for rec in self:
            # Se houver qualquer membro joined, zera o contador
            if rec.channel_member_ids.filtered(lambda m: m.partner_id.user_ids):
                rec.wa_unread_count = 0
            # Caso contrário, mantém o valor atual (incrementado via wa_post_incoming)
            # Odoo só chama o compute se houver mudança nos membros

    def _compute_wa_user_ids(self):
        for rec in self:
            rec.wa_user_ids = rec.channel_member_ids.mapped('partner_id.user_ids')

    def _compute_wa_unread_member_count(self):
        Notification = self.env['mail.notification']
        current_partner = self.env.user.partner_id
        for rec in self:
            try:
                count = 0
                member = rec.channel_member_ids.filtered(lambda m: m.partner_id == current_partner)[:1]
                if member:
                    m = member[0]
                    if 'message_unread_counter' in m._fields:
                        count = m.message_unread_counter or 0
                    elif 'unread_messages_count' in m._fields:
                        count = m.unread_messages_count or 0
                    elif 'unread_counter' in m._fields:
                        count = m.unread_counter or 0
                rec.wa_unread_member_count = count
            except Exception as e:
                rec.wa_unread_member_count = 0
                try:
                    self.env['ir.logging'].sudo().create({
                        'name': 'wa_conn', 'type': 'server', 'dbname': self.env.cr.dbname,
                        'level': 'ERROR', 'message': f'wa_conn: wa_unread_member_count compute error: {e}', 'path': 'wa_conn.models.wa_channel',
                    })
                except Exception:
                    pass

    def _compute_member_names(self):
        for rec in self:
            try:
                # collect partner names from channel members
                names = rec.channel_member_ids.mapped('partner_id.name') if rec.channel_member_ids else []
                rec.member_names = ', '.join(names) if names else ''
            except Exception:
                rec.member_names = ''

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        """Expand stage groups in kanban so all stages are shown and allow drag & drop"""
        order_by = order or 'sequence,id'
        return self.env['wa.channel.stage'].search([], order=order_by)
    
    @api.model
    def wa_get_or_create_for_partner(self, partner):
        channel = self.sudo().search([('is_wa', '=', True), ('wa_partner_id', '=', partner.id)], limit=1)
        if channel:
            return channel
        vals = {
            'name': partner.name,
            'channel_type': 'channel',
            'is_wa': True,
            'wa_partner_id': partner.id,
            'avatar_128': partner.avatar_128,
        }
        if partner.image_1920:
            vals['image_128'] = partner.image_1920
        return self.sudo().create(vals)

    def wa_ensure_member(self, partner):
        Member = self.env['discuss.channel.member'].sudo()
        for ch in self:
            if not ch.channel_member_ids.filtered(lambda m: m.partner_id == partner):
                Member.create({'channel_id': ch.id, 'partner_id': partner.id})
        return True

    def wa_post_incoming(self, dto, partner):
        """Posta uma mensagem de entrada (com skip de saída)."""
        print(vars(dto))
        self.ensure_one()
        attachments = []
        if dto.has_attachment():
            b64 = dto.attachment_b64
            if isinstance(b64, str) and b64.strip().startswith('data:') and ',' in b64:
                b64 = b64.split(',', 1)[1]
            # Build a friendly filename when not provided (Voice/Image/Video + extension)
            mime = (getattr(dto, 'mime_type', None) or '').lower()
            fname = dto.attachment_name or ''
            def _guess_ext(mt):
                mapping = {
                    'image/jpeg': '.jpeg', 'image/jpg': '.jpg', 'image/png': '.png', 'image/gif': '.gif', 'image/webp': '.webp',
                    'video/mp4': '.mp4', 'video/webm': '.webm', 'video/3gpp': '.3gp', 'video/3gp': '.3gp',
                    'audio/mpeg': '.mp3', 'audio/mp3': '.mp3', 'audio/ogg': '.ogg', 'audio/aac': '.aac', 'audio/wav': '.wav', 'audio/x-wav': '.wav', 'audio/mp4': '.m4a', 'audio/m4a': '.m4a',
                    'application/pdf': '.pdf',
                }
                return mapping.get(mt)
            def _default_ext(mt):
                if mt.startswith('image/'):
                    return '.jpeg'
                if mt.startswith('video/'):
                    return '.mp4'
                if mt.startswith('audio/'):
                    return '.mp3'
                return '.bin'
            def _prefix(mt):
                if mt.startswith('image/'):
                    return 'Image'
                if mt.startswith('video/'):
                    return 'Video'
                if mt.startswith('audio/'):
                    return 'Voice'
                return 'File'
            def _ensure_ext(name, mt):
                # append extension if missing
                if name and '.' in name:
                    return name
                return (name or '') + (_guess_ext(mt) or _default_ext(mt or ''))
            if not fname:
                ts = fields.Datetime.now().strftime('%Y%m%d-%H%M%S')
                ext = _guess_ext(mime) or _default_ext(mime or '')
                fname = f"{_prefix(mime)}-{ts}{ext}"
            else:
                # If name has no extension but mime is known, append one
                fname = _ensure_ext(fname, mime)
            # Decodifica base64 para bytes antes de passar ao message_post
            try:
                content = base64.b64decode(b64)
            except Exception:
                content = b64  # fallback
            attachments = [(fname, content)]

        # Determina o autor correto da mensagem
        author_id = partner.id
        if getattr(dto, 'from_me', False):
            # Se canal tem user_id, usa ele; senão, author_id recebe o id da company correta
            if hasattr(self, 'user_id') and self.user_id:
                author_id = self.user_id.id
            else:
                company = self.wa_account_id.company_id if self.wa_account_id and self.wa_account_id.company_id else self.env.company
                author_id = company.id

        # Incrementa wa_unread_count se não houver user joined
        if not self.channel_member_ids.filtered(lambda m: m.partner_id.user_ids):
            self.wa_unread_count += 1
            # Dispara notificação para todos os usuários do sistema
            all_users = self.env['res.users'].search([])
            all_partners = all_users.mapped('partner_id').ids
            self.wa_broadcast()
        # Se houver qualquer membro, zera wa_unread_count
        else:
            self.wa_unread_count = 0

        msg = self.with_context(wa_skip_send=True).sudo().message_post(
            body=dto.message or '',
            message_type='whatsapp',
            subtype_xmlid="mail.mt_comment",
            author_id=author_id,
            attachments=attachments,
        )
        # Ajustes pós-criação (voz e metadados)
        if msg and msg.attachment_ids:
            for attachment in msg.attachment_ids:
                mt = (attachment.mimetype or '').lower()
                if mt in ('audio/mpeg', 'audio/mp3', 'audio/ogg'):
                    self.env['discuss.voice.metadata'].sudo().create({'attachment_id': attachment.id})
        if msg and getattr(msg, '_fields', {}).get('wa_message_id'):
            msg.sudo().write({'wa_message_id': dto.message_id, 'message_derection': 'input'})

        return msg
    
    def wa_broadcast(self):
        """Envia notificação customizada via bus para todos os usuários informados."""
        users = self.env['res.users'].search([])
        for user in users:
            self.env['bus.bus']._sendone(
                ('res.users', user.id),
                'simple_notification',
                {
                    'type': 'info',
                    'channel_id': self.id,
                    'message': 'Nova mensagem em canal WhatsApp sem membros',
                }
            )