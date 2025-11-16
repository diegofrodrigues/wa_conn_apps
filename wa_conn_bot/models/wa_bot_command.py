# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class WaBotCommand(models.Model):
    _name = 'wa.bot.command'
    _description = 'WhatsApp Bot Custom Command'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    # Basic Info
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Command Name', required=True, tracking=True,
                       help='Descriptive name for this command')
    command = fields.Char(string='Command Shortcut', required=True, tracking=True,
                          help='Shortcut used to invoke this command (e.g., /help, #status, !info)')
    description = fields.Text(string='Description',
                             help='What this command does')
    
    # Bot Relation
    bot_id = fields.Many2one('wa.bot', string='Bot', required=True, ondelete='cascade',
                            tracking=True)
    
    # Activation
    active = fields.Boolean(string='Active', default=True, tracking=True)
    
    # Execution
    python_code = fields.Text(
        string='Python Code',
        required=True,
        help='Python code to execute when command is invoked.\n\n'
             'Available variables:\n'
             '• session: Current bot session (wa.bot.session)\n'
             '• message: Full message text received\n'
             '• args: Command arguments (list of strings)\n'
             '• phone: Sender phone number\n'
             '• env: Odoo environment\n'
             '• bot: Bot instance\n'
             '• _: Translation function\n'
             '• json: JSON module\n'
             '• datetime, timedelta: Date/time modules\n\n'
             'Full Python access - can use imports, loops, etc.\n\n'
             'Set "result" variable with response:\n'
             '• result = "Simple text response"\n'
             '• result = {"text": "Response", "data": {...}}\n'
             '• result = {"ok": False, "error": "Error message"}',
        default="""# Example: Sales report for last 4 months
from datetime import datetime, timedelta

# Calculate date 4 months ago
date_from = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')

# Search confirmed sales
orders = env['sale.order'].sudo().search([
    ('date_order', '>=', date_from),
    ('state', 'in', ['sale', 'done'])
])

# Group by partner
sales = {}
for order in orders:
    partner = order.partner_id.name
    if partner not in sales:
        sales[partner] = {'count': 0, 'total': 0.0}
    sales[partner]['count'] += 1
    sales[partner]['total'] += order.amount_total

# Format result
if not sales:
    result = "No sales in last 4 months"
else:
    lines = ["Sales (last 4 months):"]
    for partner, data in sales.items():
        lines.append(f"• {partner}: {data['count']} orders, ${data['total']:.2f}")
    result = "\\n".join(lines)
"""
    )
    
    # Testing
    test_input = fields.Char(
        string='Test Input',
        help='Sample message to test this command (e.g., "/help" or "/search keyword")',
        default='/help'
    )
    
    test_output = fields.Text(
        string='Test Output',
        readonly=True,
        help='Result from last test execution'
    )
    
    # Display
    sequence = fields.Integer(string='Sequence', default=10)
    color = fields.Integer(string='Color Index')
    
    # Statistics
    execution_count = fields.Integer(string='Executions', default=0, readonly=True,
                                     help='Number of times this command was executed')
    last_execution = fields.Datetime(string='Last Execution', readonly=True)

    _sql_constraints = [
        ('command_bot_unique', 'UNIQUE(bot_id, command)',
         'Command shortcut must be unique per bot!')
    ]

    @api.constrains('command')
    def _check_command_format(self):
        """Validate command format"""
        for rec in self:
            if not rec.command:
                continue
            
            # Remove spaces
            cmd = rec.command.strip()
            if ' ' in cmd:
                raise ValidationError(_('Command shortcut cannot contain spaces. Use /command or #command format.'))
            
            # Should start with special character
            if not cmd[0] in ['/', '#', '!', '@', '$', '%', '&', '*']:
                raise ValidationError(_('Command should start with a special character like /, #, !, etc.'))

    def action_test_command(self):
        """Test command execution"""
        self.ensure_one()
        
        if not self.python_code:
            raise UserError(_('Please provide Python code to test.'))
        
        # Parse test input to extract command and arguments
        test_msg = (self.test_input or '').strip()
        if not test_msg:
            test_msg = self.command
        
        parts = test_msg.split()
        cmd = parts[0] if parts else self.command
        args = parts[1:] if len(parts) > 1 else []
        
        # Create mock session for testing
        mock_session = type('MockSession', (), {
            'bot_id': self.bot_id,
            'phone': '+5511999999999',
            'state': 'active',
            'send_message': lambda msg: _logger.info(f'Mock send: {msg}'),
        })()
        
        # Full Python execution environment - NO RESTRICTIONS
        exec_globals = {
            '__builtins__': __builtins__,  # Full Python builtins including import
            'session': mock_session,
            'message': test_msg,
            'args': args,
            'phone': '+5511999999999',
            'env': self.env,
            'bot': self.bot_id,
            'json': json,
            '_': _,
            'datetime': __import__('datetime'),
            'timedelta': __import__('datetime').timedelta,
        }
        
        try:
            # Execute code with full Python access
            exec(self.python_code, exec_globals)
            
            # Get result
            if 'result' in exec_globals:
                result = exec_globals['result']
                
                # Format output
                if isinstance(result, dict):
                    output = json.dumps(result, indent=2, ensure_ascii=False)
                elif isinstance(result, (list, tuple)):
                    output = json.dumps(result, indent=2, ensure_ascii=False)
                else:
                    output = str(result)
            else:
                output = 'Code executed successfully but no result variable was set.\nSet result = "response" or result = {...} in your code.'
            
            self.test_output = output
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Test Successful'),
                    'message': _('Command executed successfully. Check Test Output field for results.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.test_output = f"ERROR: {str(e)}\n\n{error_detail}"
            
            raise UserError(_('Test failed: %s\n\nSee Test Output for details.') % str(e))

    def execute(self, session, message, args=None, dto=None):
        """Execute command in context of a session
        
        Args:
            session: wa.bot.session record
            message: Full message text
            args: List of command arguments
            dto: Message DTO object with additional data
            
        Returns:
            dict: Execution result
        """
        self.ensure_one()
        
        if not self.active:
            return {
                'ok': False,
                'error': 'command_disabled',
                'message': 'This command is currently disabled'
            }
        
        # Full Python execution environment - NO RESTRICTIONS
        exec_globals = {
            '__builtins__': __builtins__,  # Full Python builtins including import
            'session': session,
            'message': message,
            'args': args or [],
            'dto': dto,
            'phone': session.phone,
            'env': self.env,
            'bot': session.bot_id,
            'json': json,
            '_': _,
            'datetime': __import__('datetime'),
            'timedelta': __import__('datetime').timedelta,
        }
        
        try:
            # Execute code with full Python access
            exec(self.python_code, exec_globals)
            
            # Update statistics
            self.sudo().write({
                'execution_count': self.execution_count + 1,
                'last_execution': fields.Datetime.now(),
            })
            
            # Get result
            if 'result' in exec_globals:
                result = exec_globals['result']
                
                # Normalize result format
                if isinstance(result, str):
                    return {'ok': True, 'text': result}
                elif isinstance(result, dict):
                    if 'ok' not in result:
                        result['ok'] = True
                    return result
                else:
                    return {'ok': True, 'result': result}
            else:
                return {
                    'ok': True,
                    'message': 'Command executed successfully'
                }
                
        except Exception as e:
            _logger.error(f'Error executing command {self.name}: {str(e)}', exc_info=True)
            return {
                'ok': False,
                'error': 'execution_failed',
                'message': str(e)
            }
