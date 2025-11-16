# -*- coding: utf-8 -*-
"""
Exemplos de uso do módulo wa_conn_quepasa

Este arquivo contém exemplos de como usar a API do Quepasa programaticamente no Odoo.
"""

# ============================================================================
# EXEMPLO 1: Buscar uma conta Quepasa
# ============================================================================
def get_quepasa_account(env):
    """Busca a primeira conta Quepasa ativa"""
    account = env['wa.account'].search([
        ('provider', '=', 'quepasa'),
        ('state', '=', 'connected'),
    ], limit=1)
    return account


# ============================================================================
# EXEMPLO 2: Enviar mensagem de texto simples
# ============================================================================
def send_text_message(env, mobile, message):
    """
    Envia uma mensagem de texto via Quepasa
    
    Args:
        env: Environment do Odoo
        mobile: Número do telefone (ex: '5511999999999')
        message: Texto da mensagem
    """
    account = get_quepasa_account(env)
    if not account:
        return {'error': 'No Quepasa account found'}
    
    result = account.send_text(mobile, message)
    return result


# ============================================================================
# EXEMPLO 3: Enviar imagem com legenda
# ============================================================================
def send_image_message(env, mobile, image_path, caption=''):
    """
    Envia uma imagem com legenda via Quepasa
    
    Args:
        env: Environment do Odoo
        mobile: Número do telefone
        image_path: Caminho do arquivo de imagem
        caption: Legenda da imagem (opcional)
    """
    import base64
    
    account = get_quepasa_account(env)
    if not account:
        return {'error': 'No Quepasa account found'}
    
    # Lê o arquivo e converte para base64
    with open(image_path, 'rb') as f:
        image_data = f.read()
        image_b64 = base64.b64encode(image_data).decode()
    
    result = account.send_media(
        mobile,
        caption=caption,
        b64=image_b64,
        mime='image/jpeg',
        filename='imagem.jpg'
    )
    return result


# ============================================================================
# EXEMPLO 4: Enviar documento PDF
# ============================================================================
def send_pdf_document(env, mobile, pdf_path, caption=''):
    """
    Envia um documento PDF via Quepasa
    
    Args:
        env: Environment do Odoo
        mobile: Número do telefone
        pdf_path: Caminho do arquivo PDF
        caption: Legenda do documento (opcional)
    """
    import base64
    import os
    
    account = get_quepasa_account(env)
    if not account:
        return {'error': 'No Quepasa account found'}
    
    # Lê o arquivo e converte para base64
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
        pdf_b64 = base64.b64encode(pdf_data).decode()
    
    filename = os.path.basename(pdf_path)
    
    result = account.send_media(
        mobile,
        caption=caption,
        b64=pdf_b64,
        mime='application/pdf',
        filename=filename
    )
    return result


# ============================================================================
# EXEMPLO 5: Criar e conectar um novo bot Quepasa
# ============================================================================
def create_and_connect_bot(env, name, quepasa_url, token):
    """
    Cria uma nova conta Quepasa e conecta ao WhatsApp
    
    Args:
        env: Environment do Odoo
        name: Nome da conta
        quepasa_url: URL do servidor Quepasa
        token: Token de autenticação
        
    Returns:
        tuple: (account, qrcode_result)
    """
    # Cria a conta
    account = env['wa.account'].create({
        'name': name,
        'provider': 'quepasa',
        'quepasa_url': quepasa_url,
        'quepasa_token': token,
        'quepasa_webhook_enabled': True,
    })
    
    # Cria o bot no Quepasa
    create_result = account.create_bot()
    if not create_result.get('ok'):
        return account, {'error': 'Failed to create bot', 'details': create_result}
    
    # Conecta e obtém QR Code
    connect_result = account.connect()
    
    return account, connect_result


# ============================================================================
# EXEMPLO 6: Verificar status de conexão
# ============================================================================
def check_connection_status(env, account_id):
    """
    Verifica o status de conexão de uma conta Quepasa
    
    Args:
        env: Environment do Odoo
        account_id: ID da conta wa.account
        
    Returns:
        dict: Status da conexão
    """
    account = env['wa.account'].browse(account_id)
    if account.provider != 'quepasa':
        return {'error': 'Not a Quepasa account'}
    
    result = account.check_status()
    return result


# ============================================================================
# EXEMPLO 7: Enviar mensagem para múltiplos contatos
# ============================================================================
def send_broadcast_message(env, mobile_list, message):
    """
    Envia a mesma mensagem para múltiplos contatos
    
    Args:
        env: Environment do Odoo
        mobile_list: Lista de números de telefone
        message: Texto da mensagem
        
    Returns:
        dict: Resultados do envio para cada número
    """
    account = get_quepasa_account(env)
    if not account:
        return {'error': 'No Quepasa account found'}
    
    results = {}
    for mobile in mobile_list:
        result = account.send_text(mobile, message)
        results[mobile] = result
    
    return results


# ============================================================================
# EXEMPLO 8: Processar mensagem recebida manualmente
# ============================================================================
def process_inbound_message(env, account_id, payload):
    """
    Processa manualmente uma mensagem recebida do webhook
    
    Args:
        env: Environment do Odoo
        account_id: ID da conta wa.account
        payload: Payload do webhook Quepasa
        
    Returns:
        dict: Resultado do processamento
    """
    account = env['wa.account'].browse(account_id)
    if account.provider != 'quepasa':
        return {'error': 'Not a Quepasa account'}
    
    result = account.inbound_handle(payload)
    return result


# ============================================================================
# EXEMPLO 9: Atualizar configurações do webhook
# ============================================================================
def update_webhook_config(env, account_id, enabled=True):
    """
    Atualiza as configurações do webhook
    
    Args:
        env: Environment do Odoo
        account_id: ID da conta wa.account
        enabled: True para habilitar, False para desabilitar
    """
    account = env['wa.account'].browse(account_id)
    account.write({
        'quepasa_webhook_enabled': enabled,
    })
    
    # Se já existe bot criado, pode ser necessário recriar
    # para aplicar as novas configurações de webhook
    if account.bot_created and enabled:
        # Pega a URL do webhook
        webhook_url = account.webhook_url
        print(f"Configure this webhook URL in Quepasa: {webhook_url}")


# ============================================================================
# EXEMPLO 10: Desconectar e deletar bot
# ============================================================================
def disconnect_and_delete_bot(env, account_id):
    """
    Desconecta e deleta o bot Quepasa
    
    Args:
        env: Environment do Odoo
        account_id: ID da conta wa.account
        
    Returns:
        dict: Resultado da operação
    """
    account = env['wa.account'].browse(account_id)
    if account.provider != 'quepasa':
        return {'error': 'Not a Quepasa account'}
    
    # Desconecta
    disconnect_result = account.disconnect()
    
    # Deleta o bot
    delete_result = account.delete_bot()
    
    return {
        'disconnect': disconnect_result,
        'delete': delete_result,
    }


# ============================================================================
# EXEMPLO 11: Uso no shell do Odoo
# ============================================================================
"""
Para testar no shell do Odoo:

$ odoo-bin shell -c odoo.conf -d your_database

>>> # Importa o ambiente
>>> env = api.Environment(cr, SUPERUSER_ID, {})

>>> # Busca conta Quepasa
>>> account = env['wa.account'].search([('provider', '=', 'quepasa')], limit=1)

>>> # Envia mensagem
>>> result = account.send_text('5511999999999', 'Olá do Odoo!')
>>> print(result)

>>> # Verifica status
>>> status = account.check_status()
>>> print(status)

>>> # Obtém QR Code
>>> qr_result = account.connect()
>>> print(qr_result.get('qrcode_b64'))
"""


# ============================================================================
# EXEMPLO 12: Integração com res.partner
# ============================================================================
def send_message_to_partner(env, partner_id, message):
    """
    Envia mensagem para um parceiro do Odoo
    
    Args:
        env: Environment do Odoo
        partner_id: ID do res.partner
        message: Texto da mensagem
        
    Returns:
        dict: Resultado do envio
    """
    partner = env['res.partner'].browse(partner_id)
    mobile = partner.mobile or partner.phone
    
    if not mobile:
        return {'error': 'Partner has no mobile number'}
    
    account = get_quepasa_account(env)
    if not account:
        return {'error': 'No Quepasa account found'}
    
    result = account.send_text(mobile, message)
    return result
