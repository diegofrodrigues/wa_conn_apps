# WhatsApp Connector - Evolution API Plugin

Plugin module that adds Evolution API provider support to the WhatsApp Connector (wa_conn) module.

## Description

This plugin extends the `wa_conn` base module with Evolution API integration. It provides complete WhatsApp Business API functionality through the Evolution API platform.

## Features

- Complete Evolution API integration
- Send text and media messages (images, videos, audio, documents)
- Receive webhooks with automatic normalization
- Instance lifecycle management (create, delete, restart, connect, disconnect)
- QR Code generation for device pairing
- Connection status monitoring
- Profile image fetching
- Support for multiple Evolution API versions

## Dependencies

- `wa_conn` (base module) - Required

## Installation

1. Install the base `wa_conn` module first
2. Install this plugin module
3. Restart Odoo server
4. The Evolution API provider will automatically appear in the provider selection

## Configuration

After installation, you can configure WhatsApp accounts with Evolution API:

1. Go to **WhatsApp Connector > Accounts**
2. Create a new account
3. Select **Evolution API** as the provider
4. Fill in the required fields:
   - API URL (e.g., `https://your-evolution-api.com`)
   - API Key
   - Instance Name
   - Webhook configuration (if needed)
5. Click **Create Instance** button
6. Click **Connect** to get the QR code
7. Scan the QR code with your WhatsApp mobile app

## Technical Details

### Model

This module adds the `wa.provider.evolution` model that inherits from `wa.provider.base`. The provider is automatically discovered by the base module through Odoo's model registry.

### Auto-Discovery

The plugin uses a naming convention for auto-discovery:
- Model name: `wa.provider.<provider_name>`
- Example: `wa.provider.evolution`

The base `wa_conn` module will automatically detect this model and add "Evolution API" to the available providers list.

### API Methods Implemented

All abstract methods from `wa.provider.base` are implemented:

- `normalize_inbound()` - Normalize webhook payloads
- `inbound_handle()` - Process incoming messages
- `send_text()` - Send text messages
- `send_media()` - Send media files
- `create_instance()` - Create Evolution instance
- `delete_instance()` - Delete Evolution instance
- `check_status()` - Check connection status
- `connect()` - Connect and get QR code
- `restart()` - Restart instance
- `disconnect()` - Disconnect/logout
- `get_profile_image()` - Fetch contact profile image

## Evolution API Compatibility

This plugin supports multiple versions of Evolution API:
- v1.x
- v2.x (latest)

The code includes fallback mechanisms for different endpoint patterns across versions.

## Webhook Events

Supported Evolution API webhook events:
- `messages.upsert` - New incoming message
- Other events are logged but not processed

## Media Types

Supported media types:
- **Images**: JPG, PNG, GIF, WebP, BMP
- **Videos**: MP4, AVI, MOV, WMV, FLV, MKV, WebM
- **Audio**: MP3, OGG, WAV, AAC, FLAC, M4A, Opus
- **Documents**: PDF, DOC, DOCX, XLS, XLSX, TXT, ZIP, etc.

## Troubleshooting

### Provider not appearing in selection

- Make sure the base `wa_conn` module is installed
- Restart the Odoo server
- Check that `wa.provider.evolution` model is registered in **Settings > Technical > Models**

### Connection errors

- Verify the API URL is correct and accessible
- Check that the API Key is valid
- Ensure the instance name doesn't already exist
- Check Evolution API server logs

### Webhook not receiving messages

- Verify webhook URL is accessible from the internet
- Check webhook key configuration
- Ensure the webhook events are properly configured in the account
- Check Evolution API webhook logs

## Development

### File Structure

```
wa_conn_evolution/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── wa_provider_evolution.py
├── security/
│   └── ir.model.access.csv
└── README.md
```

### Extending

To customize the Evolution provider:

1. Inherit from `wa.provider.evolution` model
2. Override specific methods
3. The auto-discovery system will still work

## License

LGPL-3

## Author

Your Company Name

## Support

For issues related to:
- **Plugin functionality**: Contact your Odoo developer
- **Evolution API**: Check Evolution API documentation
- **Base module**: Check wa_conn documentation

## Changelog

### Version 18.0.1.0.0
- Initial release
- Full Evolution API integration
- Auto-discovery support
- All abstract methods implemented
