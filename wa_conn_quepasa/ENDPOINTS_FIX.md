# Correção de Endpoints do Quepasa v3.25

## ❌ Endpoints Incorretos (implementação atual):
- POST `/bot` → criar bot
- POST `/bot/{bot_id}/send` → enviar mensagem
- GET `/bot/{bot_id}/qrcode` → obter QR code
- GET `/bot/{bot_id}` → status
- POST `/bot/{bot_id}/disconnect` → desconectar
- DELETE `/bot/{bot_id}` → deletar bot

## ✅ Endpoints Corretos (Quepasa v3.25):

### 1. Conectar e Obter QR Code
```
POST /scan
Headers:
  X-QUEPASA-USER: user_id
  X-QUEPASA-TOKEN: masterkey_or_token
Body: (empty)
```

### 2. Enviar Mensagem
```
POST /send
Headers:
  X-QUEPASA-TOKEN: token
  X-QUEPASA-CHATID: 5511999999999  (número do destinatário)
  X-QUEPASA-TRACKID: custom_id (opcional)
Body:
{
  "text": "Hello World!"
}
```

### 3. Enviar Mídia
```
POST /send
Headers:
  X-QUEPASA-TOKEN: token
  X-QUEPASA-CHATID: 5511999999999
Body:
{
  "text": "Caption here",
  "attachment": {
    "base64": "base64_encoded_content",
    "mimetype": "image/jpeg",
    "filename": "image.jpg"
  }
}
```

### 4. Configurar Webhook
```
POST /webhook
Headers:
  X-QUEPASA-TOKEN: token
Body:
{
  "url": "https://your-odoo.com/wa/webhook/quepasa/{bot_id}",
  "forwardinternal": true,
  "trackid": "custom-track",
  "extra": {
    "clientId": "12345"
  }
}
```

### 5. Verificar Status
```
GET /info
Headers:
  X-QUEPASA-TOKEN: token
```

## 📝 Observações Importantes:

1. **Não há endpoint `/bot`** - O Quepasa não gerencia "bots" como entidades separadas
2. **Token único** - Cada conexão/número tem seu próprio token gerado pelo Quepasa
3. **Headers customizados** - Usa `X-QUEPASA-*` ao invés de apenas `X-QUEPASA-TOKEN` no body
4. **CHATID** - O número do destinatário vai no header, não no body
5. **User management** - Usa `X-QUEPASA-USER` para gerenciar usuários/conexões

## 🔄 Mudanças Necessárias:

1. **Remover conceito de "bot"** - Quepasa trabalha com tokens de conexão
2. **Ajustar send_text()** - Usar headers corretos
3. **Ajustar send_media()** - Formato correto do attachment
4. **Ajustar connect()** - Usar `/scan` ao invés de `/bot/{id}/qrcode`
5. **Simplificar autenticação** - Um token por conexão, não MASTERKEY + Bot Token
