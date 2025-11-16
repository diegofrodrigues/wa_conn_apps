from odoo import _, api, fields, models
import uuid
import secrets
import logging

_logger = logging.getLogger(__name__)


class WAAccount(models.Model):
    """
    WhatsApp Account - Base Model (Slim)
    
    Este é o modelo base que gerencia contas WhatsApp.
    Campos específicos de cada provider são adicionados via _inherit pelos plugins.
    """
    _name = 'wa.account'
    _description = 'WhatsApp Account'
    _inherit = ['mail.thread']

    # ==================== CAMPOS UNIVERSAIS ====================
    name = fields.Char(
        string="Account Name", 
        required=True, 
        tracking=True,
        help="Friendly name for this WhatsApp account in Odoo (e.g., 'Sales WhatsApp', 'Support Team')"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        help="The company this WhatsApp account belongs to."
    )
    
    wa_team_ids = fields.Many2many(
        'wa.team',
        'wa_account_team_rel',
        'account_id',
        'team_id',
        string='Teams',
        help='Teams with access to this WhatsApp account.'
    )

    # Provider selection - Extensível via selection_add
    provider = fields.Selection(
        selection=[],  # Providers são adicionados via selection_add pelos plugins
        string="Provider",
        required=True,
        tracking=True,
        help="WhatsApp API provider (extended by installed plugins)"
    )

    state = fields.Selection(
        [
            ('not_created', 'Not Created'),
            ('disconnected', 'Disconnected'),
            ('connecting', 'Connecting'),
            ('connected', 'Connected'),
        ],
        string="State",
        default='not_created',
        readonly=True,
        tracking=True,
        help="Current connection state of the WhatsApp instance"
    )

    # Webhook (universal)
    webhook_url = fields.Char(
        string="Webhook URL", 
        readonly=True, 
        help="URL do webhook para receber eventos."
    )
    webhook_key = fields.Char(
        string="Webhook Key", 
        readonly=True, 
        help="Chave secreta do webhook."
    )
    webhook_uuid = fields.Char(
        string="Webhook UUID", 
        readonly=True, 
        help="UUID único do webhook."
    )

    # ==================== INTERFACE DE INTEGRAÇÃO ====================
    # Cada tipo/provider deve sobrescrever estes métodos via herança
    
    def normalize_inbound(self, raw, request=None):
        """
        Normaliza o payload bruto do webhook para um formato padronizado (DTO).
        Deve ser sobrescrito por cada tipo/provider.
        """
        raise NotImplementedError(
            f"Provider '{self.provider}' must implement normalize_inbound() method. "
            f"Account: {self.name} (ID: {self.id})"
        )

    def inbound_handle(self, raw, request=None):
        """
        Processa o webhook completo: normaliza + cria registros no Odoo.
        Deve ser sobrescrito por cada tipo/provider.
        """
        raise NotImplementedError(
            f"Provider '{self.provider}' must implement inbound_handle() method. "
            f"Account: {self.name} (ID: {self.id})"
        )
    
    def inbound_handle_reaction(self, dto, partner):
        """
        Processa uma reação recebida (reactionMessage) de um provedor WhatsApp.
        Deve ser sobrescrito por cada provider.
        """
        raise NotImplementedError("Account type must implement inbound_handle_reaction() for reactions.")
    
    def inbound_handle_reply(self, dto, partner):
        """
        Processa uma resposta (reply) recebida de um provedor WhatsApp.
        Deve ser sobrescrito por cada provider.
        Args:
            dto: DTO normalizado da mensagem recebida.
            partner: res.partner correspondente ao remetente.
        """
        raise NotImplementedError("Account type must implement inbound_handle_reply() for replies.")

    def send_text(self, mobile, message):
        """
        Envia uma mensagem de texto.
        Deve ser sobrescrito por cada tipo/provider.
        """
        _logger.info(f"[wa_account.send_text] Account: {self.name}, Provider: {self.provider}")
        _logger.info(f"[wa_account.send_text] Class: {self.__class__.__name__}")
        _logger.info(f"[wa_account.send_text] MRO: {[c.__name__ for c in self.__class__.__mro__]}")
        
        raise NotImplementedError(
            f"Provider '{self.provider}' must implement send_text() method. "
            f"Account: {self.name} (ID: {self.id})"
        )

    def send_media(self, mobile, *, caption='', b64=None, mime=None, filename=None):
        """
        Envia uma mensagem com mídia (imagem, vídeo, documento, áudio).
        Deve ser sobrescrito por cada tipo/provider.
        """
        _logger.info(f"[wa_account.send_media] Account: {self.name}, Provider: {self.provider}")
        _logger.info(f"[wa_account.send_media] Class: {self.__class__.__name__}")
        
        raise NotImplementedError(
            f"Provider '{self.provider}' must implement send_media() method. "
            f"Account: {self.name} (ID: {self.id})"
        )
    
    def send_reaction(self, key, reaction):
        """
        Envia uma reação para uma mensagem (abstrato).
        Deve ser sobrescrito por cada tipo/provider.
        Args:
            key (dict): Deve conter 'remoteJid', 'id' e 'fromMe'.
            reaction (str): Emoji da reação (ex: '🚀').
        """
        raise NotImplementedError(
            f"Provider '{self.provider}' must implement send_reaction() method. "
            f"Account: {self.name} (ID: {self.id})"
        )
    
    def send_reply(self, mobile, message, reply_to=None):
        """
        Envia uma mensagem de texto em resposta a outra mensagem (reply threading).
        Deve ser sobrescrito por cada tipo/provider.
        Args:
            mobile (str): Número do destinatário.
            message (str): Texto da mensagem.
            reply_to (str|None): ID da mensagem a ser referenciada como reply (ex: wa_message_id).
        """
        raise NotImplementedError(
            f"Provider '{self.provider}' must implement send_reply() method. "
            f"Account: {self.name} (ID: {self.id})"
        )

    def create_instance(self):
        """
        Cria uma instância no provider.
        Deve ser sobrescrito por cada tipo/provider.
        """
        raise NotImplementedError("Account type must implement create_instance()")

    def delete_instance(self):
        """
        Deleta uma instância no provider.
        Deve ser sobrescrito por cada tipo/provider.
        """
        raise NotImplementedError("Account type must implement delete_instance()")

    def check_status(self):
        """
        Verifica o status da conexão.
        Deve ser sobrescrito por cada tipo/provider.
        """
        raise NotImplementedError("Account type must implement check_status()")

    def connect(self):
        """
        Conecta a instância (pode gerar QR code para pareamento).
        Deve ser sobrescrito por cada tipo/provider.
        """
        raise NotImplementedError("Account type must implement connect()")

    def restart(self):
        """
        Reinicia a instância.
        Deve ser sobrescrito por cada tipo/provider.
        """
        raise NotImplementedError("Account type must implement restart()")

    def disconnect(self):
        """
        Desconecta/faz logout da instância.
        Deve ser sobrescrito por cada tipo/provider.
        """
        raise NotImplementedError("Account type must implement disconnect()")

    def get_profile_image(self, remote_jid=None):
        """
        Busca a imagem de perfil de um contato.
        Deve ser sobrescrito por cada tipo/provider.
        """
        raise NotImplementedError("Account type must implement get_profile_image()")

    # ==================== WEBHOOK ====================
    def _get_provider(self):
        """
        Retorna a instância do provider associado a esta account.
        O provider é encontrado dinamicamente baseado no campo 'provider'.
        """
        self.ensure_one()
        
        if not self.provider:
            raise ValueError(_("No provider selected for this account"))
        
        provider_model_name = f'wa.provider.{self.provider}'
        
        # Verifica se o modelo existe
        if provider_model_name not in self.env:
            raise ValueError(_(f"Provider model '{provider_model_name}' not found. Is the plugin installed?"))
        
        # Busca o registro do provider associado a esta account
        provider = self.env[provider_model_name].search([
            ('account_id', '=', self.id)
        ], limit=1)
        
        if not provider:
            raise ValueError(_(f"No provider instance found for account '{self.name}'. Provider: {self.provider}"))
        
        return provider

    # ==================== WEBHOOK UTILITIES ====================
    def new_webhook_url(self):
        """Gera novas credenciais/URL do webhook."""
        new_key = secrets.token_urlsafe(32)
        new_uuid = str(uuid.uuid4())
        api_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        self.webhook_key = new_key
        self.webhook_uuid = new_uuid
        self.webhook_url = f"{api_url}/wa/webhook/{new_uuid}"
        self.message_post(body=_("Webhook credentials regenerated"))

    # ==================== CRUD HOOKS ====================
    @api.model_create_multi
    def create(self, vals_list):
        """
        Override do create para:
        1. Inicializar webhook credentials
        2. Garantir unicidade por empresa
        3. Criar automaticamente o registro do provider
        """
        for vals in vals_list:
            # Validação de unicidade
            if 'name' in vals and 'company_id' in vals:
                existing_account = self.search([
                    ('name', '=', vals['name']),
                    ('company_id', '=', vals['company_id'])
                ])
                if existing_account:
                    raise ValueError(_(
                        "A WhatsApp account with this name already exists for the selected company."
                    ))
            if not vals.get('webhook_key'):
                vals['webhook_key'] = secrets.token_urlsafe(32)
            if not vals.get('webhook_uuid'):
                vals['webhook_uuid'] = str(uuid.uuid4())
            if not vals.get('webhook_url'):
                api_url = self.env['ir.config_parameter'].sudo().get_param(
                    'web.base.url', 'http://localhost:8069'
                )
                vals['webhook_url'] = f"{api_url}/wa/webhook/{vals['webhook_uuid']}"

        # Cria as accounts
        accounts = super(WAAccount, self).create(vals_list)

        # Cria automaticamente o registro do provider para cada account
        for account in accounts:
            if account.provider == 'none':
                raise ValueError(_(
                    "No WhatsApp provider is installed. Please install a provider plugin before creating an account."
                ))
            account._create_provider_instance()
            account.message_post(body=_("WhatsApp account '%s' has been created." % account.name))

        return accounts

    def _create_provider_instance(self):
        """
        Cria automaticamente o registro do provider associado.
        Chamado automaticamente ao criar uma wa.account.
        """
        self.ensure_one()

        if not self.provider:
            raise ValueError(_("Provider not specified"))

        # Se o provider for evolution ou quepasa, não há modelo extra, tudo está em wa.account
        if self.provider in ('evolution', 'quepasa'):
            return self

        provider_model_name = f'wa.provider.{self.provider}'

        # Verifica se o modelo existe
        if provider_model_name not in self.env:
            raise ValueError(_(
                f"Provider model '{provider_model_name}' not found. "
                f"Please install the corresponding plugin (wa_conn_{self.provider})"
            ))

        # Verifica se já existe um provider para esta account
        existing = self.env[provider_model_name].search([
            ('account_id', '=', self.id)
        ], limit=1)

        if existing:
            return existing

        # Cria o registro do provider
        provider = self.env[provider_model_name].create({
            'account_id': self.id,
        })

        return provider

    def unlink(self):
        """
        Override do unlink para deletar também o provider associado.
        """
        for account in self:
            try:
                provider = account._get_provider()
                if provider:
                    provider.unlink()
            except Exception:
                pass
        
        return super(WAAccount, self).unlink()

