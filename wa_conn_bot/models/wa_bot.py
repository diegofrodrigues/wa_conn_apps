# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class WaBot(models.Model):
    _name = 'wa.bot'
    _description = 'WhatsApp Bot'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    # Basic Info
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Bot Name', required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    description = fields.Text(string='Description')
    
    # Initialization Settings
    init_mode = fields.Selection([
        ('auto', 'Automatic - On First Message'),
        ('command', 'Command - Requires Custom Command'),
        ('timeout', 'Timeout - After Session Expires')
    ], string='Initialization Mode', default='auto', required=True, tracking=True,
       help='How the bot session should be initialized:\n'
            '• Automatic: Start session on first message from contact\n'
            '• Command: Require specific command to start (e.g., #init, /start)\n'
            '• Timeout: Restart session after timeout expires')
    
    init_command = fields.Char(
        string='Init Command',
        help='Custom command to initialize bot session (e.g., #init, /start, !begin)',
        default='#init'
    )
    
    # Session Settings
    session_timeout = fields.Integer(
        string='Session Timeout (minutes)',
        default=30,
        required=True,
        help='Time in minutes before session expires due to inactivity'
    )
    
    session_timeout_message = fields.Text(
        string='Timeout Message',
        default='Your session has expired due to inactivity. Send any message to start a new session.',
        help='Message sent when session expires'
    )
    
    # Greeting Settings
    greeting_enabled = fields.Boolean(string='Enable Greeting', default=True, tracking=True)
    greeting_message = fields.Text(
        string='Greeting Message',
        default='Hello! 👋 Welcome to our WhatsApp Bot.\nHow can I help you today?',
        help='First message sent when session starts'
    )
    
    # Flow Settings
    flow_ids = fields.One2many('wa.bot.flow', 'bot_id', string='Flow Steps')
    flow_count = fields.Integer(string='# Flow Steps', compute='_compute_flow_count')
    
    # Commands
    command_ids = fields.One2many('wa.bot.command', 'bot_id', string='Custom Commands')
    command_count = fields.Integer(string='# Commands', compute='_compute_command_count')
    
    # Sessions
    session_ids = fields.One2many('wa.bot.session', 'bot_id', string='Sessions')
    active_session_count = fields.Integer(
        string='# Active Sessions', 
        compute='_compute_session_count',
        search='_search_active_session_count'
    )
    
    # Statistics
    total_messages = fields.Integer(string='Total Messages', compute='_compute_statistics', store=True)
    total_sessions = fields.Integer(string='Total Sessions', compute='_compute_statistics', store=True)
    
    # Colors for UI
    color = fields.Integer(string='Color Index')

    # user_id = fields.Many2one('res.users', string='Bot User', readonly=True, help='Usuário associado ao bot para ações automáticas')

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         bot_name = vals.get('name')
    #         if bot_name:
    #             login = f"{bot_name.lower().replace(' ','.')}@wa.bot"
    #             user_vals = {
    #                 'name': bot_name,
    #                 'login': login,
    #                 'active': True,
    #                 'share': True,
    #                 'password': '!bot_no_login!',
    #                 'company_id': self.env.company.id,
    #                 'notification_type': 'email',
    #             }
    #             user = self.env['res.users'].sudo().create(user_vals)
    #             vals['user_id'] = user.id
    #     return super(WaBot, self).create(vals_list)
    
    @api.depends('flow_ids')
    def _compute_flow_count(self):
        for rec in self:
            rec.flow_count = len(rec.flow_ids)

    @api.depends('command_ids')
    def _compute_command_count(self):
        for rec in self:
            rec.command_count = len(rec.command_ids)

    @api.depends('session_ids', 'session_ids.state')
    def _compute_session_count(self):
        for rec in self:
            rec.active_session_count = len(rec.session_ids.filtered(lambda s: s.state == 'active'))

    def _search_active_session_count(self, operator, value):
        """Custom search method for active_session_count"""
        # Get all bots with their active session count
        self._cr.execute("""
            SELECT bot_id, COUNT(*) as count
            FROM wa_bot_session
            WHERE state = 'active'
            GROUP BY bot_id
        """)
        results = {row[0]: row[1] for row in self._cr.fetchall()}
        
        # Filter based on operator and value
        if operator == '>':
            bot_ids = [bot_id for bot_id, count in results.items() if count > value]
        elif operator == '>=':
            bot_ids = [bot_id for bot_id, count in results.items() if count >= value]
        elif operator == '<':
            bot_ids = [bot_id for bot_id, count in results.items() if count < value]
        elif operator == '<=':
            bot_ids = [bot_id for bot_id, count in results.items() if count <= value]
        elif operator == '=':
            bot_ids = [bot_id for bot_id, count in results.items() if count == value]
        elif operator == '!=':
            bot_ids = [bot_id for bot_id, count in results.items() if count != value]
        else:
            bot_ids = []
        
        # Also include bots with 0 sessions if the condition matches
        if operator in ['<', '<=', '!='] and value > 0:
            all_bot_ids = self.search([]).ids
            bot_ids.extend([bid for bid in all_bot_ids if bid not in results])
        elif operator in ['='] and value == 0:
            all_bot_ids = self.search([]).ids
            bot_ids.extend([bid for bid in all_bot_ids if bid not in results])
        
        return [('id', 'in', bot_ids)]

    @api.depends('session_ids')
    def _compute_statistics(self):
        for rec in self:
            rec.total_sessions = len(rec.session_ids)
            rec.total_messages = sum(rec.session_ids.mapped('message_count'))

    @api.constrains('session_timeout')
    def _check_session_timeout(self):
        for rec in self:
            if rec.session_timeout <= 0:
                raise ValidationError(_('Session timeout must be greater than 0 minutes.'))

    @api.constrains('init_mode', 'init_command')
    def _check_init_command(self):
        for rec in self:
            if rec.init_mode == 'command' and not rec.init_command:
                raise ValidationError(_('Init command is required when initialization mode is "Command".'))

    def action_view_flows(self):
        """Open flow builder"""
        self.ensure_one()
        return {
            'name': _('Flow Builder - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'wa.bot.flow',
            'view_mode': 'list,form',
            'domain': [('bot_id', '=', self.id)],
            'context': {
                'default_bot_id': self.id,
            },
        }

    def action_view_commands(self):
        """Open commands list"""
        self.ensure_one()
        return {
            'name': _('Custom Commands - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'wa.bot.command',
            'view_mode': 'list,form',
            'domain': [('bot_id', '=', self.id)],
            'context': {
                'default_bot_id': self.id,
            },
        }

    def action_view_sessions(self):
        """Open active sessions"""
        self.ensure_one()
        return {
            'name': _('Active Sessions - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'wa.bot.session',
            'view_mode': 'list,form',
            'domain': [('bot_id', '=', self.id), ('state', '=', 'active')],
            'context': {
                'default_bot_id': self.id,
            },
        }

    def action_test_greeting(self):
        """Test greeting message"""
        self.ensure_one()
        if not self.greeting_enabled:
            raise UserError(_('Greeting is not enabled for this bot.'))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Greeting Message'),
                'message': self.greeting_message or _('No greeting message configured.'),
                'type': 'info',
                'sticky': False,
            }
        }

    def _create_session(self, channel, partner):
        """Create a new bot session
        
        Args:
            channel: discuss.channel record
            partner: res.partner record
            
        Returns:
            wa.bot.session: New session record
        """
        self.ensure_one()
        
        session = self.env['wa.bot.session'].sudo().create({
            'bot_id': self.id,
            'channel_id': channel.id,
            'partner_id': partner.id,
            'state': 'active',
        })
        
        # Send greeting if enabled
        if self.greeting_enabled and self.greeting_message:
            try:
                # Post greeting message to channel
                channel.with_context(wa_skip_receive=True).message_post(
                    body=self.greeting_message,
                    message_type='whatsapp',
                    subtype_xmlid="mail.mt_comment",
                    author_id=2,  # OdooBot
                )
            except Exception as e:
                _logger.warning(f"Failed to send greeting message: {e}")
        
        # Start flow if configured
        if self.flow_ids:
            first_step = self.flow_ids.sorted('sequence')[0]
            if first_step:
                try:
                    self._execute_flow_chain(session, first_step)
                except Exception as e:
                    _logger.error(f"Failed to execute flow: {e}", exc_info=True)
        
        return session
    
    def _execute_flow_chain(self, session, current_step, max_steps=50):
        """Execute flow steps in chain until waiting or end
        
        Args:
            session: wa.bot.session record
            current_step: Current flow step to execute
            max_steps: Maximum steps to execute (prevent infinite loops)
        """
        executed_count = 0
        
        while current_step and executed_count < max_steps:
            # Execute current step
            result = current_step.execute(session)
            
            if not result.get('ok'):
                _logger.error(f"Flow step {current_step.name} failed: {result.get('error')}")
                break
            
            # If waiting for input, stop chain
            if result.get('waiting'):
                _logger.info(f"Flow waiting for input at step: {current_step.name}")
                break
            
            # Move to next step
            next_step = result.get('next_step')
            if not next_step:
                _logger.info(f"Flow completed at step: {current_step.name}")
                break
            
            current_step = next_step
            executed_count += 1
        
        if executed_count >= max_steps:
            _logger.warning(f"Flow chain exceeded max steps ({max_steps}). Possible infinite loop.")
        
        return True

    def get_or_create_session(self, phone, wa_account_id):
        """Get or create bot session for a phone number
        
        Args:
            phone (str): Phone number
            wa_account_id (int): WhatsApp account ID
            
        Returns:
            wa.bot.session: Active session record
        """
        self.ensure_one()
        
        # Search for active session
        session = self.env['wa.bot.session'].search([
            ('bot_id', '=', self.id),
            ('phone', '=', phone),
            ('wa_account_id', '=', wa_account_id),
            ('state', '=', 'active')
        ], limit=1)
        
        # Check if session expired
        if session and session.is_expired():
            session.action_expire()
            session = False
        
        # Create new session if needed
        if not session:
            session = self.env['wa.bot.session'].create({
                'bot_id': self.id,
                'phone': phone,
                'wa_account_id': wa_account_id,
                'state': 'active',
            })
            
            # Send greeting if enabled
            if self.greeting_enabled and self.greeting_message:
                session.send_message(self.greeting_message)
        
        return session

    def process_message(self, phone, message, wa_account_id, message_data=None):
        """Process incoming message through bot
        
        Args:
            phone (str): Sender phone number
            message (str): Message text
            wa_account_id (int): WhatsApp account ID
            message_data (dict): Additional message data
            
        Returns:
            dict: Processing result
        """
        self.ensure_one()
        
        try:
            # Check initialization mode
            if self.init_mode == 'command':
                if message.strip() == self.init_command:
                    # Initialize new session
                    session = self.get_or_create_session(phone, wa_account_id)
                    return {
                        'ok': True,
                        'session_id': session.id,
                        'message': 'Session initialized'
                    }
                else:
                    # Check for existing session
                    session = self.env['wa.bot.session'].search([
                        ('bot_id', '=', self.id),
                        ('phone', '=', phone),
                        ('wa_account_id', '=', wa_account_id),
                        ('state', '=', 'active')
                    ], limit=1)
                    
                    if not session or session.is_expired():
                        # No active session, send init command hint
                        return {
                            'ok': False,
                            'error': 'no_session',
                            'message': f'Please send {self.init_command} to start a session'
                        }
            
            # Get or create session (auto/timeout mode)
            session = self.get_or_create_session(phone, wa_account_id)
            
            # Process message through session
            result = session.process_message(message, message_data)
            
            return result
            
        except Exception as e:
            _logger.error(f'Error processing message in bot {self.name}: {str(e)}', exc_info=True)
            return {
                'ok': False,
                'error': 'processing_failed',
                'message': str(e)
            }
