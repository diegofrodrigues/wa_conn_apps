# -*- coding: utf-8 -*-
"""
This module registers bot hooks for wa.provider.evolution.
The actual bot processing happens in discuss.channel.wa_post_incoming override.
This file exists to ensure compatibility with wa_conn_evolution.
"""

def post_init_hook(env):
    """Hook called after module installation"""
    import logging
    _logger = logging.getLogger(__name__)
    
    if 'wa.provider.evolution' in env:
        _logger.info('wa_conn_bot: Bot integration ready for wa.provider.evolution channels')
    else:
        _logger.info('wa_conn_bot: wa.provider.evolution not installed - bot will work when provider is added')
