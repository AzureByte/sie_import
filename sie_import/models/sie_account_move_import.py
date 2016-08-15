#-*- coding: utf-8 -*-
from openerp import models, fields, api
import time

class sie_account_move_import(models.Model):
	_name = "sie.account.move.import"
	_inherit = ['mail.thread', 'ir.needaction_mixin']
	_description = "SIE Journal Entries Import"
	_order = "id desc"

	file = fields.Binary('File', required=True)
	filename = fields.Char('Filename')
	date = fields.Datetime('Date', default=fields.Date.today)
	move_id = fields.Many2one('account.move', 'Journal Entry', track_visibility='onchange')
	result = fields.Text('Result')
	state = fields.Selection([('draft', 'Draft'), ('done','Done')], 'Import Status', track_visibility='onchange', default='draft')

	#export fields
	company_name = fields.Char('Company Name')
	program_name = fields.Char('Program Name')
	version = fields.Char('Verson')
	export_date = fields.Date('Export Date')

	@api.multi
	def action_import(self):
		for doc in self:
			print doc.filename
