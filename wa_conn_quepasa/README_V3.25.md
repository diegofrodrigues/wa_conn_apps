# WhatsApp Connector - Quepasa Provider v3.25+

Módulo de integração do Odoo 18 com API do Quepasa v3.25+.

## 🎯 Características

- ✅ Envio de mensagens de texto e mídia
- ✅ Recebimento de mensagens via webhook
- ✅ QR Code para conexão com WhatsApp
- ✅ Gerenciamento de status de conexão
- ✅ Suporte a múltiplas contas WhatsApp
- ✅ Integração com discuss.channel do Odoo

## 📋 Requisitos

- Odoo 18.0
- Módulo `wa_conn` (base)
- Servidor Quepasa v3.25+ configurado e rodando
- Python 3.10+
- Biblioteca `requests`

## 🔧 Instalação

1. **Clone o repositório no diretório custom_addons:**
```bash
cd /path/to/odoo/custom_addons
# Assume que wa_conn já está instalado
```

2. **Instale as dependências Python:**
```bash
pip install requests
```

3. **Atualize a lista de aplicativos no Odoo:**
   - Apps → Update Apps List

4. **Instale o módulo:**
   - Apps → Search "WhatsApp Connector Quepasa" → Install

## ⚙️ Configuração

### 1. Configure o Token no Quepasa

O Quepasa v3.25+ não possui interface de criação de bots via API. Você precisa:

**Opção A: Via Interface Web**
1. Acesse a interface web do Quepasa: `http://seu-servidor:port`
2. Crie uma nova conexão/bot
3. Copie o Token gerado

**Opção B: Via Arquivo .env**
```env
QUEPASA_PORT=31000
SIGNING_SECRET=seu_signing_secret_aqui
MASTERKEY=seu_masterkey_aqui

# Token para cada conexão (opcional, pode criar via web)
# TOKEN_1=token_da_conexao_1
```

### 2. Configure no Odoo

1. Vá para **Discuss → WhatsApp → Accounts**
2. Crie um novo registro:
   - **Provider:** Quepasa
   - **Name:** Nome da conta (ex: "Suporte WhatsApp")
   - **Quepasa Server URL:** `http://seu-servidor:31000`
   - **Bot Token:** Cole o token obtido do Quepasa
   
3. **Opcional:** Configure MASTERKEY em **API Token** se precisar gerenciar múltiplas conexões

### 3. Conecte ao WhatsApp

1. Clique no botão **"Connect"** no header do formulário
2. Escaneie o QR Code com WhatsApp
3. Clique em **"Check Status"** para verificar conexão

### 4. Configure Webhook (Opcional)

Para receber mensagens:
1. Marque **"Enable Webhook"**
2. Configure no Quepasa o webhook URL mostrado no campo **"Webhook URL"**

## 🔌 Endpoints da API Quepasa v3.25

Este módulo usa os seguintes endpoints:

| Método | Endpoint | Descrição | Headers |
|--------|----------|-----------|---------|
| POST | `/scan` | Gera QR Code para conexão | `X-QUEPASA-TOKEN` |
| POST | `/send` | Envia mensagem | `X-QUEPASA-TOKEN`, `X-QUEPASA-CHATID` |
| GET | `/info` | Status da conexão | `X-QUEPASA-TOKEN` |
| POST | `/logout` | Desconecta | `X-QUEPASA-TOKEN` |
| POST | `/webhook` | Configura webhook | `X-QUEPASA-TOKEN` |

### Exemplo de Envio

```python
# Via Python
account = env['wa.account'].search([('provider', '=', 'quepasa')], limit=1)
result = account.send_text('5511999999999', 'Olá do Odoo!')

# Via curl
curl -X POST "http://localhost:31000/send" \
  -H "Content-Type: application/json" \
  -H "X-QUEPASA-TOKEN: seu_token_aqui" \
  -H "X-QUEPASA-CHATID: 5511999999999" \
  -d '{"text": "Hello World!"}'
```

## 📚 Uso

### Enviar Mensagem de Texto

```python
account = self.env['wa.account'].search([('provider', '=', 'quepasa')], limit=1)
result = account.send_text('5511999999999', 'Olá!')
if result['ok']:
    print(f"Mensagem enviada! ID: {result['id']}")
```

### Enviar Mídia

```python
import base64

# Ler arquivo
with open('/path/to/image.jpg', 'rb') as f:
    b64_data = base64.b64encode(f.read()).decode()

# Enviar
result = account.send_media(
    '5511999999999',
    caption='Veja esta imagem!',
    b64=b64_data,
    mime='image/jpeg',
    filename='imagem.jpg'
)
```

## 🔍 Troubleshooting

### Erro: "bot_token_missing"
- Configure o **Bot Token** no formulário da conta
- Verifique se o token está correto no Quepasa

### QR Code não aparece
- Verifique se a URL do servidor está correta
- Teste manualmente: `curl -X POST http://seu-servidor:31000/scan -H "X-QUEPASA-TOKEN: seu_token"`

### Webhook não recebe mensagens
- Verifique se **Enable Webhook** está marcado
- Configure a URL no Quepasa: `POST /webhook` com body `{"url": "https://seu-odoo.com/wa/webhook/quepasa/ID"}`
- Verifique logs do Quepasa

### Mensagens não são enviadas
- Verifique status: Clique em **"Check Status"**
- Certifique-se que está conectado (status "connected")
- Verifique formato do número: `5511999999999` (sem + ou espaços)

## 📖 Documentação Adicional

- [Tokens e Autenticação](./TOKENS.md)
- [Exemplos de Código](./examples.py)
- [Correção de Endpoints](./ENDPOINTS_FIX.md)
- [Documentação Oficial Quepasa](https://github.com/sufficit/quepasa)

## 🔐 Segurança

- **Nunca exponha seus tokens** em logs ou repositórios públicos
- Use HTTPS para comunicação com Quepasa em produção
- Configure firewall para proteger servidor Quepasa
- Implemente validação de assinatura de webhook com `SIGNING_SECRET`

## 🤝 Suporte

Para issues e dúvidas:
- Issues: GitHub do projeto
- Documentação Quepasa: https://github.com/sufficit/quepasa

## 📄 Licença

LGPL-3.0

## 🎯 Diferenças vs Evolution API

| Recurso | Quepasa v3.25 | Evolution API |
|---------|---------------|---------------|
| Criação de Bot | Via Web/Env | Via API POST /bot |
| Headers | X-QUEPASA-* | Authorization Bearer |
| Endpoint Envio | POST /send | POST /bot/{id}/send |
| QR Code | POST /scan | GET /bot/{id}/qrcode |
| Status | GET /info | GET /bot/{id} |
| Chat ID | Header | Body payload |
