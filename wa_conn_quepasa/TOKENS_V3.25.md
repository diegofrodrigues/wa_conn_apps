# Tokens e Autenticação - Quepasa v3.25+

## 📘 Visão Geral

O Quepasa v3.25+ usa um sistema de token único por conexão WhatsApp, diferente das versões anteriores que tinham WEBAPITOKEN global.

## 🔑 Tipos de Token

### 1. Bot Token (Por Conexão)
- **O que é:** Token único gerado para cada conexão/número WhatsApp
- **Onde obter:** Interface web do Quepasa ou variáveis de ambiente
- **Usado para:** 
  - Enviar mensagens (`POST /send`)
  - Obter QR Code (`POST /scan`)
  - Verificar status (`GET /info`)
  - Desconectar (`POST /logout`)
  - Configurar webhook (`POST /webhook`)

**Campo no Odoo:** `Bot Token` (quepasa_bot_token)

### 2. MASTERKEY (Opcional)
- **O que é:** Token global para gerenciamento do servidor Quepasa
- **Onde configurar:** Arquivo `.env` do Quepasa (`MASTERKEY=...`)
- **Usado para:** Operações administrativas (não usado por padrão neste módulo)

**Campo no Odoo:** `API Token (MASTERKEY)` (quepasa_api_token)

### 3. SIGNING_SECRET (Opcional)
- **O que é:** Chave secreta para validar assinatura de webhooks
- **Onde configurar:** Arquivo `.env` do Quepasa (`SIGNING_SECRET=...`)
- **Usado para:** Validar que webhooks realmente vieram do Quepasa

**Status:** 🚧 Não implementado ainda (pendente)

## 📋 Como Obter o Bot Token

### Método 1: Interface Web do Quepasa

1. Acesse: `http://seu-servidor:31000`
2. Clique em "New Connection" ou "Adicionar Conexão"
3. Copie o **Token** gerado
4. Cole no campo **Bot Token** no Odoo

### Método 2: Variável de Ambiente

Edite `.env` do Quepasa:
```env
# Configurações globais
QUEPASA_PORT=31000
MASTERKEY=my_super_secret_masterkey_here
SIGNING_SECRET=my_webhook_signing_secret

# Tokens de conexões (opcional, melhor criar via web)
TOKEN_SUPORTE=abc123xyz789suporte
TOKEN_VENDAS=def456uvw012vendas
```

## 🔐 Headers da API

O Quepasa v3.25+ usa headers customizados com prefixo `X-QUEPASA-`:

### Cabeçalhos Comuns

```http
Content-Type: application/json
X-QUEPASA-TOKEN: seu_token_aqui
```

### Envio de Mensagem

```http
Content-Type: application/json
X-QUEPASA-TOKEN: seu_token_aqui
X-QUEPASA-CHATID: 5511999999999
X-QUEPASA-TRACKID: custom_tracking_id  (opcional)
```

### Exemplo com curl

```bash
# Enviar mensagem
curl -X POST "http://localhost:31000/send" \
  -H "Content-Type: application/json" \
  -H "X-QUEPASA-TOKEN: abc123xyz789" \
  -H "X-QUEPASA-CHATID: 5511999999999" \
  -d '{"text": "Hello from Odoo!"}'

# Obter QR Code
curl -X POST "http://localhost:31000/scan" \
  -H "Content-Type: application/json" \
  -H "X-QUEPASA-TOKEN: abc123xyz789"

# Verificar status
curl -X GET "http://localhost:31000/info" \
  -H "X-QUEPASA-TOKEN: abc123xyz789"

# Configurar webhook
curl -X POST "http://localhost:31000/webhook" \
  -H "Content-Type: application/json" \
  -H "X-QUEPASA-TOKEN: abc123xyz789" \
  -d '{
    "url": "https://seu-odoo.com/wa/webhook/quepasa/123",
    "forwardinternal": true
  }'
```

## 🔄 Diferenças vs Versões Anteriores

| Aspecto | v3.25+ (Atual) | Versões Antigas |
|---------|----------------|-----------------|
| **Token Global** | MASTERKEY (opcional) | WEBAPITOKEN (obrigatório) |
| **Token Bot** | Único por conexão | Gerado via API POST /bot |
| **Criação Bot** | Via Web/Env | Via API endpoint |
| **Header Auth** | X-QUEPASA-TOKEN | Authorization Bearer |
| **Endpoint Bot** | ❌ Removido | POST /bot, DELETE /bot/{id} |

## ⚠️ Migrando de Versões Antigas

Se você está migrando de uma versão antiga do Quepasa:

1. **WEBAPITOKEN → MASTERKEY**
   ```env
   # Antes
   WEBAPITOKEN=old_token_here
   
   # Agora (v3.25+)
   MASTERKEY=new_master_key_here
   ```

2. **Criar tokens via Web**
   - Não é mais possível criar via `POST /bot`
   - Use a interface web do Quepasa
   - Ou configure no `.env` do servidor

3. **Atualizar endpoints**
   - `/bot/{id}/send` → `/send` com header `X-QUEPASA-CHATID`
   - `/bot/{id}/qrcode` → `/scan`
   - `/bot/{id}` → `/info`

## 🛡️ Segurança

### ✅ Boas Práticas

1. **Nunca commit tokens no Git**
```bash
# Adicione ao .gitignore
.env
*.token
config/tokens.json
```

2. **Use HTTPS em produção**
```python
quepasa_url = "https://quepasa.suaempresa.com"  # ✅
# NÃO: "http://quepasa.suaempresa.com"  # ❌
```

3. **Rotacione tokens periodicamente**
   - Crie novo token na interface web
   - Atualize no Odoo
   - Remova token antigo do Quepasa

4. **Restrinja acesso ao servidor Quepasa**
```bash
# Firewall: aceite apenas IPs conhecidos
ufw allow from SEU_IP_ODOO to any port 31000
```

5. **Implemente validação de webhook** (pendente)
```python
# TODO: Validar assinatura com SIGNING_SECRET
import hmac
import hashlib

def validate_webhook(body, signature, secret):
    expected = hmac.new(
        secret.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

## 📚 Referências

- [Documentação Oficial Quepasa](https://github.com/sufficit/quepasa)
- [Swagger API](http://localhost:31000/swagger) (quando Quepasa estiver rodando)
- [Exemplos de Código](./examples.py)
- [Correção de Endpoints](./ENDPOINTS_FIX.md)
