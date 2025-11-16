# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class WaBotFlow(models.Model):
    _name = 'wa.bot.flow'
    _description = 'WhatsApp Bot Flow Step'
    _order = 'bot_id, sequence, id'

    # Basic Info
    name = fields.Char(string='Step Name', required=True,
                       help='Name for this flow step')
    bot_id = fields.Many2one('wa.bot', string='Bot', required=True, ondelete='cascade')
    active = fields.Boolean(string='Active', default=True)
    
    # Sequencing
    sequence = fields.Integer(string='Sequence', default=10,
                             help='Order of execution in the flow')
    
    # Step Type
    step_type = fields.Selection([
        ('message', 'Send Message'),
        ('question', 'Ask Question'),
        ('condition', 'Conditional Branch'),
        ('action', 'Execute Action'),
        ('wait', 'Wait for Input'),
    ], string='Step Type', default='message', required=True)
    
    # Message Content
    message = fields.Text(
        string='Message',
        help='Message to send. Available variables:\n'
             '• {contact_name} - Contact name\n'
             '• {phone} - Phone number\n'
             '• {session.variable_name} - Session variable'
    )
    
    # Question Settings
    question_variable = fields.Char(
        string='Store Answer In',
        help='Variable name to store the answer (for question type)'
    )
    
    question_validation = fields.Selection([
        ('none', 'No Validation'),
        ('text', 'Text Only'),
        ('number', 'Number Only'),
        ('email', 'Email Format'),
        ('phone', 'Phone Format'),
        ('custom', 'Custom Python Code'),
    ], string='Answer Validation', default='none')
    
    validation_code = fields.Text(
        string='Validation Code',
        help='Python code for custom validation.\n'
             'Available variables: response, session\n'
             'Set "valid = True/False" and "error_message" if invalid'
    )
    
    validation_error_message = fields.Char(
        string='Validation Error Message',
        default='Invalid input. Please try again.'
    )
    
    # Conditional Settings
    condition_type = fields.Selection([
        ('python', 'Python Expression'),
        ('variable', 'Variable Comparison'),
    ], string='Condition Type', default='python')
    
    condition_code = fields.Text(
        string='Condition Code',
        help='Python code that returns True/False.\n'
             'Available variables: session, message, env'
    )
    
    condition_variable = fields.Char(string='Variable Name')
    condition_operator = fields.Selection([
        ('==', 'Equal'),
        ('!=', 'Not Equal'),
        ('>', 'Greater Than'),
        ('>=', 'Greater or Equal'),
        ('<', 'Less Than'),
        ('<=', 'Less or Equal'),
        ('contains', 'Contains'),
        ('not_contains', 'Does Not Contain'),
    ], string='Operator', default='==')
    condition_value = fields.Char(string='Compare Value')
    
    # Next Steps (for branching)
    next_step_true_id = fields.Many2one('wa.bot.flow', string='Next Step (True)',
                                         domain="[('bot_id', '=', bot_id)]",
                                         help='Next step if condition is true')
    next_step_false_id = fields.Many2one('wa.bot.flow', string='Next Step (False)',
                                          domain="[('bot_id', '=', bot_id)]",
                                          help='Next step if condition is false')
    next_step_id = fields.Many2one('wa.bot.flow', string='Next Step',
                                    domain="[('bot_id', '=', bot_id)]",
                                    help='Next step in flow (for non-conditional steps)')
    
    # Action Settings
    action_code = fields.Text(
        string='Action Code',
        help='Python code to execute as action.\n'
             'Available variables: session, env, bot'
    )
    
    # Wait Settings
    wait_timeout = fields.Integer(
        string='Wait Timeout (seconds)',
        default=300,
        help='Maximum time to wait for user input'
    )
    
    # Delay Settings
    delay = fields.Integer(
        string='Delay (seconds)',
        default=0,
        help='Wait time before executing this step (in seconds)'
    )
    
    # Display
    color = fields.Integer(string='Color Index')
    notes = fields.Text(string='Notes')

    @api.constrains('condition_code')
    def _check_condition_code(self):
        """Validate condition code syntax"""
        for rec in self:
            if rec.step_type == 'condition' and rec.condition_type == 'python':
                if not rec.condition_code:
                    raise ValidationError(_('Condition code is required for conditional steps.'))

    def evaluate_condition(self, session, message=None):
        """Evaluate condition and return True/False
        
        Args:
            session: wa.bot.session record
            message: Message text (optional)
            
        Returns:
            bool: Condition result
        """
        self.ensure_one()
        
        if self.condition_type == 'variable':
            # Simple variable comparison
            var_value = session.get_variable(self.condition_variable)
            compare_value = self.condition_value
            
            # Type conversion
            try:
                if isinstance(var_value, (int, float)):
                    compare_value = float(compare_value)
                elif isinstance(var_value, bool):
                    compare_value = compare_value.lower() in ('true', '1', 'yes')
            except:
                pass
            
            # Comparison
            if self.condition_operator == '==':
                return var_value == compare_value
            elif self.condition_operator == '!=':
                return var_value != compare_value
            elif self.condition_operator == '>':
                return var_value > compare_value
            elif self.condition_operator == '>=':
                return var_value >= compare_value
            elif self.condition_operator == '<':
                return var_value < compare_value
            elif self.condition_operator == '<=':
                return var_value <= compare_value
            elif self.condition_operator == 'contains':
                return str(compare_value) in str(var_value)
            elif self.condition_operator == 'not_contains':
                return str(compare_value) not in str(var_value)
            
        elif self.condition_type == 'python':
            # Python expression evaluation
            safe_globals = {
                '__builtins__': {
                    'True': True,
                    'False': False,
                    'None': None,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'len': len,
                    'isinstance': isinstance,
                },
                'session': session,
                'message': message,
                'env': self.env,
            }
            
            try:
                exec(self.condition_code, safe_globals)
                return safe_globals.get('result', False)
            except Exception as e:
                _logger.error(f'Error evaluating condition: {str(e)}')
                return False
        
        return False

    def validate_answer(self, response, session):
        """Validate response for question type
        
        Args:
            response: User's response
            session: wa.bot.session record
        
        Returns:
            tuple: (valid, error_message)
        """
        self.ensure_one()
        
        if self.question_validation == 'none':
            return True, None
        
        if self.question_validation == 'text':
            if not response or not response.strip():
                return False, self.validation_error_message or 'Please provide a text answer.'
            return True, None
        
        elif self.question_validation == 'number':
            try:
                float(response)
                return True, None
            except:
                return False, self.validation_error_message or 'Please provide a valid number.'
        
        elif self.question_validation == 'email':
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if re.match(email_pattern, response):
                return True, None
            return False, self.validation_error_message or 'Please provide a valid email address.'
        
        elif self.question_validation == 'phone':
            import re
            # Simple phone validation (digits only, 8-15 chars)
            phone_clean = re.sub(r'[^\d]', '', response)
            if 8 <= len(phone_clean) <= 15:
                return True, None
            return False, self.validation_error_message or 'Please provide a valid phone number.'
        
        elif self.question_validation == 'custom':
            if not self.validation_code:
                return True, None
            
            safe_globals = {
                '__builtins__': {
                    'True': True,
                    'False': False,
                    'None': None,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'len': len,
                    'isinstance': isinstance,
                },
                'response': response,
                'session': session,
            }
            
            try:
                exec(self.validation_code, safe_globals)
                valid = safe_globals.get('valid', True)
                error_msg = safe_globals.get('error_message', self.validation_error_message)
                return valid, error_msg if not valid else None
            except Exception as e:
                _logger.error(f'Error in custom validation: {str(e)}')
                return False, 'Validation error. Please try again.'
        
        return True, None

    def execute(self, session, message=None):
        """Execute this flow step
        
        Args:
            session: wa.bot.session record
            message: Message text (optional)
            
        Returns:
            dict: Execution result with next_step
        """
        self.ensure_one()
        
        if not self.active:
            return {'ok': False, 'error': 'step_inactive'}
        
        # Apply delay if configured
        if self.delay > 0:
            import time
            time.sleep(self.delay)
        
        result = {'ok': True}
        
        try:
            if self.step_type == 'message':
                # Send message
                msg = self._format_message(self.message, session)
                session.send_message(msg)
                result['next_step'] = self.next_step_id
                
            elif self.step_type == 'question':
                # Ask question and wait for answer
                msg = self._format_message(self.message, session)
                session.send_message(msg)
                session.set_waiting_for(self.id)
                result['waiting'] = True
                
            elif self.step_type == 'condition':
                # Evaluate condition and branch
                condition_result = self.evaluate_condition(session, message)
                if condition_result:
                    result['next_step'] = self.next_step_true_id
                else:
                    result['next_step'] = self.next_step_false_id
                    
            elif self.step_type == 'action':
                # Execute action code
                safe_globals = {
                    '__builtins__': {
                        'True': True,
                        'False': False,
                        'None': None,
                        'str': str,
                        'int': int,
                        'float': float,
                        'bool': bool,
                        'list': list,
                        'dict': dict,
                    },
                    'session': session,
                    'env': self.env,
                    'bot': session.bot_id,
                    'json': json,
                }
                exec(self.action_code, safe_globals)
                result['next_step'] = self.next_step_id
                
            elif self.step_type == 'wait':
                # Wait for input
                session.set_waiting_for(self.id)
                result['waiting'] = True
                
        except Exception as e:
            _logger.error(f'Error executing flow step {self.name}: {str(e)}', exc_info=True)
            result = {'ok': False, 'error': str(e)}
        
        return result

    def _format_message(self, message, session):
        """Format message replacing variables
        
        Args:
            message: Message template
            session: wa.bot.session record
            
        Returns:
            str: Formatted message
        """
        if not message:
            return ''
        
        # Replace session variables
        formatted = message
        variables = session.variables or {}
        if isinstance(variables, dict):
            for key, value in variables.items():
                formatted = formatted.replace(f'{{{key}}}', str(value))
        
        # Replace built-in variables
        formatted = formatted.replace('{phone}', session.phone or '')
        formatted = formatted.replace('{contact_name}', session.contact_name or session.phone or '')
        
        return formatted

    def process_input(self, session, message):
        """Process user input for this step (when waiting for answer)
        
        Args:
            session: wa.bot.session record
            message: User's message
            
        Returns:
            dict: Processing result
        """
        self.ensure_one()
        
        if self.step_type == 'question':
            # Validate response
            valid, error_msg = self.validate_answer(message, session)
            
            if not valid:
                # Send error and keep waiting
                session.send_message(error_msg)
                return {'ok': False, 'error': 'validation_failed', 'message': error_msg}
            
            # Store response in variable
            if self.question_variable:
                session.set_variable(self.question_variable, message)
            
            # Clear waiting state
            session.clear_waiting()
            
            # Move to next step and execute chain
            if self.next_step_id:
                # Execute the chain starting from next step
                return session.bot_id._execute_flow_chain(session, self.next_step_id)
            else:
                return {'ok': True, 'completed': True}
        
        elif self.step_type == 'wait':
            # Clear waiting and move to next step
            session.clear_waiting()
            
            if self.next_step_id:
                # Execute the chain starting from next step
                return session.bot_id._execute_flow_chain(session, self.next_step_id)
            else:
                return {'ok': True, 'completed': True}
        
        return {'ok': True}
