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
                              ('done','Success')],
                              'Import Status',
                              track_visibility='onchange',
                              default='draft'
                            )

    #export fields
    company_name = fields.Char('Company Name')
    program_name = fields.Char('Program Name')
    version = fields.Char('Verson')
    export_date_char = fields.Char('Export Date')
    export_date = fields.Date('Export Date')

    @api.one
    def set_draft(self):
        for rec in self:
            return self.write({'state': 'draft', 'result': None, 'move_check':False})

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

                flag = 0
                fformat, ttype, company_name, program, version, export_date = None, None, None, None, None, None
                export_dt = False
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
                        i = [i for i, x in enumerate(program) if x == '"']
                        if i and len(i) == 2:
                            version = program[i[-1]+1:]
                            program = program.split(version)[0]
                            program = program.replace('"', '')
                        elif i and len(i) > 2:
                            version = program[i[len(i)-2]+1:i[-1]-1]
                            program = program.replace('"', '')
                            program = program.split(version)[0]

                    if len(res.split('GEN')) > 1:
                        export_date = res.split('GEN')[1].split('"')[0].replace(' ', '')
                        export_dt = format_date(export_date)

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
                            trans[ref[refcount-1]] = [res]
                        else:
                            trans[ref[refcount-1]].append(res)
                result = ''
                if not flag:
                    result = '<h3 style="color:red">FLAGGA not set correctly.</h3>FLAGGA : %s'%(flag)
                elif flag:
                    try:
                        flag = int(flag.strip())
                        if flag != 0:
                            result = '<h3 style="color:red">FLAGGA not set correctly.</h3>FLAGGA : %s'%(flag)
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
                                        'export_date': export_dt,
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
                                        'export_date': export_dt,
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
                                        'export_date': export_dt,
                                        'state': 'fail',
                                        'result': '<h3 style="color:red">Journal Entries are missing for Import!</h3>',
                            })
                    else: #flag not set correctly
                        return self.write({
                                    'company_name': company_name,
                                    'program_name': program,
                                    'version': version,
                                    'export_date_char': export_date,
                                    'export_date': export_dt,
                                    'state': 'fail',
                                    'result': result
                        })
                else: #Import Workflow
                    journal_id = rec.journal_id.id
                    count = 0
                    no_account_ref_flag = False
                    no_account_ref = '<h3 style="color:red">Some Journal Items were not created!</h3>Account(s) not found with Code :<br/>'
                    unbalanced_ref_check = False
                    unbalanced_ref = '<h3 style="color:red">Some Journal Entries were not created as they are Unbalanced.</h3><b>Reference(s) :</b><br/>'

                    flag = False
                    try:
                        for r in range(0, len(ref)):
                            #construct Journal Entry
                            reference = ref[r]
                            ref_date = refdates[r]
                            dt = format_date(ref_date)
                            dt = datetime.strptime(dt, "%Y-%m-%d").date()

                            #compute & create Journal Items:
                            lines = []
                            for line in trans[reference]:
                                transaction = line.split('TRANS')[1]
                                code = transaction.split('{')[0].replace(' ', '')
                                account = self.env['account.account'].search([('code','=',code)])
                                account_id = False
                                if account: account_id = account.id

                                amount = transaction.split('}')[1].split('"')[0].replace(' ', '')
                                amount = float(amount)
                                credit, debit = 0.0, 0.0
                                if amount > 0:
                                    debit = amount
                                else:
                                    credit = abs(amount)

                                fstart = [i for i,x in enumerate(transaction) if x == '{']
                                fend = [i for i,x in enumerate(transaction) if x == '}']
                                move_name = '/'
                                if fstart and fend:
                                    move_name = transaction[fstart[0]+1:fend[0]]
                                if not move_name:
                                    move_name = '/'
                                #construct Journal Items:
                                if account_id:
                                    move_line = [0, False, {
                                        'account_id': account_id,
                                        'credit': credit,
                                        'debit': debit,
                                        'name': move_name
                                    }]
                                    lines.append(move_line)
                                else:
                                    no_account_ref_flag = True
                                    no_account_ref = no_account_ref + code + '<br/>'

                            #Validate Journal Items to check if it is Unbalanced:
                            unbalanced = False
                            move_credit, move_debit = 0, 0
                            for l in lines:
                                l = l[2]
                                move_credit = move_credit + l['credit']
                                move_debit = move_debit + l['debit']
                            if round(move_credit,6) != round(move_debit,6):
                                unbalanced = True

                            #Update Journal Items in Journal Entry:
                            if not unbalanced:
                                count = count + 1
                                move_id = self.env['account.move'].create({
                                                                            'journal_id': journal_id,
                                                                            'date': dt,
                                                                            'ref': reference
                                })
                                self.env['sie.account.move.line'].create({'import_id': rec.id, 'move_id': move_id.id})
                                move_id.write({'line_ids': lines})
                            else:
                                unbalanced_ref_check = True
                                unbalanced_ref = unbalanced_ref + reference + '<br/>'
                    except Exception, e:
                        flag = True
                        exception = e

                    if not flag: #no exception processing TRANS
                        if count:
                            result = '<h3 style="color:blue">Import Successful! Journal Entries created.</h3>'
                        if unbalanced_ref_check:
                            result = result + unbalanced_ref
                        if no_account_ref_flag:
                            result = result + no_account_ref
                        if count: #at least one Journal Entry Imported
                            self.write({'result': result, 'move_check': True, 'state': 'done'})
                        else:
                            self.write({'result': result, 'state': 'fail'})
                    else:
                        result = '''<h3 style="color:red">Failed! Journal Entry creation Failed.</h3><b>Error: </b>%s'''%(exception)
                        self.write({'result': result, 'state': 'fail'})



class sie_account_move_line(models.Model):
    _name = "sie.account.move.line"
    _description = "SIE Journal Entries"

    import_id = fields.Many2one('sie.account.move.import', 'Import Ref')
    move_id = fields.Many2one('account.move', 'Journal Entry')

