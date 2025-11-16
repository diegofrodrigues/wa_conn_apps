# Debug: bot_token_missing Error

## Problema
Ao chamar `send_text('número', 'Hello João Grilo')`, está retornando `{'ok': False, 'error': 'bot_token_missing'}`.

## Causa
O campo `quepasa_bot_token` está vazio ou `None` no registro `wa.account` que você está usando.

## Verificação

### 1. Via Python Console no Odoo

```python
# No shell do Odoo (./odoo-bin shell -c odoo.conf)
account = env['wa.account'].search([('provider', '=', 'quepasa')], limit=1)

# Verifica se encontrou o registro
print(f"Account ID: {account.id}")
print(f"Account Name: {account.name}")
print(f"Provider: {account.provider}")

# IMPORTANTE: Verifica o Bot Token
print(f"Bot Token: {account.quepasa_bot_token}")
print(f"Bot Token is empty? {not account.quepasa_bot_token}")

# Verifica URL também
print(f"Quepasa URL: {account.quepasa_url}")
```

### 2. Via Interface Web

1. Acesse **WhatsApp Connector > Accounts**
2. Abra o registro com provider **Quepasa**
3. Verifique se o campo **Bot Token** está preenchido
4. Se estiver vazio, você precisa:
   - Acessar a interface web do Quepasa (https://quepasa-api.bitconn.com.br)
   - Obter o token de uma conexão existente
   - Colar no campo **Bot Token**
   - Salvar o registro

### 3. Testando send_text Corretamente

```python
# Shell do Odoo
account = env['wa.account'].search([('provider', '=', 'quepasa')], limit=1)

# Configura o token se ainda não tiver (SUBSTITUA pelo seu token real)
if not account.quepasa_bot_token:
    account.write({
        'quepasa_bot_token': 'SEU_TOKEN_AQUI',
        'quepasa_url': 'https://quepasa-api.bitconn.com.br'
    })

# Agora testa o envio
result = account.send_text('5511999999999', 'Hello João Grilo')
print(result)
```

## Solução Rápida

### Opção 1: Configurar via Interface Web
1. Menu: **WhatsApp Connector > Accounts**
2. Abrir registro Quepasa
3. Preencher campo **Bot Token**
4. Salvar

### Opção 2: Configurar via Shell

```python
# ./odoo-bin shell -c odoo.conf

account = env['wa.account'].search([('provider', '=', 'quepasa')], limit=1)

# Substitua pelo seu token real do Quepasa
account.write({
    'quepasa_bot_token': 'SeuTokenAqui123...',
    'quepasa_url': 'https://quepasa-api.bitconn.com.br'
})

env.cr.commit()
```

## Checklist de Verificação

- [ ] Existe um registro `wa.account` com `provider='quepasa'`?
- [ ] O campo `quepasa_bot_token` está preenchido?
- [ ] O campo `quepasa_url` está correto?
- [ ] Você está chamando `send_text()` no registro correto?
- [ ] O token foi obtido da interface web do Quepasa?

## Exemplo de Chamada Correta

```python
# Certifique-se de chamar no registro correto
account = env['wa.account'].browse(ID_DO_REGISTRO)  # Substitua pelo ID correto

# OU buscar por nome/provider
account = env['wa.account'].search([
    ('provider', '=', 'quepasa'),
    ('name', '=', 'Nome da Sua Conta')
], limit=1)

# Verifica antes de usar
if not account:
    print("ERRO: Nenhuma conta Quepasa encontrada!")
elif not account.quepasa_bot_token:
    print("ERRO: Bot Token não configurado!")
else:
    # Agora sim, envia a mensagem
    result = account.send_text('5511999999999', 'Hello João Grilo')
    print(f"Resultado: {result}")
```

## Log Detalhado

Para adicionar logs detalhados ao método `send_text()`, você pode adicionar estas linhas logo no início:

```python
def send_text(self, mobile, message):
    """Envia mensagem de texto via Quepasa"""
    _logger.info(f"=== send_text() called ===")
    _logger.info(f"Account ID: {self.id}")
    _logger.info(f"Account Name: {self.name}")
    _logger.info(f"Provider: {self.provider}")
    _logger.info(f"Mobile: {mobile}")
    _logger.info(f"Message: {message}")
    _logger.info(f"Bot Token present? {bool(self.quepasa_bot_token)}")
    _logger.info(f"Quepasa URL: {self.quepasa_url}")
    
    number = self._fmt_number(mobile)
    # ... resto do código
```

Isso vai ajudar a debugar exatamente qual registro está sendo usado e por que o token está vazio.
