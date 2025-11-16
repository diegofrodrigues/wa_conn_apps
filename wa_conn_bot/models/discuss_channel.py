# -*- coding: utf-8 -*-
from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class DiscussChannelBot(models.Model):
    """Extend discuss.channel to integrate bot processing"""
    _inherit = 'discuss.channel'

    def wa_post_incoming(self, dto, partner):
        """Override to process through bot before posting message"""
        # First, check if this channel has bot enabled via wa_account
        if self.wa_account_id and self.wa_account_id.bot_enabled and self.wa_account_id.bot_id:
            try:
                # Process message through bot
                bot_handled = self._process_message_through_bot(dto, partner)
                
                # If bot handled the message, we might skip posting or modify the flow
                # For now, we always post the incoming message but let bot respond
                
            except Exception as e:
                _logger.error(f'Error processing message through bot: {e}', exc_info=True)
        
        # Call parent to post the incoming message
        return super().wa_post_incoming(dto, partner)
    
    def _process_message_through_bot(self, dto, partner):
        """Process incoming message through bot system
        
        Args:
            dto: Normalized message DTO
            partner: res.partner who sent the message
            
        Returns:
            bool: True if bot handled the message
        """
        self.ensure_one()
        
        account = self.wa_account_id
        bot = account.bot_id
        
        if not bot or not account.bot_enabled:
            return False
        
        # Get message text
        message_text = getattr(dto, 'message', '') or ''
        
        # Get or create bot session for this channel
        Session = self.env['wa.bot.session'].sudo()
        session = Session.search([
            ('bot_id', '=', bot.id),
            ('channel_id', '=', self.id),
            ('state', '=', 'active')
        ], limit=1)
        
        # Check if session needs initialization
        if not session:
            # Check initialization mode
            if bot.init_mode == 'command':
                # Requires init command
                if message_text.strip() == bot.init_command:
                    session = bot._create_session(self, partner)
                else:
                    # Message ignored - waiting for init command
                    _logger.info(f'Bot waiting for init command. Received: {message_text[:50]}')
                    return False
            
            elif bot.init_mode == 'auto':
                # Auto-initialize on first message
                session = bot._create_session(self, partner)
            
            elif bot.init_mode == 'timeout':
                # Don't auto-create on timeout mode
                _logger.info(f'Bot in timeout mode - no active session')
                return False
        
        else:
            # Check if session expired
            if session.is_expired():
                session.action_expire()
                
                # Send timeout message if configured
                if bot.session_timeout_message:
                    self._send_bot_message(bot.session_timeout_message)
                
                # Check if should auto-restart
                if bot.init_mode == 'auto':
                    session = bot._create_session(self, partner)
                else:
                    return False
        
        # Process message through session
        if session:
            try:
                result = session.process_message(message_text, dto=dto)
                
                # Send response if provided
                if result.get('status') == 'ok':
                    # Check if command returned text to send
                    if result.get('result') and isinstance(result['result'], dict):
                        response_text = result['result'].get('text')
                        if response_text:
                            self._send_bot_message(response_text)
                
                return True
                
            except Exception as e:
                _logger.error(f'Error in bot session processing: {e}', exc_info=True)
                return False
        
        return False
    
    def _send_bot_message(self, message_text):
        """Send a message from the bot to this channel
        
        Args:
            message_text: Text to send
        """
        self.ensure_one()
        
        try:
            # Post message to channel - will be sent via wa_conn
            self.sudo().message_post(
                body=message_text,
                author_id=2,  # OdooBot
                message_type='whatsapp',
                subtype_xmlid="mail.mt_comment",
            )
        except Exception as e:
            _logger.error(f'Error sending bot message: {e}', exc_info=True)
