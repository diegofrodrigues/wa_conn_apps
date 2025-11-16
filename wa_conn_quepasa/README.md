# WhatsApp Connector - Quepasa Provider

Módulo de integração do Odoo com WhatsApp usando a API Quepasa.

## Descrição

Este módulo adiciona suporte ao provider **Quepasa** no módulo base `wa_conn`, permitindo que você conecte sua instância Odoo ao WhatsApp através da API open-source Quepasa.

## Características

- ✅ Envio e recebimento de mensagens de texto
- ✅ Suporte a mídias (imagens, vídeos, áudios, documentos)
- ✅ Geração de QR Code para pareamento
- ✅ Webhook para recepção de mensagens em tempo real
- ✅ Gerenciamento de bots via interface Odoo
- ✅ Multi-conta (múltiplos números WhatsApp)

## Requisitos

### Dependências Odoo
- `wa_conn` - Módulo base de conectores WhatsApp

### Requisitos Externos
- Servidor Quepasa rodando e acessível
- Token de autenticação do Quepasa
- Python `requests` library

## Instalação

1. Clone ou copie este módulo para o diretório `custom_addons`:
```bash
cd /path/to/odoo/custom_addons
# Módulo já deve estar em: custom_addons/wa_conn_quepasa/
```

2. Certifique-se de que o módulo `wa_conn` está instalado

3. Atualize a lista de módulos:
```
Odoo → Apps → Update Apps List
```

4. Instale o módulo:
```
Odoo → Apps → Search: "WhatsApp Connector - Quepasa" → Install
```

## Configuração

### 1. Configurar Servidor Quepasa

Certifique-se de que você tem:
- URL do servidor Quepasa (ex: `https://seu-quepasa.com`)
- Token de autenticação (API Token)

### 2. Criar Conta WhatsApp no Odoo

1. Vá para: **Discuss → Configuration → WhatsApp Accounts**
2. Clique em **Create**
3. Preencha os campos:
   - **Name**: Nome da conta (ex: "Suporte WhatsApp")
   - **Provider**: Selecione **Quepasa**
   - **Quepasa Server URL**: URL do seu servidor Quepasa
   - **API Token**: Token de autenticação

### 3. Criar Bot

1. Na aba **Quepasa Settings**, clique em **Create Bot**
2. O sistema criará automaticamente um bot no Quepasa
3. O **Bot ID** será preenchido automaticamente

### 4. Conectar WhatsApp

1. Clique em **Connect / Get QR Code**
2. Um QR Code será exibido
3. Abra o WhatsApp no seu celular
4. Vá em **Configurações → Dispositivos Conectados → Conectar Dispositivo**
5. Escaneie o QR Code
6. Aguarde a conexão (o status mudará para "Connected")

### 5. Configurar Webhook (Automático)

1. O webhook é configurado automaticamente ao clicar em **"Create Bot"**
2. A URL gerada usa o padrão do `wa_conn`: `https://seu-odoo.com/wa/webhook/<webhook_uuid>`
3. O sistema envia a URL automaticamente para o Quepasa
4. Você pode regenerar a URL clicando em **"Generate New Webhook URL"**

**Nota**: Este módulo usa o controller base do `wa_conn`, não possui controller personalizado.

## Uso

### Enviar Mensagens

As mensagens podem ser enviadas através de:
- Módulo `wa_conn_bot` (Bot conversacional)
- Módulo `wa_conn_marketing` (Campanhas)
- Interface Discuss (conversas diretas)
- API programática

### Receber Mensagens

Com o webhook configurado, todas as mensagens recebidas aparecerão automaticamente no Discuss como conversas.

## Estrutura da API Quepasa

### Endpoints Utilizados

#### Criar Bot
```http
POST /bot
Content-Type: application/json
X-QUEPASA-TOKEN: seu_token

{
  "name": "Nome do Bot",
  "webhook": "https://seu-odoo.com/wa/webhook/quepasa"
}
```

#### Obter QR Code
```http
GET /bot/{bot_id}/qrcode
X-QUEPASA-TOKEN: seu_token
```

#### Enviar Mensagem de Texto
```http
POST /bot/{bot_id}/send
Content-Type: application/json
X-QUEPASA-TOKEN: seu_token

{
  "recipient": "5511999999999",
  "message": "Olá!"
}
```

#### Enviar Mídia
```http
POST /bot/{bot_id}/send
Content-Type: application/json
X-QUEPASA-TOKEN: seu_token

{
  "recipient": "5511999999999",
  "message": "Legenda da imagem",
  "attachment": {
    "mimetype": "image/jpeg",
    "filename": "imagem.jpg",
    "base64": "base64_encoded_content"
  }
}
```

#### Verificar Status
```http
GET /bot/{bot_id}
X-QUEPASA-TOKEN: seu_token
```

#### Desconectar
```http
POST /bot/{bot_id}/disconnect
X-QUEPASA-TOKEN: seu_token
```

#### Deletar Bot
```http
DELETE /bot/{bot_id}
X-QUEPASA-TOKEN: seu_token
```

## Formato do Webhook

### Mensagem Recebida (Inbound)

```json
{
  "id": "message_id_123",
  "timestamp": 1234567890,
  "from": "5511999999999",
  "participant": "5511999999999",
  "recipient": "5511888888888",
  "text": "Olá!",
  "type": "text",
  "fromMe": false,
  "pushName": "Nome do Contato"
}
```

### Mídia Recebida

```json
{
  "id": "message_id_456",
  "timestamp": 1234567890,
  "from": "5511999999999",
  "participant": "5511999999999",
  "recipient": "5511888888888",
  "type": "image",
  "caption": "Olhe esta foto",
  "fromMe": false,
  "attachment": {
    "mimetype": "image/jpeg",
    "filename": "foto.jpg",
    "url": "https://..."
  }
}
```

## Troubleshooting

### QR Code não aparece
- Verifique se a URL do Quepasa está correta
- Verifique se o token de autenticação está correto
- Verifique logs do Odoo e do Quepasa

### Mensagens não são recebidas
- Verifique se o webhook está configurado corretamente no Quepasa
- Teste a URL do webhook manualmente
- Verifique se o Quepasa consegue alcançar seu Odoo (firewall, HTTPS)

### Bot não conecta
- Clique em "Refresh QR Code"
- Tente desconectar e reconectar
- Verifique se o bot não está conectado em outro lugar

### Erros de API
- Verifique logs do Odoo: `Settings → Technical → Logging`
- Verifique logs do Quepasa
- Teste os endpoints manualmente com curl/Postman

## Comparação com Evolution API

| Característica | Quepasa | Evolution API |
|----------------|---------|---------------|
| Open Source | ✅ | ✅ |
| Multi-device | ✅ | ✅ |
| Webhooks | ✅ | ✅ |
| Mídias | ✅ | ✅ |
| Reações | ❌ | ✅ |
| Status/Stories | ❌ | ✅ |
| Grupos | ✅ | ✅ |
| Auto-reject calls | ❌ | ✅ |

## Suporte

Para suporte e dúvidas:
- Issues: GitHub do projeto
- Email: suporte@yourcompany.com

## Licença

LGPL-3

## Autor

Your Company - 2025

## Changelog

### Version 18.0.1.0.0
- Release inicial
- Suporte básico a texto e mídia
- Webhook inbound
- Gerenciamento de bots
- QR Code pairing
