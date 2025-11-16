from odoo import api, fields, models, _
from odoo.exceptions import UserError
import random
import time

class WASendQueue(models.Model):
    _name = 'wa.send.queue'
    _description = 'WA Send Queue Item'
    _order = 'scheduled_datetime, id'

    mass_send_id = fields.Many2one('wa.mass.send', string='Mass Send', ondelete='cascade', required=True)
    partner_id = fields.Many2one('res.partner', string='Recipient', required=True)
    wa_account_id = fields.Many2one('wa.account', string='WA Account', required=True)
    wa_template_id = fields.Many2one('wa.template', string='WA Template')
    wa_message = fields.Text(string='WA Message')
    wa_media = fields.Binary(string='Media File')
    wa_media_filename = fields.Char(string='Media Filename')
    scheduled_datetime = fields.Datetime(string='Scheduled Date/Time')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('error', 'Error'),
        ('cancelled', 'Cancelled'),
    ], default='pending', string='Status', required=True)
    error_message = fields.Text(string='Error Message')
    last_attempt = fields.Datetime(string='Last Attempt')
    attempts = fields.Integer(string='Attempts', default=0)

    def process_queue_item(self):
        for item in self:
            if item.status != 'pending':
                continue
            item.status = 'sending'
            item.last_attempt = fields.Datetime.now()
            item.attempts += 1
            account = item.wa_account_id
            msg = item.wa_message
            if item.wa_template_id:
                msg = item.wa_template_id.render_template('wa_message', item.partner_id)
            try:
                if item.wa_template_id and item.wa_template_id.wa_media:
                    account.send_media(
                        mobile=item.partner_id.mobile,
                        caption=msg,
                        b64=item.wa_template_id.wa_media,
                        filename=item.wa_template_id.wa_media_filename
                    )
                else:
                    account.send_text(
                        mobile=item.partner_id.mobile,
                        message=msg
                    )
                item.status = 'sent'
                item.error_message = False
            except Exception as e:
                item.status = 'error'
                item.error_message = str(e)

class WAMassSend(models.Model):
    _inherit = 'wa.mass.send'

    queue_ids = fields.One2many('wa.send.queue', 'mass_send_id', string='Queue Items')

    def action_generate_queue(self):
        for mass_send in self:
            queue_vals = []
            for partner in mass_send.partner_ids:
                queue_vals.append({
                    'mass_send_id': mass_send.id,
                    'partner_id': partner.id,
                    'wa_account_id': mass_send.wa_account_id.id,
                    'wa_template_id': mass_send.wa_template_id.id if mass_send.wa_template_id else False,
                    'wa_message': mass_send.wa_message,
                    'wa_media': mass_send.wa_template_id.wa_media if mass_send.wa_template_id else False,
                    'wa_media_filename': mass_send.wa_template_id.wa_media_filename if mass_send.wa_template_id else False,
                    'scheduled_datetime': mass_send.scheduled_datetime,
                })
            self.env['wa.send.queue'].create(queue_vals)
            mass_send.state = 'scheduled'

    def action_send_queue(self):
        for mass_send in self:
            # Processa todos os itens pendentes da fila
            pending_items = mass_send.queue_ids.filtered(lambda q: q.status == 'pending')
            for item in pending_items:
                item.process_queue_item()
            # Atualiza status do envio em massa
            if all(q.status == 'sent' for q in mass_send.queue_ids):
                mass_send.state = 'done'
            elif any(q.status == 'error' for q in mass_send.queue_ids):
                mass_send.state = 'error'
            else:
                mass_send.state = 'sending'

    @api.model
    def cron_process_send_queue(self):
        # Processa todos os itens pendentes da fila, pode ser chamado por um cron
        pending_items = self.env['wa.send.queue'].search([
            ('status', '=', 'pending'),
            ('scheduled_datetime', '<=', fields.Datetime.now()),
        ], limit=10)  # Processa em lotes de 10
        for item in pending_items:
            item.process_queue_item()
        # Atualiza o status dos envios em massa relacionados
        for mass_send in pending_items.mapped('mass_send_id'):
            mass_send.action_send_queue()
