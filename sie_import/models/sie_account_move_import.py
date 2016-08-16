#-*- coding: utf-8 -*-
from openerp import models, fields, api
import time
from openerp.exceptions import ValidationError
import base64
import cStringIO
from datetime import datetime

def format_date(dt):
	return str(dt[0:4]) + '-' + str(dt[4:6]) + '-' + str(dt[6:8])

class sie_account_move_import(models.Model):
	_name = "sie.account.move.import"
	_inherit = ['mail.thread', 'ir.needaction_mixin']
	_description = "SIE Journal Entries Import"
	_order = "id desc"
	_rec_name = "filename"

	file = fields.Binary('File', required=True)
	filename = fields.Char('Filename')
	journal_id = fields.Many2one('account.journal', 'Journal')
	move_check = fields.Boolean('Journal Entry Created?')
	import_id = fields.Many2one('sie.account.move.import', 'Import Reference')
	date = fields.Datetime('Date', default=datetime.now())
	result = fields.Html('Result')
	trans_line = fields.One2many('sie.account.move.line', 'import_id', 'Journal Entries')
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
				fformat, ttype, company_name, program, version, export_date = None, None, None, None, None, None
				ref, refdates, trans = [], [], {}
				refcount = 0
				
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
						ver = res.split('VER')[1]
						i = [i for i,x in enumerate(ver) if x == '"']
						if i: 
							refcount = refcount + 1
							#get VER Reference:
							start = i[len(i)-2]+1
							stop = i[len(i)-1]
							ref.append(ver[start:stop])
							#get VER Date:
							stop = start - 1
							start = i[len(i)-3]+1
							refdates.append(ver[start:stop].replace(' ', ''))
							
					if 'TRANS' in res or 'trans' in res:
						if ref[refcount-1] not in trans.keys():
							trans[ref[refcount-1]] = []
						else:
							trans[ref[refcount-1]].append(res)

				if not flag:
					result = '<h3 style="color:red">FLAGGA not set correctly.</h3>FLAGGA : %s'%(flag)
				elif flag:
					try:
						flag = int(flag.strip())
					except Exception:
						result = '<h3 style="color:red">FLAGGA not set correctly.</h3>FLAGGA : %s'%(flag)

				if context and 'validate' in context: #Validate Workflow
					if flag == 0: #new file 
						#check existing Import reference with same file data:
						import_ids = self.search([
										('company_name','=',company_name),
										('program_name','=',program),
										('version','=',version),	
										('export_date_char','=',export_date),
										('state', 'in', ('validate','done'))
									])
						if not import_ids and ref:
							return self.write({
										'company_name': company_name,
										'program_name': program,
										'version': version,
										'export_date_char': export_date,
										'state': 'validate'
							})
						elif import_ids and ref: #file already imported with file data
							if import_ids.state == 'validate':
								status = 'Validated'
							elif import_ids.state == 'done':
								status = 'Imported'
							return self.write({
										'company_name': company_name,
										'program_name': program,
										'version': version,
										'export_date_char': export_date,
										'state': 'fail',
										'result': '<h3 style="color:red">File already %s with similar "File Data"</h3>'%(status),
										'import_id': import_ids.id
							})
						elif not ref:
							return self.write({
										'company_name': company_name,
										'program_name': program,
										'version': version,
										'export_date_char': export_date,
										'state': 'fail',
										'result': '<h3 style="color:red">Journal Entries are missing for Import!</h3>',
							})
					else: #flag not set correctly
						return self.write({
									'company_name': company_name,
									'program_name': program,
									'version': version,
									'export_date_char': export_date,
									'state': 'fail',
									'result': result
						})
				else: #Import Workflow
					print "Import workflow"
					journal_id = rec.journal_id.id
					for r in range(0, len(ref)):
						reference = ref[r]
						ref_date = refdates[r]
						dt = format_date(ref_date)
						dt = datetime.strptime(dt, "%Y-%m-%d").date()
						move_id = self.env['account.move'].create({
																	'journal_id': journal_id,
																	'date': dt,
																	'ref': reference
												})
						result = '<h3 style="color:blue">Import Successful! Journal Entries created.</h3>'
						self.env['sie.account.move.line'].create({'import_id': rec.id, 'move_id': move_id.id})
						self.write({'result': result, 'move_check': True})

					

class sie_account_move_line(models.Model):
	_name = "sie.account.move.line"
	_description = "SIE Journal Entries"

	import_id = fields.Many2one('sie.account.move.import', 'Import Ref')
	move_id = fields.Many2one('account.move', 'Journal Entry')

