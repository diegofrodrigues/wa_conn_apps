# -*- coding: utf-8 -*-
import re
import base64
import requests
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.wa_conn.models import dto

_logger = logging.getLogger(__name__)


class WAAccountQuepasa(models.Model):
    """
    WhatsApp Account Quepasa Extension
    
    Este modelo estende wa.account adicionando campos específicos do provider Quepasa.
    """
    _inherit = 'wa.account'
    
    # ==================== PROVIDER REGISTRATION ====================
    # Adiciona 'quepasa' como opção válida no campo provider
    provider = fields.Selection(
        selection_add=[('quepasa', 'Quepasa')],
        ondelete={'quepasa': 'cascade'}
    )
    
    # ==================== CAMPOS ESPECÍFICOS DO QUEPASA ====================
    
    # API Configuration
    quepasa_url = fields.Char(
        string="Quepasa Server URL",
        tracking=True,
        help="URL do servidor Quepasa (ex: https://seu-quepasa.com)"
    )
    
    quepasa_bot_token = fields.Char(
        string="Bot Token",
        required=True,
        help="Token da conexão obtido da interface web do Quepasa (http://seu-servidor:31000) ou arquivo .env"
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
    
    # Webhook Settings
    quepasa_webhook_enabled = fields.Boolean(
        string="Enable Webhook", 
        default=True,
        help="Enable webhook to receive events from Quepasa"
    )
    
    # Bot Status
    bot_created = fields.Boolean(
        string="Bot Created",
        default=False,
        readonly=True,
        help="Indicates whether the Quepasa bot was successfully created"
    )

    @api.model
    def _get_available_providers(self):
        """
        Adiciona 'quepasa' como opção de provider.
        """
        base_providers = super()._get_available_providers()
        found = any(p[0] == 'quepasa' for p in base_providers)
        if not found:
            base_providers.append(('quepasa', 'Quepasa'))
        return base_providers

    # ==================== HELPERS QUEPASA ====================
    def _get_api_base_url(self):
        """Retorna URL base da API baseada na versão"""
        self.ensure_one()
        # Tanto v3 quanto v4 usam a URL base sem prefixo /v3 ou /v4
        # A diferença está na estrutura dos endpoints e payloads
        return self.quepasa_url
    
    def _headers(self, chat_id=None, track_id=None):
        """
        Headers para autenticação no Quepasa
        
        Args:
            chat_id: Número do destinatário (ex: 5511999999999) - opcional
            track_id: ID de rastreamento customizado - opcional
        
        Returns:
            dict: Headers para requisições HTTP
        """
        if self.provider != 'quepasa':
            return super()._headers() if hasattr(super(), '_headers') else {}
        
        self.ensure_one()
        
        headers = {
            "Content-Type": "application/json",
            "X-QUEPASA-TOKEN": self.quepasa_bot_token or ""
        }
        
        if chat_id:
            headers["X-QUEPASA-CHATID"] = str(chat_id)
        if track_id:
            headers["X-QUEPASA-TRACKID"] = str(track_id)
            
        return headers

    def _fmt_number(self, mobile):
        """Formata número de telefone para o padrão do Quepasa"""
        if self.provider != 'quepasa':
            return super()._fmt_number(mobile) if hasattr(super(), '_fmt_number') else mobile
        
        m = str(mobile or '').strip().lstrip('+')
        # Quepasa usa formato: 5511999999999 (sem +)
        return m if m else None

    def _get_media_type(self, filename):
        """Detecta tipo de mídia baseado na extensão do arquivo"""
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
        """Retorna mime type baseado na extensão"""
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

    # ==================== MÉTODOS DE INTEGRAÇÃO QUEPASA ====================
    def normalize_inbound(self, raw, request=None):
        """
        Normaliza o payload do Quepasa para o formato DTO padrão.
        
        Estrutura típica do Quepasa:
        {
            "id": "message_id",
            "timestamp": 1234567890,
            "from": "5511999999999",
            "participant": "5511999999999", 
            "recipient": "5511888888888",
            "text": "mensagem",
            "type": "text",
            "fromMe": false
        }
        """
        # Se não for provider quepasa, chama o método base
        if self.provider != 'quepasa':
            return super().normalize_inbound(raw, request=request)
        
        raw = raw or {}
        result = []
        
        # Quepasa pode enviar mensagem única ou array
        messages = raw if isinstance(raw, list) else [raw]
        
        for item in messages:
            mobile = str(item.get('from') or item.get('participant') or '')
            # Remove caracteres especiais se houver
            mobile = mobile.split('@')[0] if '@' in mobile else mobile
            
            from_me = bool(item.get('fromMe', False))
            message_id = item.get('id', '')
            message_type = item.get('type', 'text')
            
            # Extrai texto da mensagem
            message = ''
            if message_type == 'text':
                message = item.get('text', '')
            elif message_type in ['image', 'video', 'audio', 'document']:
                message = item.get('caption', '')
            
            # Nome do contato
            push_name = item.get('pushName') or item.get('notifyName') or ''
            
            result.append(dto.NormalizedPayload(
                provider='quepasa',
                instance='default',
                event='message',
                message_id=message_id,
                remote_jid=f"{mobile}@s.whatsapp.net",
                mobile=mobile,
                from_me=from_me,
                push_name=push_name,
                message=message,
                raw=raw,
            ))
        
        return result

    def inbound_handle(self, raw, request=None):
        """Processa mensagens recebidas do Quepasa"""
        # Se não for provider quepasa, chama o método base
        if self.provider != 'quepasa':
            return super().inbound_handle(raw, request=request)
        
        dto_items = self.normalize_inbound(raw, request=request) or []
        
        if not isinstance(dto_items, list):
            dto_items = [dto_items]
        
        if not dto_items:
            return {'status': 'ignored', 'reason': 'empty'}
        
        results = []
        env = self.env
        Partner = env['res.partner'].sudo()
        Channel = env['discuss.channel'].sudo()
        
        for dto in dto_items:
            mobile = (getattr(dto, 'mobile', '') or '').strip()
            if not mobile:
                results.append({'status': 'ignored', 'reason': 'no_mobile'})
                continue
            
            push_name = getattr(dto, 'push_name', None)
            from_me = getattr(dto, 'from_me', False)
            
            # Cria ou busca parceiro
            name_arg = push_name if not from_me else None
            partner = Partner.wa_get_or_create_by_mobile(mobile, name=name_arg)
            
            # Atualiza nome se necessário
            if not from_me and (partner.name).strip() == (partner.mobile).strip():
                partner.sudo().wa_update_names_from_push(mobile, push_name)
            
            if from_me and partner and (partner.name == _('WhatsApp Contact') or not partner.name):
                partner.sudo().write({'name': mobile})
            
            # Busca ou cria canal
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
            
            # Verifica duplicatas
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
            
            # Posta mensagem no canal
            msg = channel.wa_post_incoming(dto, partner)
            results.append({'status': 'ok', 'channel_id': channel.id, 'msg_id': msg.id if msg else False})
        
        return {'results': results}

    def send_text(self, mobile, message):
        """
        Envia mensagem de texto via Quepasa API.
        Só executa se provider == 'quepasa', caso contrário delega para super().
        """
        _logger.info(f"[Quepasa.send_text] Called - Account: {self.name} (ID: {self.id})")
        _logger.info(f"[Quepasa.send_text] Provider: {self.provider}")
        _logger.info(f"[Quepasa.send_text] Class: {self.__class__.__name__}")
        _logger.info(f"[Quepasa.send_text] MRO: {' -> '.join([c.__name__ for c in self.__class__.__mro__[:5]])}")
        
        # Se não for provider quepasa, delega para próximo na cadeia MRO
        if self.provider != 'quepasa':
            _logger.info(f"[Quepasa.send_text] SKIPPING - provider is '{self.provider}', delegating to super()")
            return super().send_text(mobile, message)
        
        _logger.info(f"[Quepasa.send_text] EXECUTING - This is Quepasa provider")
        _logger.info(f"[Quepasa.send_text] Mobile: {mobile}, Message length: {len(message) if message else 0}")
        _logger.info(f"[Quepasa.send_text] Bot Token present? {bool(self.quepasa_bot_token)}")
        _logger.info(f"[Quepasa.send_text] Quepasa URL: {self.quepasa_url}")
        
        number = self._fmt_number(mobile)
        if not number:
            _logger.warning(f"[Quepasa.send_text] Invalid mobile number: {mobile}")
            return {'ok': False, 'error': 'invalid_mobile'}
        
        if not self.quepasa_bot_token:
            _logger.error(f"[Quepasa.send_text] Bot Token is missing for account {self.id} ({self.name})")
            return {'ok': False, 'error': 'bot_token_missing'}
        
        # POST /send com header X-QUEPASA-CHATID
        url = f"{self.quepasa_url}/send"
        payload = {'text': message or ''}
        headers = self._headers(chat_id=number)
        
        _logger.info(f"[Quepasa.send_text] URL: {url}")
        _logger.info(f"[Quepasa.send_text] Payload: {payload}")
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            ok = 200 <= resp.status_code < 300
            try:
                data = resp.json()
            except Exception:
                data = {'text': resp.text}
            
            _logger.info(f"[Quepasa.send_text] Response status: {resp.status_code}")
            _logger.info(f"[Quepasa.send_text] Response data: {data}")
            
            return {
                'ok': ok,
                'id': data.get('id') or data.get('messageId'),
                'raw': data,
                'status_code': resp.status_code,
            }
        except Exception as e:
            _logger.error(f"[Quepasa.send_text] Exception: {e}", exc_info=True)
            return {'ok': False, 'error': str(e), 'status_code': 0}

    def send_media(self, mobile, *, caption='', b64=None, mime=None, filename=None):
        """Envia mídia via Quepasa v4 - com arquivo binário"""
        _logger.info(f"[Quepasa.send_media] Called - Account: {self.name} (ID: {self.id})")
        _logger.info(f"[Quepasa.send_media] Provider: {self.provider}")
        
        # Se não for provider quepasa, chama o método base
        if self.provider != 'quepasa':
            _logger.info(f"[Quepasa.send_media] SKIPPING - provider is '{self.provider}', delegating to super()")
            return super().send_media(mobile, caption=caption, b64=b64, mime=mime, filename=filename)
        
        _logger.info(f"[Quepasa.send_media] EXECUTING - This is Quepasa provider")
        
        number = self._fmt_number(mobile)
        if not number:
            _logger.warning(f"[Quepasa.send_media] Invalid mobile: {mobile}")
            return {'ok': False, 'error': 'invalid_mobile'}
        
        if not self.quepasa_bot_token:
            _logger.error(f"[Quepasa.send_media] Bot Token missing")
            return {'ok': False, 'error': 'bot_token_missing'}
        
        media_b64 = b64
        if isinstance(media_b64, (bytes, bytearray)):
            media_b64 = media_b64.decode()
        
        if not media_b64:
            _logger.error(f"[Quepasa.send_media] Empty media")
            return {'ok': False, 'error': 'empty_media'}
        
        eff_mime = mime or (self._get_mime_type(filename) if filename else None) or 'application/octet-stream'
        
        _logger.info(f"[Quepasa.send_media] Mobile: {number}")
        _logger.info(f"[Quepasa.send_media] Caption: {caption}")
        _logger.info(f"[Quepasa.send_media] Mime: {eff_mime}")
        _logger.info(f"[Quepasa.send_media] Filename: {filename}")
        _logger.info(f"[Quepasa.send_media] Media b64 length: {len(media_b64)}")
        
        # Endpoint: POST /send com JSON
        # Quepasa v3/v4 usa 'content' com base64 puro (sem data URI prefix)
        url = f"{self.quepasa_url}/send"
        
        payload = {
            'text': caption or '',
            'content': media_b64,  # Base64 puro, igual v3
            'mimetype': eff_mime,
            'filename': filename or 'file.bin',
        }
        
        _logger.info(f"[Quepasa.send_media] URL: {url}")
        _logger.info(f"[Quepasa.send_media] Payload keys: {list(payload.keys())}")
        _logger.info(f"[Quepasa.send_media] Payload content length: {len(payload['content'])}")
        
        try:
            # Número do destinatário vai no header X-QUEPASA-CHATID
            headers = self._headers(chat_id=number)
            _logger.info(f"[Quepasa.send_media] Headers: {headers}")
            
            resp = requests.post(url, json=payload, headers=headers, timeout=40)
            ok = 200 <= resp.status_code < 300
            
            _logger.info(f"[Quepasa.send_media] Response status: {resp.status_code}")
            
            try:
                response_data = resp.json()
            except Exception:
                response_data = {'text': resp.text}
            
            _logger.info(f"[Quepasa.send_media] Response data: {response_data}")
            
            return {
                'ok': ok,
                'id': response_data.get('id') or response_data.get('messageId'),
                'raw': response_data,
                'status_code': resp.status_code,
            }
        except Exception as e:
            _logger.error(f"[Quepasa.send_media] Exception: {e}", exc_info=True)
            return {'ok': False, 'error': str(e), 'status_code': 0}

    def create_bot(self):
        """
        Configura bot no Quepasa.
        
        Nota: Quepasa não tem endpoint de criação de bot via API.
        Os tokens devem ser obtidos da interface web ou arquivo .env.
        Este método apenas valida o token e configura o webhook.
        """
        self.ensure_one()
        
        if not self.quepasa_url:
            raise UserError(_("Please configure Quepasa Server URL first"))
        
        if not self.quepasa_bot_token:
            raise UserError(_("Please configure Bot Token first.\n\n"
                             "Get the token from:\n"
                             "1. Quepasa web interface (http://seu-servidor:31000)\n"
                             "2. Or .env file: TOKEN_NAME=your_token_here"))
        
        # Configura webhook se habilitado
        if self.quepasa_webhook_enabled:
            try:
                self._configure_webhook()
                msg = _('Bot configured successfully!\nWebhook configured.')
            except Exception as e:
                _logger.warning(f"Failed to configure webhook: {str(e)}")
                msg = _('Bot configured, but webhook setup failed: %s') % str(e)
        else:
            msg = _('Bot configured successfully!')
        
        self.sudo().write({'bot_created': True})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': msg,
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _configure_webhook(self):
        """Configura webhook no Quepasa"""
        if not self.webhook_url:
            return
        
        url = f"{self.quepasa_url}/webhook"
        payload = {
            'url': self.webhook_url,
            'forwardinternal': True,
        }
        
        headers = self._headers()
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        
        if resp.status_code not in (200, 201):
            raise Exception(f"Status {resp.status_code}: {resp.text}")

    def delete_bot(self):
        """
        Quepasa v3.25+ não tem endpoint de deleção de bot.
        Este método apenas limpa a configuração local.
        """
        self.ensure_one()
        
        # Limpa configuração local
        self.sudo().write({
            'quepasa_bot_token': False,
            'bot_created': False,
            'qr_code': False,
            'state': 'disconnected',
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Bot configuration cleared!\n\nNote: Token still exists in Quepasa server.'),
                'type': 'warning',
                'sticky': False,
            }
        }

    def check_status(self):
        """Verifica status da conexão do bot"""
        _logger.info(f"[Quepasa.check_status] Called - Account: {self.name} (ID: {self.id})")
        _logger.info(f"[Quepasa.check_status] Provider: {self.provider}")
        
        if self.provider != 'quepasa':
            _logger.info(f"[Quepasa.check_status] SKIPPING - provider is '{self.provider}', delegating to super()")
            return super().check_status()
        
        _logger.info(f"[Quepasa.check_status] EXECUTING - This is Quepasa provider")
        
        self.ensure_one()
        
        if not self.quepasa_bot_token:
            _logger.error(f"[Quepasa.check_status] Bot Token not configured")
            raise UserError(_("Bot Token not configured"))
        
        # Endpoint correto: GET /info
        url = f"{self.quepasa_url}/info"
        
        _logger.info(f"[Quepasa.check_status] URL: {url}")
        
        try:
            headers = self._headers()
            _logger.info(f"[Quepasa.check_status] Headers: {headers}")
            
            resp = requests.get(url, headers=headers, timeout=15)
            
            _logger.info(f"[Quepasa.check_status] Response status: {resp.status_code}")
            _logger.info(f"[Quepasa.check_status] Response headers: {dict(resp.headers)}")
            
            if resp.status_code != 200:
                _logger.warning(f"[Quepasa.check_status] Non-200 status: {resp.status_code}")
                _logger.warning(f"[Quepasa.check_status] Response text: {resp.text}")
                raise UserError(_('Failed to check status (Status: %s)') % resp.status_code)
            
            try:
                data = resp.json()
                _logger.info(f"[Quepasa.check_status] Response JSON: {data}")
            except Exception as e:
                _logger.error(f"[Quepasa.check_status] Failed to parse JSON: {e}")
                _logger.error(f"[Quepasa.check_status] Response text: {resp.text}")
                raise UserError(_('Invalid response from Quepasa server'))
            
            # Verifica estado da conexão
            # Quepasa v4 retorna: {'success': True, 'server': {'verified': True, 'wid': '...', ...}}
            server_info = data.get('server', {})
            verified = server_info.get('verified', False)
            wid = server_info.get('wid', '')
            user = server_info.get('user', '')
            
            _logger.info(f"[Quepasa.check_status] Server verified: {verified}")
            _logger.info(f"[Quepasa.check_status] WID: {wid}")
            _logger.info(f"[Quepasa.check_status] User: {user}")
            
            if verified and wid:
                # Bot está conectado e verificado
                self.sudo().write({'state': 'connected'})
                phone = wid.split('@')[0] if '@' in wid else wid
                msg = _('Bot is connected! ✅\n\nPhone: %s\nUser: %s') % (phone, user or 'N/A')
                msg_type = 'success'
            else:
                # Bot não está conectado ou não verificado
                self.sudo().write({'state': 'disconnected'})
                msg = _('Bot is disconnected ❌\n\nPlease scan the QR Code to connect.')
                msg_type = 'warning'
            
            _logger.info(f"[Quepasa.check_status] Returning notification: {msg}")
            
            # Retorna múltiplas ações: notificação + reload
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Status Check'),
                    'message': msg,
                    'type': msg_type,
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    }
                }
            }
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"[Quepasa.check_status] RequestException: {str(e)}", exc_info=True)
            raise UserError(_('Connection error: %s') % str(e))
        except UserError:
            raise
        except Exception as e:
            _logger.error(f"[Quepasa.check_status] Exception: {str(e)}", exc_info=True)
            raise UserError(_('Error checking status: %s') % str(e))

    def connect(self):
        """Inicia processo de conexão e obtém QR Code via endpoint /scan"""
        if self.provider != 'quepasa':
            return super().connect()
        
        self.ensure_one()
        
        if not self.quepasa_bot_token:
            raise UserError(_("Please configure Bot Token first"))
        
        # Endpoint correto: POST /scan
        url = f"{self.quepasa_url}/scan"
        
        try:
            headers = self._headers()
            resp = requests.post(url, headers=headers, timeout=20)
            ok = 200 <= resp.status_code < 300
            
            payload = None
            try:
                payload = resp.json()
            except Exception:
                payload = None
            
            b64 = None
            if isinstance(payload, dict):
                b64 = payload.get('qrcode') or payload.get('base64') or payload.get('qr')
            
            # Atualiza campos
            vals = {'state': 'connecting'}
            if b64:
                # Remove data URI prefix se existir
                if isinstance(b64, str) and b64.startswith('data:') and ',' in b64:
                    b64 = b64.split(',', 1)[1]
                vals['qr_code'] = b64
            
            self.sudo().write(vals)
            
            if ok and b64:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('QR Code Updated'),
                        'message': _('QR Code generated! Please scan it with WhatsApp.'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(_('Failed to get QR Code (Status: %s)') % resp.status_code)
            
        except requests.exceptions.RequestException as e:
            self.sudo().write({'state': 'disconnected'})
            _logger.error(f"Error connecting Quepasa bot: {str(e)}")
            raise UserError(_('Connection error: %s') % str(e))
        except UserError:
            raise
        except Exception as e:
            self.sudo().write({'state': 'disconnected'})
            _logger.error(f"Error connecting Quepasa bot: {str(e)}")
            raise UserError(_('Error connecting: %s') % str(e))

    def disconnect(self):
        """Desconecta o bot do WhatsApp"""
        if self.provider != 'quepasa':
            return super().disconnect()
        
        self.ensure_one()
        
        if not self.quepasa_bot_token:
            raise UserError(_("Bot Token not configured"))
        
        # Endpoint: POST /logout (baseado na documentação)
        url = f"{self.quepasa_url}/logout"
        
        try:
            headers = self._headers()
            resp = requests.post(url, headers=headers, timeout=20)
            ok = 200 <= resp.status_code < 300
            
            # Limpa estado e QR code
            self.sudo().write({'state': 'disconnected', 'qr_code': False})
            
            if ok:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Bot disconnected successfully!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Warning'),
                        'message': _('Bot disconnected locally, but Quepasa returned status: %s') % resp.status_code,
                        'type': 'warning',
                        'sticky': False,
                    }
                }
                
        except requests.exceptions.RequestException as e:
            self.sudo().write({'state': 'disconnected', 'qr_code': False})
            _logger.error(f"Error disconnecting Quepasa bot: {str(e)}")
            raise UserError(_('Connection error (bot disconnected locally): %s') % str(e))
        except UserError:
            raise
        except Exception as e:
            self.sudo().write({'state': 'disconnected', 'qr_code': False})
            _logger.error(f"Error disconnecting Quepasa bot: {str(e)}")
            raise UserError(_('Error disconnecting: %s') % str(e))

    def restart(self):
        """Reinicia a conexão do bot"""
        if self.provider != 'quepasa':
            return super().restart()
        
        self.disconnect()
        return self.connect()

    def refresh_qrcode(self):
        """Atualiza QR Code reconectando"""
        if self.provider != 'quepasa':
            return super().refresh_qrcode()
        
        return self.connect()

    # ==================== CRUD ====================
    # Nota: A criação do bot deve ser feita manualmente através do botão "Create Bot"
    # após configurar as credenciais (URL e Token)
    
    def write(self, vals):
        res = super().write(vals)
        # Se mudar o nome e já tiver bot criado, atualiza no Quepasa
        if 'name' in vals and self.provider == 'quepasa' and self.bot_created:
            # TODO: implementar update do bot no Quepasa se a API suportar
            pass
        return res
