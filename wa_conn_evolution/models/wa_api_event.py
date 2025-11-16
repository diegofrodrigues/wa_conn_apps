from odoo import fields, models


class WAApiEvent(models.Model):
    """
    Evolution API Events
    
    Lista de eventos que a Evolution API pode enviar via webhook.
    Este modelo é específico do provider Evolution.
    """
    _name = 'wa.api.event'
    _description = 'WhatsApp API Event (Evolution)'
    _order = 'name'

    name = fields.Char(
        string="Event Name", 
        required=True,
        help="Nome do evento na Evolution API (ex: MESSAGES_UPSERT, QRCODE_UPDATED)"
    )
    
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Event name must be unique!')
    ]
