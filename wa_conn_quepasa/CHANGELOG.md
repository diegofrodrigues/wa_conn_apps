# 🔄 Changelog - Atualização para Quepasa v3.25+

## Data: 2024
## Versão: 1.1.0 → 1.2.0

---

## 🎯 Resumo das Mudanças

O módulo foi completamente refatorado para ser compatível com a API do Quepasa v3.25+, que tem diferenças significativas em relação às versões anteriores.

---

## ✅ Endpoints Corrigidos

### Antes (Incorreto - baseado em Evolution API)
```python
# ❌ Endpoints que NÃO existem no Quepasa v3.25+
POST /bot                        # Criar bot
POST /bot/{id}/send             # Enviar mensagem
GET  /bot/{id}/qrcode           # QR Code
GET  /bot/{id}                  # Status
POST /bot/{id}/disconnect       # Desconectar
DELETE /bot/{id}                # Deletar bot
```

### Depois (Correto - Quepasa v3.25+)
```python
# ✅ Endpoints reais do Quepasa
POST /scan                      # Obter QR Code
POST /send                      # Enviar mensagem (com headers)
GET  /info                      # Status da conexão
POST /logout                    # Desconectar
POST /webhook                   # Configurar webhook
```

---

## 🔧 Mudanças no Código

### 1. Método `_headers()`

**Antes:**
```python
def _headers(self, use_bot_token=False):
    token = self.quepasa_bot_token if use_bot_token else self.quepasa_api_token
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    }
```

**Depois:**
```python
def _headers(self, chat_id=None, track_id=None):
    headers = {
        'Content-Type': 'application/json',
        'X-QUEPASA-TOKEN': self.quepasa_bot_token or self.quepasa_api_token or ''
    }
    if chat_id:
        headers['X-QUEPASA-CHATID'] = str(chat_id)
    if track_id:
        headers['X-QUEPASA-TRACKID'] = str(track_id)
    return headers
```

**Motivo:** Quepasa usa headers customizados `X-QUEPASA-*` ao invés de `Authorization: Bearer`

---

### 2. Método `send_text()`

**Antes:**
```python
def send_text(self, mobile, message):
    url = f"{self.quepasa_url}/bot/{bot_id}/send"
    payload = {
        'recipient': number,
        'message': message
    }
    resp = requests.post(url, json=payload, headers=self._headers(use_bot_token=True))
```

**Depois:**
```python
def send_text(self, mobile, message):
    url = f"{self.quepasa_url}/send"
    payload = {'text': message}
    headers = self._headers(chat_id=number)  # Número vai no header!
    resp = requests.post(url, json=payload, headers=headers)
```

**Mudanças:**
- ✅ Endpoint: `/bot/{id}/send` → `/send`
- ✅ Número do destinatário: body `recipient` → header `X-QUEPASA-CHATID`
- ✅ Campo da mensagem: `message` → `text`

---

### 3. Método `send_media()`

**Antes:**
```python
url = f"{self.quepasa_url}/bot/{bot_id}/send"
payload = {
    'recipient': number,
    'message': caption,
    'attachment': {...}
}
```

**Depois:**
```python
url = f"{self.quepasa_url}/send"
payload = {
    'text': caption,
    'attachment': {...}
}
headers = self._headers(chat_id=number)
```

**Mudanças:**
- ✅ Endpoint corrigido
- ✅ Número vai no header
- ✅ `message` → `text`

---

### 4. Método `connect()`

**Antes:**
```python
def connect(self):
    if not bot_id:
        return self.create_bot()  # Tenta criar bot via API
    
    url = f"{self.quepasa_url}/bot/{bot_id}/qrcode"
    resp = requests.get(url, headers=self._headers())
```

**Depois:**
```python
def connect(self):
    if not self.quepasa_bot_token:
        raise UserError(_("Please configure Bot Token first"))
    
    url = f"{self.quepasa_url}/scan"
    resp = requests.post(url, headers=self._headers())  # POST, não GET!
```

**Mudanças:**
- ✅ Endpoint: `/bot/{id}/qrcode` → `/scan`
- ✅ Método: GET → POST
- ✅ Não tenta mais criar bot via API (não existe no v3.25+)

---

### 5. Método `disconnect()`

**Antes:**
```python
url = f"{self.quepasa_url}/bot/{bot_id}/disconnect"
resp = requests.post(url, headers=self._headers())
```

**Depois:**
```python
url = f"{self.quepasa_url}/logout"
resp = requests.post(url, headers=self._headers())
```

**Mudanças:**
- ✅ Endpoint: `/bot/{id}/disconnect` → `/logout`

---

### 6. Método `check_status()`

**Antes:**
```python
url = f"{self.quepasa_url}/bot/{bot_id}"
resp = requests.get(url, headers=self._headers())
```

**Depois:**
```python
url = f"{self.quepasa_url}/info"
resp = requests.get(url, headers=self._headers())
```

**Mudanças:**
- ✅ Endpoint: `/bot/{id}` → `/info`

---

### 7. Método `create_bot()`

**Antes:**
```python
def create_bot(self):
    url = f"{self.quepasa_url}/bot"
    payload = {'name': bot_name, 'webhook': webhook_url}
    resp = requests.post(url, json=payload, headers=self._headers(use_bot_token=False))
    
    if ok:
        self.sudo().write({
            'quepasa_bot_id': data['id'],
            'quepasa_bot_token': data['token'],
            'bot_created': True
        })
```

**Depois:**
```python
def create_bot(self):
    """
    Quepasa v3.25+ não tem endpoint de criação de bot.
    Tokens são criados via interface web ou .env
    """
    if not self.quepasa_bot_token:
        raise UserError(_("Please configure Bot Token first"))
    
    # Apenas configura webhook se necessário
    if self.quepasa_webhook_enabled:
        self._configure_webhook()
    
    self.sudo().write({'bot_created': True})
```

**Mudanças:**
- ✅ Não cria mais bot via API (endpoint não existe)
- ✅ Apenas valida token e configura webhook
- ✅ Usuário deve obter token manualmente via web

---

### 8. Método `delete_bot()`

**Antes:**
```python
def delete_bot(self):
    url = f"{self.quepasa_url}/bot/{bot_id}"
    resp = requests.delete(url, headers=self._headers())
    
    if ok:
        self.sudo().write({
            'quepasa_bot_id': False,
            'bot_created': False
        })
```

**Depois:**
```python
def delete_bot(self):
    """
    Apenas limpa configuração local.
    Token continua existindo no servidor Quepasa.
    """
    self.sudo().write({
        'quepasa_bot_token': False,
        'bot_created': False,
        'qr_code': False,
        'state': 'disconnected',
    })
```

**Mudanças:**
- ✅ Não deleta mais via API (endpoint não existe)
- ✅ Apenas limpa dados locais

---

### 9. Novo Método `_configure_webhook()`

```python
def _configure_webhook(self):
    """Configura webhook no Quepasa"""
    url = f"{self.quepasa_url}/webhook"
    payload = {
        'url': self.webhook_url,
        'forwardinternal': True,
    }
    headers = self._headers()
    resp = requests.post(url, json=payload, headers=headers)
```

**Motivo:** Webhook agora é configurado via endpoint dedicado `/webhook`

---

## 📋 Campos Modificados

### Campo `quepasa_bot_id`
- **Status:** Mantido por compatibilidade, mas não mais usado
- **Motivo:** Quepasa v3.25+ não gera IDs de bot via API

### Campo `quepasa_api_token`
- **Antes:** WEBAPITOKEN (obrigatório)
- **Depois:** MASTERKEY (opcional, para operações administrativas)

### Campo `quepasa_bot_token`
- **Antes:** Gerado automaticamente ao criar bot
- **Depois:** Deve ser obtido manualmente via interface web ou .env

---

## 📚 Documentação Atualizada

### Novos Arquivos
- ✅ `ENDPOINTS_FIX.md` - Comparação detalhada endpoints antigos vs novos
- ✅ `README_V3.25.md` - Documentação específica para v3.25+
- ✅ `TOKENS_V3.25.md` - Guia completo de tokens v3.25+
- ✅ `CHANGELOG.md` - Este arquivo

### Arquivos Atualizados
- 📝 `models/wa_conn_quepasa_provider.py` - Todos os métodos refatorados
- 📝 `README.md` - Marcado para atualização (use README_V3.25.md)
- 📝 `TOKENS.md` - Marcado para atualização (use TOKENS_V3.25.md)

---

## 🔬 Teste Manual

### Como testar os novos endpoints:

```bash
# 1. Obter QR Code
curl -X POST "http://localhost:31000/scan" \
  -H "X-QUEPASA-TOKEN: seu_token_aqui"

# 2. Enviar mensagem
curl -X POST "http://localhost:31000/send" \
  -H "Content-Type: application/json" \
  -H "X-QUEPASA-TOKEN: seu_token_aqui" \
  -H "X-QUEPASA-CHATID: 5511999999999" \
  -d '{"text": "Teste do Odoo!"}'

# 3. Verificar status
curl -X GET "http://localhost:31000/info" \
  -H "X-QUEPASA-TOKEN: seu_token_aqui"

# 4. Configurar webhook
curl -X POST "http://localhost:31000/webhook" \
  -H "Content-Type: application/json" \
  -H "X-QUEPASA-TOKEN: seu_token_aqui" \
  -d '{
    "url": "https://seu-odoo.com/wa/webhook/quepasa/123",
    "forwardinternal": true
  }'
```

---

## ⚠️ Breaking Changes

### Para Usuários Existentes

1. **Token precisa ser reconfigurado**
   - WEBAPITOKEN → MASTERKEY (opcional)
   - Bot Token precisa ser obtido da interface web do Quepasa

2. **Botão "Create Bot" mudou comportamento**
   - Antes: Criava bot via API
   - Agora: Apenas valida token e configura webhook

3. **Campo Bot ID não é mais preenchido automaticamente**
   - Mantido apenas por compatibilidade

---

## 🎯 Próximos Passos

### Implementações Pendentes

- [ ] Validação de webhook com SIGNING_SECRET
- [ ] Testes automatizados para novos endpoints
- [ ] Migração automática de contas antigas
- [ ] Suporte para múltiplos tokens via .env
- [ ] Documentação de API completa

---

## 🤝 Contribuindo

Se você encontrar problemas com os novos endpoints:

1. Verifique a documentação: `README_V3.25.md`
2. Consulte exemplos: `ENDPOINTS_FIX.md`
3. Teste manualmente com curl
4. Reporte issues com logs completos

---

## 📖 Referências

- [Quepasa GitHub](https://github.com/sufficit/quepasa)
- [Quepasa API Docs](https://github.com/sufficit/quepasa/blob/main/docs/api.md)
- [Postman Collection](https://www.postman.com/sufficit-team/sufficit-public-workspace)
