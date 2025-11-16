import re
import base64
import requests
import logging
from odoo import api, fields, models, _
from odoo.addons.wa_conn.models import dto

_logger = logging.getLogger(__name__)


class WAAccountEvolution(models.Model):
    """
    WhatsApp Account Evolution Extension
    
    Este modelo estende wa.account adicionando campos específicos do provider Evolution.
    Os campos só existem quando o plugin wa_conn_evolution está instalado.
    """
    _inherit = 'wa.account'
    
    # ==================== PROVIDER REGISTRATION ====================
    # Adiciona 'evolution' como opção válida no campo provider
    provider = fields.Selection(
        selection_add=[('evolution', 'Evolution API')],
        ondelete={'evolution': 'cascade'}
    )
    
    # ==================== CAMPOS ESPECÍFICOS DO EVOLUTION ====================
    # Instance Name (Technical)
    instance_name = fields.Char(
        string="Evolution Instance Name",
        help="Technical instance name used in Evolution API. Gerado automaticamente a partir do nome da conta.",
        readonly=True,
        store=True,
    )
    
    # API Configuration
    api_url = fields.Char(
        string="API URL",
        tracking=True,
        help="Evolution API base URL (ex: https://your-evolution-api.com)"
    )
    
    api_key = fields.Char(
        string="API Key",
        help="API Key para autenticação na Evolution API"
    )
    
    # QR Code
    qr_code = fields.Image(
        string="QR Code",
        help="QR Code for WhatsApp connection",
        max_width=200,
        max_height=200,
        store=True,
        readonly=False,
    )
    
    # Instance Settings
    reject_call = fields.Boolean(
        string="Reject Call", 
        default=False,
        help="Automatically reject incoming calls"
    )
    
    ignore_group = fields.Boolean(
        string="Ignore Group", 
        default=False,
        help="Ignore messages from groups"
    )
    
    always_online = fields.Boolean(
        string="Always Online", 
        default=False,
        help="Keep the instance always shown as online"
    )
    
    view_message = fields.Boolean(
        string="Mark as Read", 
        default=False,
        help="Automatically mark messages as read"
    )
    
    sync_history = fields.Boolean(
        string="Sync History", 
        default=False,
        help="Sync message history when connecting"
    )
    
    view_status = fields.Boolean(
        string="View Status", 
        default=False,
        help="Automatically view contact status updates"
    )
    
    call_rejected_message = fields.Char(
        string="Call Rejected Message",
        help="Message sent when a call is rejected"
    )
    
    # Webhook Settings
    enable_webhook = fields.Boolean(
        string="Enable Webhook", 
        default=False,
        help="Enable webhook to receive events from Evolution API"
    )
    
    base64_webhook = fields.Boolean(
        string="Base64 in Webhook", 
        default=False,
        help="Include media as base64 in webhook payload"
    )
    
    # Webhook Events
    api_events_ids = fields.Many2many(
        'wa.api.event',
        'wa_account_api_event_rel',
        'account_id',
        'event_id',
        string="Webhook Events",
        help="Evolution API events to receive via webhook"
    )
    
    # Instance Status
    instance_created = fields.Boolean(
        string="Instance Created",
        default=False,
        readonly=True,
        help="Indicates whether the Evolution instance was successfully created"
    )

    @api.model
    def _get_available_providers(self):
        """
        Garante que 'evolution' apareça como opção de provider, mesmo sem modelo wa.provider.evolution.
        """
        # Busca opções do base
        base_providers = super()._get_available_providers()
        # Adiciona evolution se não estiver
        found = any(p[0] == 'evolution' for p in base_providers)
        if not found:
            base_providers.append(('evolution', 'Evolution API'))
        return base_providers

    # ==================== HELPERS EVOLUTION ====================
    def _headers(self):
        """Retorna headers para Evolution API"""
        if self.provider != 'evolution':
            return super()._headers() if hasattr(super(), '_headers') else {}
        
        return {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

    def _fmt_number(self, mobile):
        """Formata número de telefone"""
        if self.provider != 'evolution':
            return super()._fmt_number(mobile) if hasattr(super(), '_fmt_number') else mobile
        
        m = str(mobile or '').strip().lstrip('+')
        return f'+{m}' if m else None

    def _get_media_type(self, filename):
        """Detecta tipo de mídia baseado na extensão do arquivo"""
        if self.provider != 'evolution':
            return super()._get_media_type(filename) if hasattr(super(), '_get_media_type') else 'document'
        
        if not filename:
            return 'document'
        ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
        image_exts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
        video_exts = ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm']
        audio_exts = ['mp3', 'ogg', 'wav', 'aac', 'flac', 'm4a', 'opus']
        if ext in image_exts:
            return 'image'
        elif ext in video_exts:
            return 'video'
        elif ext in audio_exts:
            return 'audio'
        return 'document'

    def _get_mime_type(self, filename):
        """Retorna MIME type baseado na extensão do arquivo"""
        if self.provider != 'evolution':
            return super()._get_mime_type(filename) if hasattr(super(), '_get_mime_type') else 'application/octet-stream'
        
        if not filename:
            return 'application/octet-stream'
        ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
        mime_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'mp3': 'audio/mpeg',
            'mp4': 'video/mp4',
            'txt': 'text/plain',
            'zip': 'application/zip',
        }
        return mime_map.get(ext, 'application/octet-stream')

    # ==================== MÉTODOS DE INTEGRAÇÃO EVOLUTION ====================
    def normalize_inbound(self, raw, request=None):
        """
        Normaliza o payload Evolution extraindo os campos diretamente e preenchendo o DTO corretamente.
        """
        # Se não for provider evolution, chama o método base/próximo na cadeia
        if self.provider != 'evolution':
            return super().normalize_inbound(raw, request=request)
        
        raw = raw or {}
        data = raw.get('data') or raw
        batch = data.get('messages') or data.get('events') or data.get('entries')
        result = []
        items = batch if isinstance(batch, list) else [data]
        for item in items:
            key = (item or {}).get('key', {})
            remote_jid = str(item.get('remoteJid') or key.get('remoteJid') or item.get('from') or '')
            mobile = remote_jid.split('@', 1)[0] if remote_jid else None
            from_me = bool(item.get('from_me') or key.get('fromMe') or False)
            push_name = item.get('push_name') or item.get('pushName') or item.get('senderName') or item.get('contact')
            message_id = item.get('message_id') or item.get('id') or key.get('id')
            event = raw.get('event') or item.get('type') or 'messages.upsert'
            message_dict = item.get('message') or item.get('msg') or item.get('content') or {}
            message = item.get('text') or item.get('caption') or message_dict.get('conversation') or ''
            if isinstance(message, dict):
                message = message.get('conversation') or message.get('caption') or message.get('text') or ''
            message = message.strip() if isinstance(message, str) else ''
            result.append(dto.NormalizedPayload(
                provider='evolution',
                instance=self.get_instance_name(),
                event=event,
                message_id=message_id,
                remote_jid=remote_jid,
                mobile=mobile,
                from_me=from_me,
                push_name=push_name,
                message=message,
                raw=raw,
            ))
        return result

    def inbound_handle(self, raw, request=None):
        # Se não for provider evolution, chama o método base/próximo na cadeia
        if self.provider != 'evolution':
            return super().inbound_handle(raw, request=request)
        
        dto_items = self.normalize_inbound(raw, request=request) or []
        print(vars(dto_items[0]))
        if not isinstance(dto_items, list):
            dto_items = [dto_items]
        if not dto_items:
            return {'status': 'ignored', 'reason': 'empty'}
        results = []
        env = self.env
        Partner = env['res.partner'].sudo()
        Channel = env['discuss.channel'].sudo()
        for dto in dto_items:
            event = (getattr(dto, 'event', '') or '').lower()
            if event != 'messages.upsert':
                results.append({'status': 'ignored', 'event': event or None})
                continue
            mobile = (getattr(dto, 'mobile', '') or '').strip()
            if not mobile:
                results.append({'status': 'ignored', 'reason': 'no_mobile'})
                continue
            push_name = getattr(dto, 'push_name', None)
            from_me = getattr(dto, 'from_me', False)
            name_arg = push_name if not from_me else None
            partner = Partner.wa_get_or_create_by_mobile(mobile, name=name_arg)
            # Reação: processa e pula o resto
            if self.inbound_handle_reaction(dto, partner):
                results.append({'status': 'reaction', 'mobile': mobile})
                continue
            # Detecta reply: contextInfo.stanzaId
            raw = getattr(dto, 'raw', {})
            data = raw.get('data', {})
            message_dict = data.get('message', {})
            context_info = None
            if 'extendedTextMessage' in message_dict:
                ext = message_dict['extendedTextMessage']
                context_info = ext.get('contextInfo') if isinstance(ext, dict) else None
            if not context_info:
                context_info = data.get('contextInfo')
            parent_wa_id = context_info.get('stanzaId') if context_info else None
            if parent_wa_id:
                # Chama handler de reply
                reply_result = self.inbound_handle_reply(dto, partner)
                results.append({'status': 'reply', 'mobile': mobile, 'msg_id': reply_result.get('msg_id'), 'parent_id': reply_result.get('parent_id')})
                continue
            # Só passa push_name se não for from_me
            if not from_me and (partner.name).strip() == (partner.mobile).strip():
                partner.sudo().wa_update_names_from_push(mobile, push_name)
            if from_me and partner and (partner.name == _('WhatsApp Contact') or not partner.name):
                partner.sudo().write({'name': mobile})
            try:
                channel = partner.wa_get_or_create_channel(account=self)
            except Exception:
                domain = [('is_wa', '=', True), ('wa_partner_id', '=', partner.id)]
                if 'wa_account_id' in Channel._fields:
                    domain.append(('wa_account_id', '=', self.id))
                channel = Channel.search(domain, limit=1)
                if not channel:
                    vals = {
                        'name': partner.name,
                        'channel_type': 'channel',
                        'is_wa': True,
                        'wa_partner_id': partner.id,
                    }
                    if 'wa_account_id' in Channel._fields:
                        vals['wa_account_id'] = self.id
                    channel = Channel.create(vals)
            try:
                rjid = getattr(dto, 'remote_jid', None) or mobile
                img_b64 = self.get_profile_image(rjid)
                if img_b64:
                    if isinstance(img_b64, (bytes, bytearray)):
                        img_b64 = img_b64.decode()
                    if not partner.image_1920:
                        partner.sudo().write({'image_1920': img_b64})
                    vals_img = {}
                    if 'avatar_128' in channel._fields:
                        vals_img['avatar_128'] = img_b64
                    if 'image_128' in channel._fields:
                        vals_img['image_128'] = img_b64
                    if vals_img:
                        channel.sudo().write(vals_img)
            except Exception:
                pass
            mid = getattr(dto, 'message_id', None)
            if mid:
                existing = env['mail.message'].sudo().search([
                    ('model', '=', 'discuss.channel'),
                    ('res_id', '=', channel.id),
                    ('wa_message_id', '=', mid),
                ], limit=1)
                if existing:
                    results.append({'status': 'duplicate', 'channel_id': channel.id, 'msg_id': existing.id})
                    continue
            msg = channel.wa_post_incoming(dto, partner)
            results.append({'status': 'ok', 'channel_id': channel.id, 'msg_id': msg.id if msg else False})
        return {'results': results}

    def inbound_handle_reaction(self, dto, partner):
        """
        Processa reações do EvolutionAPI (reactionMessage) criando/removendo wa.message.reaction.
        """
        # O DTO deve conter raw['data']['message']['reactionMessage'] se for reação
        raw = getattr(dto, 'raw', {})
        data = raw.get('data', {})
        message_dict = data.get('message', {})
        if data.get('messageType') == 'reactionMessage' and 'reactionMessage' in message_dict:
            reaction = message_dict['reactionMessage']
            reacted_msg_id = reaction['key']['id']
            emoji = reaction.get('text')
            from_me = reaction['key'].get('fromMe')
            mail_message = self.env['mail.message'].sudo().search([('wa_message_id', '=', reacted_msg_id)], limit=1)
            if mail_message:
                reaction_model = self.env['mail.message.reaction'].sudo()
                if emoji:
                    reaction_model.add_reaction(mail_message.id, emoji, partner=partner)
                else:
                    reaction_model.remove_reaction(mail_message.id, emoji, partner=partner)
            return True
        return False
    
    def inbound_handle_reply(self, dto, partner):
        """
        Processa replies recebidos do Evolution API, criando mail.message com parent_id.
        Suporta contextInfo tanto em extendedTextMessage quanto no root do payload.
        """
        raw = getattr(dto, 'raw', {})
        data = raw.get('data', {})
        message_dict = data.get('message', {})
        # contextInfo pode estar em extendedTextMessage/contextInfo ou direto em data['contextInfo']
        context_info = None
        if 'extendedTextMessage' in message_dict:
            ext = message_dict['extendedTextMessage']
            context_info = ext.get('contextInfo') if isinstance(ext, dict) else None
        if not context_info:
            context_info = data.get('contextInfo')
        parent_wa_id = context_info.get('stanzaId') if context_info else None
        parent_message = None
        if parent_wa_id:
            parent_message = self.env['mail.message'].sudo().search([
                ('wa_message_id', '=', parent_wa_id)
            ], limit=1)
        channel = partner.wa_get_or_create_channel(account=self)
        vals = {
            'author_id': partner.id,
            'body': getattr(dto, 'message', ''),
            'message_type': 'whatsapp',
            'subtype_xmlid':'mail.mt_comment',
        }
        if parent_message:
            vals['parent_id'] = parent_message.id
        msg = channel.with_context(wa_skip_send=True).sudo().message_post(**vals)
        # Atualiza campos customizados após criação
        msg.sudo().write({
            'wa_message_id': getattr(dto, 'message_id', None),
            'is_wa': True,
        })
        return {'status': 'ok', 'msg_id': msg.id if hasattr(msg, 'id') else msg, 'parent_id': parent_message.id if parent_message else None}

    def send_text(self, mobile, message):
        """
        Envia mensagem de texto via Evolution API.
        Só executa se provider == 'evolution', caso contrário delega para super().
        """
        _logger.info(f"[Evolution.send_text] Called - Account: {self.name} (ID: {self.id})")
        _logger.info(f"[Evolution.send_text] Provider: {self.provider}")
        _logger.info(f"[Evolution.send_text] Class: {self.__class__.__name__}")
        _logger.info(f"[Evolution.send_text] MRO: {' -> '.join([c.__name__ for c in self.__class__.__mro__[:5]])}")
        
        # Se não for provider evolution, delega para próximo na cadeia MRO
        if self.provider != 'evolution':
            _logger.info(f"[Evolution.send_text] SKIPPING - provider is '{self.provider}', delegating to super()")
            return super().send_text(mobile, message)
        
        _logger.info(f"[Evolution.send_text] EXECUTING - This is Evolution provider")
        
        number = self._fmt_number(mobile)
        if not number:
            _logger.warning(f"[Evolution.send_text] Invalid mobile: {mobile}")
            return {'ok': False, 'error': 'invalid_mobile'}
            
        instance_name = self.get_instance_name()
        url = f"{self.api_url}/message/sendText/{instance_name}"
        payload = {'number': number, 'text': message or ''}
        
        _logger.info(f"[Evolution.send_text] URL: {url}")
        _logger.info(f"[Evolution.send_text] Payload: {payload}")
        
        try:
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=20)
            ok = 200 <= resp.status_code < 300
            try:
                data = resp.json()
            except Exception:
                data = {'text': resp.text}
            
            _logger.info(f"[Evolution.send_text] Response status: {resp.status_code}")
            _logger.info(f"[Evolution.send_text] Response data: {data}")
            
            return {
                'ok': ok,
                'id': data.get('id') or data.get('message_id'),
                'raw': data,
                'status_code': resp.status_code,
            }
        except Exception as e:
            _logger.error(f"[Evolution] Error: {str(e)}")
            return {'ok': False, 'error': str(e), 'status_code': 0}

    def send_media(self, mobile, *, caption='', b64=None, mime=None, filename=None):
        # Se não for provider evolution, chama o método base/próximo na cadeia
        if self.provider != 'evolution':
            return super().send_media(mobile, caption=caption, b64=b64, mime=mime, filename=filename)
        
        number = self._fmt_number(mobile)
        if not number:
            return {'ok': False, 'error': 'invalid_mobile'}
        media_b64 = b64
        if isinstance(media_b64, (bytes, bytearray)):
            media_b64 = media_b64.decode()
        elif isinstance(media_b64, str):
            media_b64 = media_b64
        else:
            media_b64 = ''
        if not media_b64:
            return {'ok': False, 'error': 'empty_media'}
        eff_mime = mime or (self._get_mime_type(filename) if filename else None) or 'application/octet-stream'
        mt_root = self._get_media_type(filename) if filename else 'document'
        instance_name = self.get_instance_name()
        url = f"{self.api_url}/message/sendMedia/{instance_name}"
        payload = {
            'number': number,
            'caption': caption or '',
            'mediatype': mt_root,
            'mimetype': eff_mime,
            'media': media_b64,
            'fileName': filename or 'file.bin',
        }
        try:
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=40)
            ok = 200 <= resp.status_code < 300
            try:
                data = resp.json()
            except Exception:
                data = {'text': resp.text}
            return {
                'ok': ok,
                'id': data.get('id') or data.get('message_id'),
                'raw': data,
                'status_code': resp.status_code,
            }
        except Exception as e:
            return {'ok': False, 'error': str(e), 'status_code': 0}

    def send_reaction(self, key, reaction):
        """
        Envia uma reação para uma mensagem via Evolution API.
        Args:
            key (dict): Deve conter 'remoteJid', 'id' e 'fromMe'.
            reaction (str): Emoji da reação (ex: '🚀').
        Returns:
            dict: Resultado da requisição.
        """
        # Se não for provider evolution, chama o método base/próximo na cadeia
        if self.provider != 'evolution':
            return super().send_reaction(key, reaction)
        
        instance_name = self.get_instance_name()
        url = f"{self.api_url}/message/sendReaction/{instance_name}"
        # Monta o payload conforme Evolution API
        payload = {
            "key": {
                "remoteJid": key.get("remoteJid"),
                "fromMe": key.get("fromMe", True),
                "id": key.get("id"),
            },
            "reaction": reaction or '',
        }
        try:
            print('WA SEND_REACTION PAYLOAD:', payload)
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=20)
            ok = 200 <= resp.status_code < 300
            try:
                data = resp.json()
            except Exception:
                data = {'text': resp.text}
            print('WA SEND_REACTION RESPONSE:', data)
            return {
                'ok': ok,
                'raw': data,
                'status_code': resp.status_code,
            }
        except Exception as e:
            print('WA SEND_REACTION ERROR:', str(e))
            return {'ok': False, 'error': str(e), 'status_code': 0}
    
    def send_reply(self, mobile, message, reply_to=None, quoted_message=None):
        """
        Envia uma mensagem de texto em resposta a outra mensagem (reply threading) via Evolution API.
        Args:
            mobile (str): Número do destinatário (remoteJid ou número puro).
            message (str): Texto da mensagem.
            reply_to (str|None): wa_message_id da mensagem a ser referenciada como reply.
            quoted_message (str|None): Conteúdo da mensagem original (opcional, para exibir preview do texto).
        Returns:
            dict: Resultado da requisição.
        """
        # Se não for provider evolution, chama o método base/próximo na cadeia
        if self.provider != 'evolution':
            return super().send_reply(mobile, message, reply_to=reply_to, quoted_message=quoted_message)
        
        number = self._fmt_number(mobile)
        if not number:
            return {'ok': False, 'error': 'invalid_mobile'}
        instance_name = self.get_instance_name()
        url = f"{self.api_url}/message/sendText/{instance_name}"
        payload = {
            'number': number,
            'text': message or '',
        }
        if reply_to:
            quoted = {'key': {'id': reply_to}}
            if quoted_message:
                quoted['message'] = {'conversation': quoted_message}
            payload['quoted'] = quoted
        try:
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=20)
            ok = 200 <= resp.status_code < 300
            try:
                data = resp.json()
            except Exception:
                data = {'text': resp.text}
            return {
                'ok': ok,
                'id': data.get('id') or data.get('message_id'),
                'raw': data,
                'status_code': resp.status_code,
            }
        except Exception as e:
            return {'ok': False, 'error': str(e), 'status_code': 0}

    def create_instance(self):
        """Cria instância no Evolution API"""
        if self.provider != 'evolution':
            return super().create_instance()
        
        instance_name = self.get_instance_name()
        data = {
            "instanceName": instance_name,
            "integration": "WHATSAPP-BAILEYS",
            "rejectCall": self.reject_call,
            "msgCall": self.call_rejected_message or '',
            "groupsIgnore": self.ignore_group,
            "alwaysOnline": self.always_online,
            "readMessages": self.view_message,
            "readStatus": self.view_status,
            "syncFullHistory": self.sync_history,
            "qrcode": True,
        }
        events = [e.name for e in self.api_events_ids] or ['APPLICATION_STARTUP', 'QRCODE_UPDATED']
        if self.enable_webhook:
            data["webhook"] = {
                "url": self.webhook_url,
                "byEvents": bool(events),
                "base64": bool(self.base64_webhook),
                "headers": {"webhook_key": self.webhook_key},
                "events": events,
            }
        url = f"{self.api_url}/instance/create"
        try:
            resp = requests.post(url, json=data, headers=self._headers(), timeout=30)
            ok = resp.status_code in (200, 201)
            j = None
            try:
                j = resp.json()
            except Exception:
                j = None
            qr_b64 = None
            if isinstance(j, dict):
                qr_b64 = j.get('qrcode') or j.get('base64')
                if qr_b64:
                    if isinstance(qr_b64, str) and qr_b64.startswith('data:') and ',' in qr_b64:
                        qr_b64 = qr_b64.split(',', 1)[1]
                    self.sudo().write({'qr_code': qr_b64})
            return {'ok': ok, 'status_code': resp.status_code, 'text': resp.text, 'json': j}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'status_code': 0}

    def delete_instance(self):
        """Deleta instância no Evolution API"""
        if self.provider != 'evolution':
            return super().delete_instance()
        
        instance_name = self.get_instance_name()
        url = f"{self.api_url}/instance/delete/{instance_name}"
        try:
            resp = requests.delete(url, headers=self._headers(), timeout=20)
            ok = 200 <= resp.status_code < 300
            return {'ok': ok, 'status_code': resp.status_code, 'text': resp.text}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'status_code': 0}

    def check_status(self):
        """Verifica status da conexão no Evolution API"""
        if self.provider != 'evolution':
            return super().check_status()
        
        self.ensure_one()
        
        instance_name = self.get_instance_name()
        url = f"{self.api_url}/instance/connectionState/{instance_name}"
        
        try:
            resp = requests.get(url, headers=self._headers(), timeout=15)
            
            if resp.status_code != 200:
                from odoo.exceptions import UserError
                raise UserError(_('Failed to check status (Status: %s)') % resp.status_code)
            
            try:
                data = resp.json()
            except Exception:
                from odoo.exceptions import UserError
                raise UserError(_('Invalid response from Evolution server'))
            
            state = (data.get('instance') or {}).get('state') or 'unknown'
            
            # Mapeia estados do Evolution
            if state == 'open':
                self.sudo().write({'state': 'connected'})
                msg = _('Instance is connected! ✅')
                msg_type = 'success'
            elif state == 'close':
                self.sudo().write({'state': 'disconnected'})
                msg = _('Instance is disconnected ❌')
                msg_type = 'warning'
            elif state == 'connecting':
                self.sudo().write({'state': 'connecting'})
                msg = _('Instance is connecting... ⏳')
                msg_type = 'info'
            else:
                msg = _('Instance status: %s') % state
                msg_type = 'info'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Status Check'),
                    'message': msg,
                    'type': msg_type,
                    'sticky': False,
                }
            }
            
        except Exception as e:
            from odoo.exceptions import UserError
            _logger.error(f"Error checking Evolution instance status: {str(e)}")
            raise UserError(_('Error checking status: %s') % str(e))

    def connect(self):
        """Conecta instância no Evolution API e obtém QR Code"""
        if self.provider != 'evolution':
            return super().connect()
        
        instance_name = self.get_instance_name()
        url = f"{self.api_url}/instance/connect/{instance_name}"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=20)
            ok = 200 <= resp.status_code < 300
            payload = None
            try:
                payload = resp.json()
            except Exception:
                payload = None
            b64 = payload.get('base64') if isinstance(payload, dict) else None
            # Atualiza os campos no registro
            vals = {'state': 'connecting'}
            if b64:
                # Remove data URI prefix se existir
                if isinstance(b64, str) and b64.startswith('data:') and ',' in b64:
                    b64 = b64.split(',', 1)[1]
                vals['qr_code'] = b64
            self.sudo().write(vals)
            print(f"[WAAccountEvolution.connect] payload: {payload}")
            return {'ok': ok, 'qrcode_b64': b64, 'payload': payload, 'text': resp.text, 'status_code': resp.status_code}
        except Exception as e:
            self.sudo().write({'state': 'disconnected'})
            return {'ok': False, 'error': str(e), 'status_code': 0}

    def restart(self):
        """Reinicia instância no Evolution API"""
        if self.provider != 'evolution':
            return super().restart()
        
        self.ensure_one()
        
        instance_name = self.get_instance_name()
        url = f"{self.api_url}/instance/restart/{instance_name}"
        headers = self._headers()
        
        _logger.info(f"[Evolution.restart] Account: {self.name} (ID: {self.id})")
        _logger.info(f"[Evolution.restart] URL: {url}")
        _logger.info(f"[Evolution.restart] API Key present: {bool(self.api_key)}")
        _logger.info(f"[Evolution.restart] API Key length: {len(self.api_key) if self.api_key else 0}")
        _logger.info(f"[Evolution.restart] Headers: {headers}")
        
        try:
            # POST /instance/restart/{instance} com apikey no header
            resp = requests.post(url, headers=headers, timeout=20)
            ok = 200 <= resp.status_code < 300
            
            try:
                payload = resp.json()
            except Exception:
                payload = None
            
            _logger.info(f"[Evolution.restart] Response status: {resp.status_code}")
            _logger.info(f"[Evolution.restart] Payload: {payload}")
            
            if ok:
                # Atualiza estado para connecting
                self.sudo().write({'state': 'connecting'})
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Instance restarted successfully! Please wait for reconnection...'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                from odoo.exceptions import UserError
                raise UserError(_('Failed to restart instance (Status: %s): %s') % (resp.status_code, payload))
                
        except requests.exceptions.RequestException as e:
            from odoo.exceptions import UserError
            _logger.error(f"Error restarting Evolution instance: {str(e)}")
            raise UserError(_('Connection error: %s') % str(e))
        except Exception as e:
            from odoo.exceptions import UserError
            _logger.error(f"Error restarting Evolution instance: {str(e)}")
            raise UserError(_('Error restarting instance: %s') % str(e))

    def disconnect(self):
        """Desconecta e faz logout da instância no Evolution API"""
        if self.provider != 'evolution':
            return super().disconnect()
        
        instance_name = self.get_instance_name()
        url = f"{self.api_url}/instance/logout/{instance_name}"
        try:
            resp = requests.delete(url, headers=self._headers(), timeout=20)
            ok = 200 <= resp.status_code < 300
            # Sempre limpa o estado e o QR code
            self.sudo().write({'state': 'disconnected', 'qr_code': False})
            return {'ok': ok, 'status_code': resp.status_code, 'text': resp.text}
        except Exception as e:
            self.sudo().write({'state': 'disconnected', 'qr_code': False})
            return {'ok': False, 'error': str(e), 'status_code': 0}
        
    def refresh_qrcode(self):
        """Atualiza QR Code reconectando"""
        if self.provider != 'evolution':
            return super().refresh_qrcode()
        
        self.connect()

    def get_profile_image(self, remote_jid=None):
        """Obtém imagem de perfil do contato"""
        if self.provider != 'evolution':
            return super().get_profile_image(remote_jid)
        
        if not remote_jid:
            return False
        headers = self._headers()
        instance_name = self.get_instance_name()
        url = f"{self.api_url}/chat/fetchProfilePictureUrl/{instance_name}"
        try:
            num = str(remote_jid)
            if '@' in num:
                num = num.split('@', 1)[0]
            if num and not num.startswith('+'):
                num = f'+{num}'
            r = requests.post(url, json={'number': num}, headers=headers, timeout=15)
            data = r.json()
            pic_url = data.get('profilePictureUrl')
            if not pic_url:
                return False
            img = requests.get(pic_url, timeout=20)
            if img.status_code == 200:
                return base64.b64encode(img.content)
        except Exception:
            return False
        return False
    
    # ==================== MÉTODOS ====================
    @api.onchange('name')
    def _onchange_name_generate_instance_name(self):
        """Auto-gera instance_name sempre que name é alterado"""
        if self.name and self.provider == 'evolution':
            self.instance_name = self._generate_instance_name(self.name)
    
    @api.model
    def _generate_instance_name(self, account_name):
        """
        Gera um nome técnico válido para a instância Evolution a partir do nome amigável.
        
        Regras:
        - Remove caracteres especiais
        - Converte para lowercase
        - Substitui espaços por underscores
        - Limita a 50 caracteres
        
        Args:
            account_name (str): Nome amigável da conta
            
        Returns:
            str: Nome técnico válido para Evolution API
        """
        if not account_name:
            return ''
        
        # Remove acentos e caracteres especiais, mantém apenas letras, números e espaços
        clean = re.sub(r'[^a-zA-Z0-9\s]', '', account_name)
        
        # Converte para lowercase e substitui espaços por underscores
        clean = clean.lower().replace(' ', '_')
        
        # Remove underscores múltiplos
        clean = re.sub(r'_+', '_', clean)
        
        # Remove underscores no início e fim
        clean = clean.strip('_')
        
        # Limita a 50 caracteres
        return clean[:50]
    
    def get_instance_name(self):
        """
        Retorna o instance_name a ser usado na Evolution API.
        Sempre gerado automaticamente a partir do nome da conta.
        """
        self.ensure_one()
        generated = self._generate_instance_name(self.name)
        if self.instance_name != generated:
            self.instance_name = generated
        return generated or 'default_instance'

    # CRUD
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('provider') == 'evolution':
                name = vals.get('name')
                if name:
                    vals['instance_name'] = self._generate_instance_name(name)
        return super().create(vals_list)
    
    def write(self, vals):
        res = super().write(vals)
        # Atualiza instance_name se o nome mudou e provider for evolution
        if 'name' in vals and self.provider == 'evolution':
            new_instance_name = self._generate_instance_name(vals['name'])
            self.sudo().write({'instance_name': new_instance_name})
        return res