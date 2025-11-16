# Fix: Webhook URL Generation

## Problema Identificado

A ação de **gerar nova webhook URL** parou de funcionar quando o provider é `quepasa`.

### Causa Raiz

No módulo `wa_conn_quepasa`, o campo `webhook_url` foi **redefinido como computed field**:

```python
webhook_url = fields.Char(
    string="Webhook URL",
    compute="_compute_webhook_url",  # ❌ PROBLEMA
    readonly=True,
    help="URL to configure in Quepasa for receiving events"
)
```

Isso causou conflito com o campo original do `wa_conn` que é **stored** (gravado no banco de dados).

### Impacto

- O método `new_webhook_url()` do `wa_conn` não conseguia gravar o novo valor
- O webhook URL ficava sempre calculado como `/wa/webhook/quepasa/<account_id>`
- Não era possível usar o sistema de webhook UUID padrão do framework

---

## Solução Implementada

### 1. **Removida redefinição do campo `webhook_url`**

```python
# ANTES (❌ Errado)
webhook_url = fields.Char(
    compute="_compute_webhook_url",
    readonly=True,
)

def _compute_webhook_url(self):
    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    for record in self:
        if record.provider == 'quepasa' and record.id:
            record.webhook_url = f"{base_url}/wa/webhook/quepasa/{record.id}"
        else:
            record.webhook_url = False
```

```python
# DEPOIS (✅ Correto)
# Campo herdado do wa_conn - não redefinir!
# O wa_conn já gerencia webhook_url, webhook_uuid e webhook_key
```

### 2. **Simplificado o controller**

```python
# ANTES (❌ Endpoint customizado)
@http.route('/wa/webhook/quepasa/<int:account_id>', type='json', auth='none', methods=['POST'], csrf=False)
def webhook_quepasa(self, account_id, **kwargs):
    account = request.env['wa.account'].sudo().browse(account_id)
    # ... processamento manual
```

```python
# DEPOIS (✅ Usa controller padrão do wa_conn)
# O webhook agora usa: /wa/webhook/<webhook_uuid>
# O controller em wa_conn/controllers/wa_controller.py já resolve a conta
# e processa o payload automaticamente
```

---

## Como Funciona Agora

### 1. **Geração de Webhook URL**

O método `new_webhook_url()` do `wa_conn` funciona corretamente:

```python
account = env['wa.account'].browse(ID)
account.new_webhook_url()

# Gera:
# - webhook_uuid: "abc-123-def-456"
# - webhook_key: "secret_token_xyz"
# - webhook_url: "https://seu-odoo.com/wa/webhook/abc-123-def-456"
```

### 2. **Endpoint do Webhook**

O Quepasa deve enviar eventos para:

```
POST https://seu-odoo.com/wa/webhook/<webhook_uuid>
Headers:
  - Content-Type: application/json
  - webhook_key: <valor do webhook_key> (opcional, para segurança)
Body: JSON payload do Quepasa
```

### 3. **Resolução Automática da Conta**

O controller do `wa_conn` resolve a conta usando (em ordem de prioridade):

1. `webhook_uuid` na URL
2. Header `X-Webhook-UUID`
3. Header `webhook_key`
4. Campo `instance` no payload JSON

### 4. **Configuração no Quepasa**

Ao clicar em **"Create Bot"**, o método `_configure_webhook()` envia:

```json
POST https://quepasa-api.bitconn.com.br/webhook
Headers:
  X-QUEPASA-TOKEN: <bot_token>
Body:
{
  "url": "https://seu-odoo.com/wa/webhook/<webhook_uuid>",
  "forwardinternal": true
}
```

---

## Compatibilidade

### ✅ Mantido

- O campo `webhook_url` continua funcionando normalmente
- O método `_configure_webhook()` usa `self.webhook_url` (agora o campo correto do wa_conn)
- Toda a lógica de envio de mensagens permanece igual

### ✅ Melhorado

- O botão **"Generate New Webhook URL"** agora funciona
- Sistema de segurança com `webhook_key` habilitado
- Webhook URL com UUID único e randômico (mais seguro)
- Compatível com todos os providers do `wa_conn`

---

## Teste

### 1. Atualizar o módulo

```bash
./odoo-bin -c odoo.conf -u wa_conn_quepasa
```

### 2. Gerar novo webhook

```python
# Via interface web: Botão "Generate New Webhook URL"
# OU via shell:
account = env['wa.account'].search([('provider', '=', 'quepasa')], limit=1)
account.new_webhook_url()
print(f"Webhook URL: {account.webhook_url}")
print(f"Webhook Key: {account.webhook_key}")
```

### 3. Configurar no Quepasa

Clicar no botão **"Create Bot"** para enviar a nova URL ao Quepasa.

### 4. Testar recebimento

```bash
# Endpoint de teste
curl https://seu-odoo.com/wa/webhook/quepasa/test
# Resposta: "Quepasa Webhook is working! Use POST /wa/webhook/<webhook_uuid> to send events."

# Simular webhook
curl -X POST "https://seu-odoo.com/wa/webhook/<seu-webhook-uuid>" \
  -H "Content-Type: application/json" \
  -H "webhook_key: <seu-webhook-key>" \
  -d '{
    "id": "test123",
    "from": "5511999999999",
    "text": "Test message",
    "type": "text"
  }'
```

---

## Arquivos Modificados

1. **models/wa_conn_quepasa_provider.py**
   - Removido campo `webhook_url` (linhas ~53-59)
   - Removido método `_compute_webhook_url()` (linhas ~68-74)

2. **controllers/main.py**
   - Removido endpoint customizado `/wa/webhook/quepasa/<account_id>`
   - Mantido apenas endpoint de teste `/wa/webhook/quepasa/test`

---

## Conclusão

A correção garante que o **Quepasa usa o sistema padrão de webhooks do `wa_conn`**, permitindo:

✅ Geração de webhook URL funcional  
✅ Segurança com webhook_key  
✅ UUID único por conta  
✅ Compatibilidade com framework base  
✅ Facilidade de manutenção
