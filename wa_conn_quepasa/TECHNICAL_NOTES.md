# Notas Técnicas - wa_conn_quepasa

## Estrutura do Módulo

```
wa_conn_quepasa/
├── __init__.py                     # Init principal (importa models e controllers)
├── __manifest__.py                 # Manifesto do módulo
├── README.md                       # Documentação do usuário
├── examples.py                     # Exemplos de uso da API
├── TECHNICAL_NOTES.md             # Este arquivo
├── controllers/
│   ├── __init__.py                # Init dos controllers
│   └── main.py                    # Controller do webhook
├── models/
│   ├── __init__.py                # Init dos models
│   └── wa_conn_quepasa_provider.py # Modelo principal
├── security/
│   └── ir.model.access.csv        # Permissões de acesso
└── views/
    └── wa_conn_quepasa_provider_views.xml # Views XML
```

## Arquitetura

### Herança de Modelo

O módulo usa **herança por extensão** do modelo `wa.account`:

```python
class WAAccountQuepasa(models.Model):
    _inherit = 'wa.account'
```

Isso significa que:
- Adiciona campos específicos do Quepasa ao modelo existente
- Os campos só aparecem quando `provider == 'quepasa'`
- Não cria uma nova tabela no banco de dados
- Todos os registros `wa.account` podem usar o provider Quepasa

### Campos Computados

**webhook_url**: Computado automaticamente baseado em:
- Base URL do Odoo (`web.base.url`)
- Bot ID do Quepasa (`quepasa_bot_id`)
- Formato: `https://seu-odoo.com/wa/webhook/quepasa/{bot_id}`

### Métodos Principais

#### API Methods (Integração com Quepasa)

1. **create_bot()**: Cria um novo bot no servidor Quepasa
2. **delete_bot()**: Remove o bot do servidor
3. **connect()**: Inicia conexão e obtém QR Code
4. **disconnect()**: Desconecta o bot do WhatsApp
5. **check_status()**: Verifica estado da conexão
6. **send_text()**: Envia mensagem de texto
7. **send_media()**: Envia mídia (imagem, vídeo, áudio, documento)

#### Webhook Methods

1. **normalize_inbound()**: Normaliza payload do Quepasa para DTO padrão
2. **inbound_handle()**: Processa mensagens recebidas

## Formato de Dados

### DTO (Data Transfer Object)

O módulo usa o DTO padrão definido em `wa_conn.models.dto`:

```python
dto.NormalizedPayload(
    provider='quepasa',
    instance='bot_id',
    event='message',
    message_id='msg_123',
    remote_jid='5511999999999@s.whatsapp.net',
    mobile='5511999999999',
    from_me=False,
    push_name='Nome do Contato',
    message='Texto da mensagem',
    raw={...},  # Payload original do Quepasa
)
```

### Estrutura de Resposta da API

Todas as chamadas à API retornam um dicionário padronizado:

```python
{
    'ok': True/False,              # Sucesso da operação
    'status_code': 200,            # HTTP status code
    'id': 'message_id',            # ID da mensagem (quando aplicável)
    'raw': {...},                  # Resposta completa da API
    'error': 'error message',      # Mensagem de erro (se houver)
}
```

## Diferenças em relação ao Evolution API

### Campos de Configuração

**Evolution API**:
- `instance_name`: Nome técnico da instância
- `api_url`: URL base da API
- `api_key`: Chave de API
- Múltiplas configurações de instância

**Quepasa**:
- `quepasa_bot_id`: ID do bot (gerado pelo Quepasa)
- `quepasa_url`: URL do servidor Quepasa
- `quepasa_token`: Token de autenticação
- Mais simples, menos configurações

### Endpoints da API

**Evolution API**:
```
POST /instance/create
POST /message/sendText/{instance}
GET /instance/connectionState/{instance}
```

**Quepasa**:
```
POST /bot
POST /bot/{bot_id}/send
GET /bot/{bot_id}
```

### Payload de Webhook

**Evolution API**:
```json
{
  "event": "messages.upsert",
  "data": {
    "key": {"id": "...", "remoteJid": "..."},
    "message": {"conversation": "..."},
    ...
  }
}
```

**Quepasa**:
```json
{
  "id": "message_id",
  "from": "5511999999999",
  "text": "mensagem",
  "type": "text",
  "fromMe": false,
  ...
}
```

## Fluxo de Dados

### Mensagens Enviadas (Outbound)

```
Odoo (wa.account)
    ↓ send_text() ou send_media()
Quepasa API
    ↓ POST /bot/{bot_id}/send
WhatsApp
```

### Mensagens Recebidas (Inbound)

```
WhatsApp
    ↓
Quepasa Server
    ↓ POST webhook
Odoo Controller (/wa/webhook/quepasa/{bot_id})
    ↓ inbound_handle()
    ↓ normalize_inbound()
    ↓ wa_post_incoming()
discuss.channel (mensagem postada)
```

## Segurança

### Autenticação

- **API Quepasa**: Header `X-QUEPASA-TOKEN`
- **Webhook Odoo**: `auth='none'` (público)
  - Valida bot_id para identificar conta
  - Recomendado: Adicionar autenticação customizada se necessário

### Permissões Odoo

```csv
access_wa_account_quepasa_user       # Usuários: CRUD (sem delete)
access_wa_account_quepasa_manager    # Administradores: Full CRUD
```

## Otimizações

### Performance

1. **Lazy Loading**: Campos computados só são calculados quando necessário
2. **Bulk Operations**: Webhook processa múltiplas mensagens de uma vez
3. **Caching**: Estados armazenados no banco (state, bot_created)

### Escalabilidade

- Suporta múltiplas contas Quepasa simultaneamente
- Cada conta tem seu próprio bot_id e webhook endpoint
- Sem limite de throughput (depende do servidor Quepasa)

## Debugging

### Logs

Ative logs no Odoo:

```python
_logger.info(f'[Quepasa] Message sent: {result}')
_logger.warning(f'[Quepasa] Bot not found: {bot_id}')
_logger.error(f'[Quepasa] API Error: {error}')
_logger.exception(f'[Quepasa] Exception: {e}')
```

### Teste Manual de Webhook

```bash
curl -X POST http://seu-odoo.com/wa/webhook/quepasa/test_bot_id \
  -H "Content-Type: application/json" \
  -d '{
    "id": "msg_123",
    "from": "5511999999999",
    "text": "Teste",
    "type": "text",
    "fromMe": false
  }'
```

### Teste da API Quepasa

```bash
# Criar bot
curl -X POST https://seu-quepasa.com/bot \
  -H "Content-Type: application/json" \
  -H "X-QUEPASA-TOKEN: seu_token" \
  -d '{"name": "Test Bot"}'

# Obter QR Code
curl -X GET https://seu-quepasa.com/bot/{bot_id}/qrcode \
  -H "X-QUEPASA-TOKEN: seu_token"

# Enviar mensagem
curl -X POST https://seu-quepasa.com/bot/{bot_id}/send \
  -H "Content-Type: application/json" \
  -H "X-QUEPASA-TOKEN: seu_token" \
  -d '{"recipient": "5511999999999", "message": "Teste"}'
```

## Extensões Futuras

### Features Planejadas

1. **Reações**: Suporte a reações em mensagens (se Quepasa implementar)
2. **Grupos**: Melhor suporte para mensagens de grupos
3. **Status**: Envio e recepção de stories/status
4. **Botões**: Mensagens com botões interativos
5. **Listas**: Mensagens com listas de opções
6. **Templates**: Suporte a templates de mensagens
7. **Agendamento**: Agendar envio de mensagens

### Integrações

- **wa_conn_bot**: Bot conversacional (já compatível)
- **wa_conn_marketing**: Campanhas de marketing (compatível)
- **mail**: Integração com chatter do Odoo
- **crm**: Envio de mensagens do CRM
- **sale**: Notificações de pedidos

## Manutenção

### Atualizações da API Quepasa

Se a API do Quepasa mudar:

1. Atualize os endpoints em `wa_conn_quepasa_provider.py`
2. Ajuste o `normalize_inbound()` para novos formatos de payload
3. Teste todos os métodos (send, receive, connect, etc)
4. Atualize a documentação

### Compatibilidade Odoo

- **Versão atual**: 18.0
- **Compatibilidade**: 16.0+, 17.0+
- **Dependências**: wa_conn (obrigatório)

### Testes

```python
# Teste de envio
account = env['wa.account'].search([('provider', '=', 'quepasa')], limit=1)
result = account.send_text('5511999999999', 'Teste')
assert result['ok'] == True

# Teste de webhook
payload = {
    'id': 'test_123',
    'from': '5511999999999',
    'text': 'Test message',
    'type': 'text',
    'fromMe': False
}
result = account.inbound_handle(payload)
assert result['results'][0]['status'] == 'ok'
```

## Contribuindo

Para contribuir com o módulo:

1. Fork o repositório
2. Crie uma branch para sua feature
3. Implemente e teste suas mudanças
4. Atualize a documentação
5. Envie um Pull Request

## Suporte

- GitHub Issues
- Email: suporte@yourcompany.com
- Documentação: Ver README.md

## Licença

LGPL-3 - Ver LICENSE file
