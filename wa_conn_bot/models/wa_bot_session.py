# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class WaBotSession(models.Model):
    _name = 'wa.bot.session'
    _description = 'WhatsApp Bot Session'
    _order = 'last_activity desc'

    # Basic Info
    name = fields.Char(string='Session', compute='_compute_name', store=True)
    bot_id = fields.Many2one('wa.bot', string='Bot', required=True, ondelete='cascade')
    channel_id = fields.Many2one('discuss.channel', string='Channel', required=True, index=True, ondelete='cascade',
                                 help='WhatsApp channel for this session')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, index=True,
                                 help='Contact partner for this session')
    phone = fields.Char(string='Phone', related='partner_id.mobile', store=True, readonly=True)
    contact_name = fields.Char(string='Contact Name', related='partner_id.name', store=True, readonly=True)
    
    # WhatsApp Account
    wa_account_id = fields.Many2one('wa.account', string='WhatsApp Account', related='channel_id.wa_account_id',
                                    store=True, readonly=True)
    
    # State
    state = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('closed', 'Closed'),
    ], string='State', default='active', required=True, index=True)
    
    # Timing
    start_time = fields.Datetime(string='Started', default=fields.Datetime.now, required=True)
    last_activity = fields.Datetime(string='Last Activity', default=fields.Datetime.now, required=True)
    end_time = fields.Datetime(string='Ended')
    
    # Session Data
    variables = fields.Json(string='Variables', default={},
                           help='Session variables stored as key-value pairs')
    current_flow_step_id = fields.Many2one('wa.bot.flow', string='Current Flow Step')
    waiting_for_step_id = fields.Many2one('wa.bot.flow', string='Waiting For Step',
                                          help='Flow step waiting for user input')
    
    # Statistics
    message_count = fields.Integer(string='Messages', default=0)
    
    # Display
    color = fields.Integer(string='Color Index')

    @api.depends('phone', 'bot_id.name')
    def _compute_name(self):
        for rec in self:
            rec.name = f'{rec.bot_id.name} - {rec.phone}'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure variables is always a dict"""
        for vals in vals_list:
            if 'variables' not in vals or not vals.get('variables'):
                vals['variables'] = {}
        return super().create(vals_list)

    def is_expired(self):
        """Check if session has expired due to inactivity
        
        Returns:
            bool: True if expired
        """
        self.ensure_one()
        
        if self.state != 'active':
            return True
        
        timeout_minutes = self.bot_id.session_timeout or 30
        timeout_delta = timedelta(minutes=timeout_minutes)
        expiry_time = self.last_activity + timeout_delta
        
        return datetime.now() > expiry_time

    def action_expire(self):
        """Mark session as expired"""
        for rec in self:
            if rec.state == 'active':
                rec.write({
                    'state': 'expired',
                    'end_time': fields.Datetime.now(),
                })
                
                # Send timeout message if configured
                if rec.bot_id.session_timeout_message:
                    rec.send_message(rec.bot_id.session_timeout_message)

    def action_close(self):
        """Close session manually"""
        for rec in self:
            rec.write({
                'state': 'closed',
                'end_time': fields.Datetime.now(),
            })

    def action_reopen(self):
        """Reopen expired/closed session"""
        for rec in self:
            rec.write({
                'state': 'active',
                'last_activity': fields.Datetime.now(),
                'end_time': False,
            })

    def get_variable(self, key, default=None):
        """Get session variable
        
        Args:
            key: Variable name
            default: Default value if not found
            
        Returns:
            Variable value or default
        """
        self.ensure_one()
        variables = self.variables or {}
        if not isinstance(variables, dict):
            variables = {}
        return variables.get(key, default)

    def set_variable(self, key, value):
        """Set session variable
        
        Args:
            key: Variable name
            value: Variable value
        """
        self.ensure_one()
        variables = self.variables or {}
        if not isinstance(variables, dict):
            variables = {}
        variables[key] = value
        self.variables = variables

    def set_waiting_for(self, flow_step_id):
        """Set flow step waiting for user input
        
        Args:
            flow_step_id: wa.bot.flow record ID
        """
        self.ensure_one()
        self.waiting_for_step_id = flow_step_id

    def clear_waiting(self):
        """Clear waiting state"""
        self.ensure_one()
        self.waiting_for_step_id = False

    def send_message(self, message):
        """Send message to user through WhatsApp channel
        
        Args:
            message: Message text to send
            
        Returns:
            bool: Success
        """
        self.ensure_one()
        
        try:
            if not self.channel_id:
                _logger.error(f'No channel for session {self.id}')
                return False
            
            # Post message to channel (will be sent via wa_conn)
            self.channel_id.with_context(wa_skip_receive=True).sudo().message_post(
                body=message,
                message_type='whatsapp',
                subtype_xmlid="mail.mt_comment",
                author_id=2,  # OdooBot
            )
            
            return True
            
        except Exception as e:
            _logger.error(f'Error sending message: {str(e)}', exc_info=True)
            return False

    def process_message(self, message, dto=None):
        """Process incoming message in this session
        
        Args:
            message: Message text
            dto: Message DTO object with additional data
            
        Returns:
            dict: Processing result
        """
        self.ensure_one()
        
        # Update activity
        self.write({
            'last_activity': fields.Datetime.now(),
            'message_count': self.message_count + 1,
        })
        
        try:
            # Check for commands first
            if message and message.strip().startswith(('/', '#', '!', '@')):
                parts = message.strip().split()
                cmd_text = parts[0]
                cmd_args = parts[1:] if len(parts) > 1 else []
                
                # Search for matching command
                command = self.env['wa.bot.command'].sudo().search([
                    ('bot_id', '=', self.bot_id.id),
                    ('command', '=', cmd_text),
                    ('active', '=', True),
                ], limit=1)
                
                if command:
                    result = command.execute(self, message, cmd_args, dto=dto)
                    
                    return {'status': 'ok', 'command': cmd_text, 'result': result}
            
            # Process through flow if waiting for input
            if self.waiting_for_step_id:
                flow_step = self.waiting_for_step_id
                result = flow_step.process_input(self, message)
                return {'status': 'ok', 'flow': True, 'result': result}
            
            # No specific handler - use default response if configured
            # TODO: Implement default responses
            return {'status': 'ok', 'handled': False}
            
        except Exception as e:
            _logger.error(f'Error processing message: {str(e)}', exc_info=True)
            return {'status': 'error', 'error': str(e)}

    @api.model
    def _cron_expire_sessions(self):
        """Cron job to expire inactive sessions"""
        timeout_minutes_ago = fields.Datetime.now() - timedelta(minutes=60)  # Default 60min if not configured
        
        sessions = self.search([
            ('state', '=', 'active'),
            ('last_activity', '<', timeout_minutes_ago),
        ])
        
        for session in sessions:
            if session.is_expired():
                session.action_expire()
        
        return True

