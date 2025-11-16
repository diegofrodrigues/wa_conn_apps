# -*- coding: utf-8 -*-
{
    'name': 'WA Conn Bot',
    'version': '18.0.1.0.0',
    'category': 'WhatsApp Connector',
    'summary': 'WhatsApp Bot with Flow Builder and Custom Commands',
    'description': """
        WhatsApp Bot Module
        ===================
        * Flow builder with conditions and greetings
        * Session management with timeout
        * Custom commands with Python code execution
        * Integration with wa_account and provider
        * Automatic or manual initialization
    """,
    'author': 'Diego Ferreira Rodrigues',
    'website': 'https://bitconn.com.br',
    'depends': [
        'base',
        'mail',
        'wa_conn',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/wa_bot_views.xml',
        'views/wa_bot_command_views.xml',
        'views/wa_bot_flow_views.xml',
        'views/wa_bot_session_views.xml',
        'views/wa_account_views.xml',
        'views/wa_conn_bot_menus.xml',
        # 'data/wa_bot_user.xml',
    ],
    'demo': [
        'data/demo_commands.xml',
        'data/demo_flow_menu.xml',
        'data/demo_flow_partner.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
