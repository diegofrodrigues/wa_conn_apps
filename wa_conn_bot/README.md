# WA Conn Bot - WhatsApp Bot Module

## Overview

WhatsApp Bot module for Odoo 18.0 that provides automated message handling with custom flows and commands.

## Features

### 1. Bot Configuration
- **Initialization Modes**:
  - Automatic: Start on first message
  - Command: Require custom command (e.g., #init)
  - Timeout: Restart after session expires
- **Session Management**: Configurable timeout with custom messages
- **Greeting Messages**: Welcome messages when session starts

### 2. Flow Builder
Build conversation flows with different step types:
- **Message**: Send text messages
- **Question**: Ask questions and validate answers
- **Condition**: Branch based on conditions
- **Action**: Execute custom Python code
- **Wait**: Wait for user input

### 3. Custom Commands
Create slash commands like `/help`, `#status`, `!info`:
- Custom Python code execution
- Access to session, environment, and bot
- Arguments support
- Test functionality

### 4. Session Management
- Track active sessions per phone number
- Session variables storage
- Activity tracking
- Message counting

### 5. Integration with wa_account
- Enable/disable bot per account
- Automatic message processing
- Bot assignment

## Installation

1. Copy module to `custom_addons` directory
2. Update apps list in Odoo
3. Install "WA Conn Bot" module

## Usage

### Creating a Bot

1. Go to **WA Bot > Bots**
2. Click **Create**
3. Configure:
   - Name and description
   - Initialization mode
   - Session timeout
   - Greeting message

### Adding Commands

1. Open bot record
2. Go to **Commands** tab
3. Click **Add a line** or **Create**
4. Configure:
   - Name and command shortcut
   - Python code
5. Test with **Test Command** button

### Building Flows

1. Open bot record
2. Go to **Flow Builder** tab
3. Add steps in sequence
4. Configure step types and messages
5. Link steps with **Next Step** fields

### Enabling Bot on Account

1. Go to wa_account record
2. Enable **Bot Enabled**
3. Select **Active Bot**
4. Bot will process incoming messages automatically

## Python Code Examples

### Command Example
```python
# Show help
result = {
    'ok': True,
    'text': f"Available commands:\n"
            f"• /help - Show this help\n"
            f"• /status - Check status"
}
```

### Search Command
```python
# Search partners
if args:
    keyword = args[0]
    partners = env['res.partner'].search([('name', 'ilike', keyword)])
    result = f"Found {len(partners)} partners matching '{keyword}'"
else:
    result = "Usage: /search <keyword>"
```

### Session Variables
```python
# Store and retrieve variables
session.set_variable('user_name', 'John')
name = session.get_variable('user_name')
result = f"Hello {name}!"
```

## Flow Builder Examples

### Simple Welcome Flow
1. **Step 1 (Message)**: "Welcome! What's your name?"
2. **Step 2 (Question)**: Store in `user_name`, validate as text
3. **Step 3 (Message)**: "Nice to meet you, {user_name}!"

### Conditional Flow
1. **Step 1 (Question)**: "How old are you?" → Store in `age`
2. **Step 2 (Condition)**: Check if `age > 18`
3. **Step 3a (Message)**: "You are an adult" (if true)
4. **Step 3b (Message)**: "You are a minor" (if false)

## Available Variables in Commands

- `session`: Current bot session
- `message`: Full message text
- `args`: Command arguments (list)
- `phone`: Sender phone number
- `env`: Odoo environment
- `bot`: Bot instance
- `json`: JSON module
- `_`: Translation function

## Available Variables in Flows

- `{contact_name}`: Contact name
- `{phone}`: Phone number
- `{variable_name}`: Any session variable

## Architecture

```
wa_conn_bot/
├── models/
│   ├── wa_bot.py              # Main bot model
│   ├── wa_bot_command.py      # Custom commands
│   ├── wa_bot_flow.py         # Flow builder
│   ├── wa_bot_session.py      # Session management
│   └── wa_account.py          # wa_account extension
├── views/
│   ├── wa_bot_views.xml       # Bot views
│   ├── wa_bot_command_views.xml
│   ├── wa_bot_flow_views.xml
│   ├── wa_bot_session_views.xml
│   └── wa_conn_bot_menus.xml
└── security/
    └── ir.model.access.csv
```

## Author

**Diego Ferreira Rodrigues**
- Email: diego@bitconn.com.br
- Website: https://bitconn.com.br
- GitHub: https://github.com/diegofrodrigues

## License

LGPL-3

## Support

If this module helped you, consider supporting the project! 🍺

PIX: `00020126810014br.gov.bcb.pix013655f22863-4cea-41e9-904c-df3ce0b241ef0219wa conn odoo module5204000053039865802BR5924Diego Ferreira Rodrigues6009Sao Paulo62290525REC68545B90764819659464106304D86E`
