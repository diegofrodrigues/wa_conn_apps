{
    'name': 'WhatsApp Connector - Evolution API Plugin',
    'version': '18.0.1.0.0',
    'category': 'Social Network/WhatsApp',
    'summary': 'Evolution API provider plugin for wa_conn',
    'description': '''
        Evolution API Provider Plugin
        ==============================
        
        This module provides Evolution API integration for wa_conn base module.
        
        Features:
        ---------
        * Full Evolution API v2 support
        * Webhook handling with event normalization
        * Text and media message support
        * QR Code authentication
        * Instance lifecycle management
        * Profile image fetching
        * Automatic partner creation
        * Channel integration
        
        Requirements:
        -------------
        * wa_conn (base module)
        * Evolution API server running
        
        Configuration:
        --------------
        1. Install this plugin module
        2. Create a new WhatsApp Account in wa_conn
        3. Select "Evolution" as provider
        4. Configure API URL and API Key
        5. Create instance and connect
    ''',
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'depends': [
        'wa_conn',  # Base module dependency
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/wa_api_event_views.xml',
        'views/wa_account_evolution_views.xml',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
