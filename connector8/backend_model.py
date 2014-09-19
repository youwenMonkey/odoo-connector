# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
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

from openerp import models, fields
import backend


class connector_backend(models.AbstractModel):
    """ An instance of an external backend to synchronize with.

    The backends have to ``_inherit`` this model in the connectors
    modules.
    """
    _name = 'connector.backend'
    _description = 'Connector Backend'
    _backend_service = None

    name = fields.Char(string='Name', required=True)
    version = fields.Selection(selection=[], string='Version', required=True)

    def get_backend(self, id):
        """ For a record of backend, returns the appropriate instance
        of :py:class:`backend.Backend`.
        """

        if self._backend_service is None:
            raise ValueError('The backend %s has no _backend_service' % self)

        backend_record = self.browse(id)
        return backend.get_backend(self._backend_service,
                                   backend_record.version)


class external_binding(models.AbstractModel):
    """ An abstract model for bindings to external records.

    An external binding is a binding between a backend and OpenERP.  For
    example, for a partner, it could be ``magento.res.partner`` or for a
    product, ``magento.product``.

    The final model, will be an ``_inherits`` of the OpenERP model and
    will ``_inherit`` this model.

    It will have a relation to the record (via ``_inherits``) and to the
    concrete backend model (``magento.backend`` for instance).

    It will also contains all the data relative to the backend for the
    record.

    It needs to implements at least these fields:

    openerp_id

        The many2one to the record it links (used by ``_inherits``).

    backend_id

        The many2one to the backend (for instance ``magento.backend``).

    magento_id or prestashop_id or ...

        The ID on the backend.

    sync_date

        Last date of synchronization


    The definition of the relations in ``_columns`` is to be done in the
    concrete classes because the relations themselves do not exist in
    this addon.

    For example, for a ``res.partner.category`` from Magento, I would have
    (this is a consolidation of all the columns from the abstract models,
    in ``magentoerpconnect`` you would not find that)::

        class magento_res_partner_category(orm.Model):
            _name = 'magento.res.partner.category'

            _inherits = {'res.partner.category': 'openerp_id'}

            _columns = {
                'openerp_id': fields.Many2one(
                    comodel_name='res.partner.category',
                    string='Partner Category',
                    required=True,
                    ondelete='cascade'),
                'backend_id': fields.Many2one(
                    comodel_name='magento.backend',
                    string='Magento Backend',
                    required=True,
                    ondelete='restrict'),
                'sync_date': fields.Datetime(
                    string='Last synchronization date'),
                'magento_id': fields.Char(string='ID on Magento'),
                'tax_class_id': fields.Integer(string='Tax Class ID'),
            }

            _sql_constraints = [
                ('magento_uniq', 'unique(backend_id, magento_id)',
                 'Partner Tag with same ID on Magento already exists.'),
            ]


    """
    _name = 'external.binding'
    _description = 'External Binding (abstract)'

    _columns = {
        # TODO write the date on import / export
        # and skip import / export (avoid unnecessary import
        # right after the export)
        'sync_date': fields.Datetime(string='Last synchronization date'),
        # add other fields in concrete models
    }
