from odoo import models, fields

class WATeam(models.Model):
    _name = 'wa.team'
    _description = 'WhatsApp Team'
    _inherit = ['mail.thread']

    name = fields.Char(string='Team Name', required=True, tracking=True)
    agent_ids = fields.Many2many('res.users', string='Agents', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
