# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class WAAccountBot(models.Model):
    """Extend wa.account to add bot support"""
    _inherit = 'wa.account'

    # Bot Configuration
    bot_enabled = fields.Boolean(
        string='Enable Bot',
        default=False,
        tracking=True,
        help='Enable bot to automatically handle incoming messages'
    )
    
    bot_id = fields.Many2one(
        'wa.bot',
        string='Active Bot',
        tracking=True,
        help='Bot that will handle messages for this account'
    )
