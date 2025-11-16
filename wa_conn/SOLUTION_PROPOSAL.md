# Proposta de Solução: Models Separados (Composition Pattern)

## Visão Geral

Em vez de múltiplos `_inherit` causando conflitos de MRO, vamos usar **composição**:
- `wa.account` = Model principal (gerencia tudo)
- `wa.provider.evolution` = Model separado para Evolution
- `wa.provider.quepasa` = Model separado para Quepasa

## Estrutura Proposta

```
wa_conn/
├── models/
│   ├── wa_account.py          # Model principal COM dispatch
│   ├── wa_provider_abstract.py # Abstract base para providers
│   └── ...

wa_conn_evolution/
├── models/
│   └── wa_provider_evolution.py  # Implementação Evolution
└── ...

wa_conn_quepasa/
├── models/
│   └── wa_provider_quepasa.py    # Implementação Quepasa
└── ...
```

## Implementação

### 1. Abstract Provider Base (wa_conn/models/wa_provider_abstract.py)

```python
from odoo import models, fields, api
from abc import abstractmethod

class WAProviderAbstract(models.AbstractModel):
    """Base abstrata para todos os providers WhatsApp"""
    _name = 'wa.provider.abstract'
    _description = 'WhatsApp Provider Abstract'
    
    account_id = fields.Many2one('wa.account', required=True, ondelete='cascade')
    
    @abstractmethod
    def send_text(self, mobile, message):
        pass
    
    @abstractmethod
    def send_media(self, mobile, *, caption='', b64=None, mime=None, filename=None):
        pass
    
    @abstractmethod
    def normalize_inbound(self, raw, request=None):
        pass
    
    @abstractmethod
    def inbound_handle(self, raw, request=None):
        pass
    
    @abstractmethod
    def create_instance(self):
        pass
    
    @abstractmethod
    def check_status(self):
        pass
```

### 2. wa.account com Dispatch (wa_conn/models/wa_account.py)

```python
class WAAccount(models.Model):
    _name = 'wa.account'
    _description = 'WhatsApp Account'
    _inherit = ['mail.thread']
    
    name = fields.Char()
    provider = fields.Selection([
        ('evolution', 'Evolution API'),
        ('quepasa', 'Quepasa'),
    ])
    
    # Reference field - dynamically points to correct provider
    provider_id = fields.Reference(
        selection='_selection_provider_models',
        string='Provider Configuration'
    )
    
    @api.model
    def _selection_provider_models(self):
        """Retorna models disponíveis dinamicamente"""
        models = []
        if 'wa.provider.evolution' in self.env:
            models.append(('wa.provider.evolution', 'Evolution'))
        if 'wa.provider.quepasa' in self.env:
            models.append(('wa.provider.quepasa', 'Quepasa'))
        return models
    
    @api.model
    def create(self, vals):
        """Cria o provider correspondente automaticamente"""
        record = super().create(vals)
        if record.provider == 'evolution':
            provider = self.env['wa.provider.evolution'].create({
                'account_id': record.id
            })
            record.provider_id = f'wa.provider.evolution,{provider.id}'
        elif record.provider == 'quepasa':
            provider = self.env['wa.provider.quepasa'].create({
                'account_id': record.id
            })
            record.provider_id = f'wa.provider.quepasa,{provider.id}'
        return record
    
    def _get_provider(self):
        """Retorna o objeto provider"""
        self.ensure_one()
        if not self.provider_id:
            raise ValueError(f"No provider configured for account {self.name}")
        return self.provider_id
    
    # Métodos que delegam para o provider
    def send_text(self, mobile, message):
        return self._get_provider().send_text(mobile, message)
    
    def send_media(self, mobile, *, caption='', b64=None, mime=None, filename=None):
        return self._get_provider().send_media(mobile, caption=caption, b64=b64, mime=mime, filename=filename)
    
    def normalize_inbound(self, raw, request=None):
        return self._get_provider().normalize_inbound(raw, request)
    
    def inbound_handle(self, raw, request=None):
        return self._get_provider().inbound_handle(raw, request)
```

### 3. Evolution Provider (wa_conn_evolution/models/wa_provider_evolution.py)

```python
class WAProviderEvolution(models.Model):
    _name = 'wa.provider.evolution'
    _description = 'Evolution API Provider'
    _inherit = 'wa.provider.abstract'
    
    # Campos específicos do Evolution
    api_url = fields.Char(string="API URL", required=True)
    api_key = fields.Char(string="API Key", required=True)
    instance_name = fields.Char(string="Instance Name")
    qr_code = fields.Image(string="QR Code")
    reject_call = fields.Boolean(string="Reject Call")
    # ... todos os campos específicos do Evolution ...
    
    def send_text(self, mobile, message):
        """Implementação Evolution"""
        self.ensure_one()
        number = self._fmt_number(mobile)
        url = f"{self.api_url}/message/sendText/{self.instance_name}"
        payload = {'number': number, 'text': message}
        resp = requests.post(url, json=payload, headers=self._headers())
        # ... resto da implementação ...
        return resultado
    
    def send_media(self, mobile, *, caption='', b64=None, mime=None, filename=None):
        """Implementação Evolution"""
        # ... código Evolution ...
    
    def normalize_inbound(self, raw, request=None):
        """Implementação Evolution"""
        # ... código Evolution ...
    
    def inbound_handle(self, raw, request=None):
        """Implementação Evolution"""
        # ... código Evolution ...
    
    def _headers(self):
        return {'apikey': self.api_key}
    
    def _fmt_number(self, mobile):
        # ... código Evolution ...
```

### 4. Quepasa Provider (wa_conn_quepasa/models/wa_provider_quepasa.py)

```python
class WAProviderQuepasa(models.Model):
    _name = 'wa.provider.quepasa'
    _description = 'Quepasa Provider'
    _inherit = 'wa.provider.abstract'
    
    # Campos específicos do Quepasa
    quepasa_url = fields.Char(string="Quepasa URL", required=True)
    quepasa_bot_token = fields.Char(string="Bot Token", required=True)
    # ... todos os campos específicos do Quepasa ...
    
    def send_text(self, mobile, message):
        """Implementação Quepasa"""
        self.ensure_one()
        url = f"{self.quepasa_url}/send"
        payload = {
            'chatId': f"{mobile}@s.whatsapp.net",
            'text': message
        }
        headers = {'X-QUEPASA-TOKEN': self.quepasa_bot_token}
        resp = requests.post(url, json=payload, headers=headers)
        # ... resto da implementação ...
        return resultado
    
    def send_media(self, mobile, *, caption='', b64=None, mime=None, filename=None):
        """Implementação Quepasa"""
        # ... código Quepasa ...
    
    def normalize_inbound(self, raw, request=None):
        """Implementação Quepasa"""
        # ... código Quepasa ...
    
    def inbound_handle(self, raw, request=None):
        """Implementação Quepasa"""
        # ... código Quepasa ...
```

## Vantagens

1. **Zero conflitos de MRO**: Cada provider é uma classe independente
2. **Isolamento perfeito**: Campos e métodos de cada provider ficam completamente separados
3. **Manutenção fácil**: Adicionar/remover provider não afeta os outros
4. **Testável**: Cada provider pode ser testado isoladamente
5. **Claro e explícito**: Fica óbvio qual código executa para qual provider
6. **Views separadas**: Cada provider pode ter suas próprias views e formulários

## Desvantagens

1. **Refatoração necessária**: Precisa mover código dos models atuais
2. **Mais objetos**: Cria registros em duas tabelas (wa_account + wa_provider_X)
3. **Views mais complexas**: Formulário da account precisa mostrar campos do provider dinamicamente

## Migração

Para migrar da arquitetura atual:

1. Criar os novos models `wa.provider.evolution` e `wa.provider.quepasa`
2. Script de migração para copiar dados:
   ```python
   for account in env['wa.account'].search([]):
       if account.provider == 'evolution':
           provider = env['wa.provider.evolution'].create({
               'account_id': account.id,
               'api_url': account.api_url,
               'api_key': account.api_key,
               # ... copiar todos os campos ...
           })
           account.provider_id = f'wa.provider.evolution,{provider.id}'
   ```
3. Remover campos específicos de provider do `wa.account`
4. Atualizar views para usar campos do provider

## Alternativa Mais Simples

Se não quiser fazer refatoração completa, podemos usar **delegates=True** no Many2one:

```python
# wa_account.py
evolution_config_id = fields.Many2one('wa.provider.evolution', delegate=True)
quepasa_config_id = fields.Many2one('wa.provider.quepasa', delegate=True)
```

Isso faz os campos aparecerem diretamente no wa.account, mas internamente ficam em tabelas separadas!
