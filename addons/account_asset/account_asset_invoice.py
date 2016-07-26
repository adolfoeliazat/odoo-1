# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _

class account_invoice(osv.osv):

    _inherit = 'account.invoice'
    def action_number(self, cr, uid, ids, *args, **kargs):
        result = super(account_invoice, self).action_number(cr, uid, ids, *args, **kargs)
        for inv in self.browse(cr, uid, ids):
            self.pool.get('account.invoice.line').asset_create(cr, uid, inv.invoice_line)
        return result

    def line_get_convert(self, cr, uid, x, part, date, context=None):
        res = super(account_invoice, self).line_get_convert(cr, uid, x, part, date, context=context)
        res['asset_id'] = x.get('asset_id', False)
        return res


class account_invoice_line(osv.osv):

    _inherit = 'account.invoice.line'
    _columns = {
        'asset_category_id': fields.many2one('account.asset.category', 'Asset Category'),
    }
    def asset_create(self, cr, uid, lines, context=None):
        context = context or {}
        asset_obj = self.pool.get('account.asset.asset')
        asset_ids = []
        for line in lines:
            if line.invoice_id.number:
                #FORWARDPORT UP TO SAAS-6
                asset_ids += asset_obj.search(cr, SUPERUSER_ID, [('code', '=', line.invoice_id.number), ('company_id', '=', line.company_id.id)], context=context)
        asset_obj.write(cr, SUPERUSER_ID, asset_ids, {'active': False})
        for line in lines:
            if line.asset_category_id:
                vals = {
                    'name': line.name,
                    'code': line.invoice_id.number or False,
                    'category_id': line.asset_category_id.id,
                    'purchase_value': line.price_subtotal,
                    'partner_id': line.invoice_id.partner_id.id,
                    'company_id': line.invoice_id.company_id.id,
                    'currency_id': line.invoice_id.currency_id.id,
                    'purchase_date' : line.invoice_id.date_invoice,
                }
                changed_vals = asset_obj.onchange_category_id(cr, uid, [], vals['category_id'], context=context)
                vals.update(changed_vals['value'])
                asset_id = asset_obj.create(cr, uid, vals, context=context)
                if line.asset_category_id.open_asset:
                    asset_obj.validate(cr, uid, [asset_id], context=context)
        return True


class account_entries_report(osv.osv):
    _name = "account.entries.report"
    _inherit = "account.entries.report"

    _columns = {
        'asset_id': fields.many2one('account.asset.asset', 'Asset', readonly=True),
        'parent_asset_id': fields.many2one('account.asset.asset', 'Asset Parent', readonly=True),
        'asset_category_id': fields.many2one('account.asset.category', 'Asset Category', readonly=True),
    }

    def _get_select(self):
        res = super(account_entries_report, self)._get_select()
        return """%s,
         l.asset_id as asset_id,
         aasset.parent_id as parent_asset_id,
         aasset.category_id as asset_category_id
        """%(res)

    def _get_from(self):
        res = super(account_entries_report, self)._get_from()
        return """%s
         left join account_asset_asset aasset on (l.asset_id = aasset.id)
        """ % (res)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: