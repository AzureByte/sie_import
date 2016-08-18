# -*- coding: utf-8 -*-
###############################################################################
#
#    Linserv Aktiebolag.
#    Copyright (C) 2016-TODAY Linserv Aktiebolag(<http://www.linserv.se/>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'SIE Import',
    'version': '1.0.0',
    'category': 'Accounting',
    'summary': 'SIE Journal Entries Import',
    'description': """
==============================================================================
                        SIE Journal Entries Import
==============================================================================
This module provides functionality to import Journal Enrtries from SIE format files.

* Menu : Accounting / Adviser / SIE Import
    """,
    'author': 'Linserv Aktiebolag',
    'website': 'http://www.linserv.se',
    'depends': ['account'],
    'data': [
        'views/sie_account_move_import.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
