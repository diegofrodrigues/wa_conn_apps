# -*- coding: utf-8 -*-
{
    'name': 'WhatsApp Connector - Quepasa',
    'version': '18.0.1.0.0',
    'category': 'Discuss',
    'summary': 'WhatsApp integration using Quepasa API',
    'description': """
WhatsApp Connector - Quepasa Provider
======================================
This module provides WhatsApp integration using the Quepasa API.

Features:
---------
* Send and receive WhatsApp messages
* Media support (images, videos, documents, audio)
* QR Code generation for pairing
* Webhook support for real-time message reception
* Multi-device support
* Session management

Requirements:
-------------
* wa_conn base module
* Quepasa server instance running
* Valid WhatsApp Business API credentials
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'wa_conn',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/wa_conn_quepasa_provider_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
