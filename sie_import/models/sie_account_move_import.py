#-*- coding: utf-8 -*-
from openerp import models, fields, api
import time
from openerp.exceptions import ValidationError
import base64
import cStringIO

class sie_account_move_import(models.Model):
	_name = "sie.account.move.import"
	_inherit = ['mail.thread', 'ir.needaction_mixin']
	_description = "SIE Journal Entries Import"
	_order = "id desc"
	_rec_name = "filename"

	file = fields.Binary('File', required=True)
	filename = fields.Char('Filename')
	journal_id = fields.Many2one('account.journal', 'Journal')
	date = fields.Datetime('Date', default=fields.Date.today)
	move_id = fields.Many2one('account.move', 'Journal Entry', track_visibility='onchange')
	result = fields.Html('Result')
	state = fields.Selection([('draft', 'Draft'), 
							  ('validate', 'Validated'), 
							  ('fail', 'Failed'),
							  ('done','Success')], 'Import Status', track_visibility='onchange', default='draft')

	#export fields
	company_name = fields.Char('Company Name')
	program_name = fields.Char('Program Name')
	version = fields.Char('Verson')
	export_date_char = fields.Char('Export Date')
	export_date = fields.Date('Export Date')

	@api.multi
	def action_import(self):
		context = self._context
		for rec in self:
			fileext = rec.filename.split('.')[-1]
			if fileext not in ('SI', 'si', 'Si', 'sI'):
				raise ValidationError('Invalid File!\nAllowed file format : si')
			encoding = 'cp437'
			data = base64.decodestring(rec.file)
			result = []
			if data:
				data = data.decode(encoding)
				data = data.split('\r\n')
				for d in data:
					result.append(d.replace('#',''))
				print result
				flag = 0
				ref, fformat, ttype, company_name, program, version, export_date = None, None, None, None, None, None, None
				trans = []
				for res in result:
					if len(res.split('FLAGGA')) > 1:
						flag = res.split('FLAGGA')[1]
					
					if len(res.split('FORMAT')) > 1:
						fformat = res.split('FORMAT')[1]

					if len(res.split('SIETYP')) > 1:
						ttype = res.split('SIETYP')[1]

					if len(res.split('FNAMN')) > 1:
						company_name = res.split('FNAMN')[1].replace('"', '')

					if len(res.split('PROGRAM')) > 1:
						program = res.split('PROGRAM')[1]
						i = [i for i,x in enumerate(program) if x == '"']
						if i and len(i) == 2: 
							version = program[i[-1]+1:]
							program = program.split(version)[0]
							program = program.replace('"', '')
						elif i and len(i) > 2:
							version = program[i[len(i)-2]+1:i[-1]-1]
							program = program.replace('"', '')
							program = program.split(version)[0]

					if len(res.split('GEN')) > 1:
						export_date = res.split('GEN')[1].split('"')[0]

					if len(res.split('VER')) > 1:
						ref = res.split('VER')[1]
						i = [i for i,x in enumerate(ref) if x == '"']
						if i: 
							start = i[len(i)-2]+1
							stop = i[len(i)-1]
							ref = ref[start:stop]

					if 'TRANS' in res or 'trans' in res:
						trans.append(res)
				if context and 'validate' in context:
					if int(flag.strip()) == 0:
						return self.write({
									'company_name': company_name,
									'program_name': program,
									'version': version,
									'export_date_char': export_date,
									'state': 'validate'
						})
					else:
						return self.write({
									'company_name': company_name,
									'program_name': program,
									'version': version,
									'export_date_char': export_date,
									'state': 'fail',
									'result': '<b>FLAGGA is not 0.<b><br/>FLAGGA : %s'%(flag)
						})

