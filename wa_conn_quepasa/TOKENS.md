# Configuração de Tokens no Quepasa

O Quepasa utiliza **dois tipos de tokens** diferentes para autenticação:

---

## 🔐 SIGNING_SECRET

### O que é?
Chave secreta usada para validar a autenticidade dos webhooks recebidos do Quepasa.

### Para que serve?
- Garantir que os webhooks recebidos vieram realmente do seu servidor Quepasa
- Evitar ataques de falsificação de webhooks

### Status no Módulo
⚠️ **Ainda não implementado** - O módulo atualmente aceita webhooks sem validação.

### Implementação Futura
```python
# Exemplo de como validar o webhook (a ser implementado)
import hmac
import hashlib

def validate_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## 📋 Resumo das Chaves (Quepasa v3.25+)

| Chave | Localização | Uso | No Odoo |
|-------|-------------|-----|---------|
| **MASTERKEY** | `.env` do Quepasa | Gerenciar bots (criar/deletar) | Campo "API Token (MASTERKEY)" |
| **SIGNING_SECRET** | `.env` do Quepasa | Validar webhooks | Não implementado ainda |
| **Bot Token** | Gerado pela API | Enviar mensagens | Campo "Bot Token" (auto) |

---

## 1. 🔑 MASTERKEY (API Token Global) - v3.25+

### O que é?
Token global da API do Quepasa configurado no arquivo `.env` do servidor Quepasa.

**Nota:** Versões antigas do Quepasa usavam `WEBAPITOKEN`. A partir da v3.25, o nome mudou para `MASTERKEY`.

### Para que serve?
- **Criar bots** novos
- **Deletar bots** existentes
- **Gerenciar** configurações globais
- **Listar** todos os bots

### Onde encontrar?
No arquivo `.env` do seu servidor Quepasa:
```env
MASTERKEY=seu_token_global_aqui
SIGNING_SECRET=seu_signing_secret_aqui
```

### Como usar no Odoo?
Preencha o campo **"API Token (MASTERKEY)"** na configuração da conta WhatsApp.

## 2. 🤖 Bot Token (Token Individual)

### O que é?
Token específico de cada bot criado. É gerado automaticamente quando você cria um bot.

### Para que serve?
- **Enviar mensagens** de texto
- **Enviar mídias** (imagens, vídeos, documentos)
- **Operações** específicas deste bot

### Onde encontrar?
- Gerado automaticamente ao criar o bot
- Pode ser obtido pela API: `GET /bot/{bot_id}`
- **No Odoo**: Salvo automaticamente no campo **"Bot Token"** (readonly)

### Como funciona no Odoo?
É preenchido automaticamente quando você clica em "Create Bot".

---

## 📋 Fluxo de Configuração no Odoo

### Passo 1: Configurar Credenciais
1. Acesse **Discuss → Configuration → WhatsApp Accounts**
2. Crie uma nova conta ou edite uma existente
3. Selecione **Provider: Quepasa**
4. Preencha:
   - **Quepasa Server URL**: `https://seu-quepasa.com`
   - **API Token (MASTERKEY)**: O MASTERKEY do arquivo `.env` do Quepasa

### Passo 2: Criar o Bot
1. Clique no botão **"Create Bot"** no header
2. O sistema irá:
   - Criar o bot no Quepasa usando o WEBAPITOKEN
   - Salvar o **Bot ID** automaticamente
   - Salvar o **Bot Token** automaticamente (se retornado pela API)

### Passo 3: Conectar ao WhatsApp
1. Clique em **"Connect"** no header
2. Um **QR Code** será gerado
3. Escaneie com WhatsApp
4. Aguarde a conexão

---

## 🔐 Exemplo de Uso dos Tokens

### Criar Bot (usa MASTERKEY)
```bash
curl -X POST https://seu-quepasa.com/bot \
  -H "X-QUEPASA-TOKEN: seu_masterkey_aqui" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Meu Bot Odoo",
    "webhook": "https://seu-odoo.com/wa/webhook/quepasa/{bot_id}"
  }'
```

### Enviar Mensagem (usa Bot Token)
```bash
curl -X POST https://seu-quepasa.com/bot/{bot_id}/send \
  -H "X-QUEPASA-TOKEN: token_do_bot_aqui" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": "5511999999999",
    "message": "Olá!"
  }'
```

---

## ⚠️ Segurança

1. **Nunca compartilhe** seus tokens
2. **Mantenha o MASTERKEY seguro** - ele pode criar/deletar bots
3. **SIGNING_SECRET** é usado para validar webhooks (não implementado ainda no módulo)
4. **Bot Token** é menos crítico - só afeta um bot específico
5. Use **HTTPS** sempre
6. Rotacione tokens periodicamente

---

## 🐛 Troubleshooting

### Erro: "Please configure API Token (MASTERKEY) first"
- ✅ Verifique se preencheu o campo "API Token (MASTERKEY)"
- ✅ Confirme que o token está correto no `.env` do Quepasa
- ✅ Teste o token manualmente com curl

### Erro ao enviar mensagens
- ✅ Verifique se o Bot Token foi salvo corretamente
- ✅ Confirme que o bot está conectado (estado "connected")
- ✅ Teste com curl usando o Bot Token

### Bot Token não foi salvo automaticamente
- 🔧 Algumas versões do Quepasa não retornam o token na criação
- 🔧 Você pode obter o token pela API: `GET /bot/{bot_id}`
- 🔧 Preencha manualmente o campo "Bot Token" (se necessário)

---

## 📚 Referências

- [Documentação oficial do Quepasa](https://github.com/nocodeleaks/quepasa)
- [API Endpoints do Quepasa](https://github.com/nocodeleaks/quepasa/wiki/API)
