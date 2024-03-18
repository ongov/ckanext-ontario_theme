from six.moves import zip_longest

from flask import Blueprint, make_response
from flask.views import MethodView

import ckan.plugins.toolkit as toolkit

import ckan.lib.navl.dictization_functions as dict_fns
from ckan.logic import (
    tuplize_dict,
    parse_params,
)
from ckan.plugins.toolkit import (
    ObjectNotFound, NotAuthorized, get_action, get_validator, _, request,
    abort, render, c, h
)
from ckanext.datastore.logic.schema import (
    list_of_strings_or_string,
    json_validator,
    unicode_or_json_validator,
)
from ckanext.datastore.writer import (
    csv_writer,
    tsv_writer,
    json_writer,
    xml_writer,
)
from .plugin_for_validation import get_datastore_info

int_validator = get_validator(u'int_validator')
boolean_validator = get_validator(u'boolean_validator')
ignore_missing = get_validator(u'ignore_missing')
one_of = get_validator(u'one_of')
default = get_validator(u'default')
unicode_only = get_validator(u'unicode_only')

DUMP_FORMATS = u'csv', u'tsv', u'json', u'xml'
PAGINATE_BY = 32000

datastore = Blueprint(u'datastore', __name__)

class DictionaryView(MethodView):

    def _prepare(self, id, resource_id):
        try:
            # resource_edit_base template uses these
            pkg_dict = get_action(u'package_show')(None, {u'id': id})
            resource = get_action(u'resource_show')(None, {u'id': resource_id})
            rec = get_action(u'datastore_search')(
                None, {
                    u'resource_id': resource_id,
                    u'limit': 0
                }
            )
            return {
                u'pkg_dict': pkg_dict,
                u'resource': resource,
                u'fields': [
                    f for f in rec[u'fields'] if not f[u'id'].startswith(u'_')
                ]
            }

        except (ObjectNotFound, NotAuthorized):
            abort(404, _(u'Resource not found'))

    def get(self, id, resource_id):
        u'''Data dictionary view: show field labels and descriptions'''

        data_dict = self._prepare(id, resource_id)

        # global variables for backward compatibility
        c.pkg_dict = data_dict[u'pkg_dict']
        c.resource = data_dict[u'resource']

        return render(u'datastore/dictionary.html', data_dict)

    def post(self, id, resource_id):
        u'''Data dictionary view: edit field labels and descriptions'''
        data_dict = self._prepare(id, resource_id)
        fields = data_dict[u'fields']
        data = dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
        info = data.get(u'info')
        if not isinstance(info, list):
            info = []
        info = info[:len(fields)]

        get_action(u'datastore_create')(
            None, {
                u'resource_id': resource_id,
                u'force': True,
                u'fields': [{
                    u'id': f[u'id'],
                    u'type': f[u'type'],
                    u'info': fi if isinstance(fi, dict) else {}
                } for f, fi in zip_longest(fields, info)]
            }
        )

        """ h.flash_success(
            _(
                u'Data Dictionary saved. Any type overrides will '
                u'take effect when the resource is next uploaded '
                u'to DataStore'
            )
        ) """
        ui_dict = get_datastore_info(resource_id)
        datastore_info=toolkit.get_action('datastore_search')(
		data_dict={'id': resource_id,
                           'limit': 0
                          })

        for row in datastore_info['fields']:
            if 'info' in row:
                col_name = row['id']
                row['info']['frictionless_dict'] = [item for item in ui_dict['fields'] if item.get('name')==col_name]
        
        toolkit.get_action('datastore_create')(None,
              {
                'resource_id': resource_id,
                'force': True,
                'fields': datastore_info.get('fields')[1:]
                }
            )
        toolkit.get_action(u'resource_validation_run')(
                            {u'ignore_auth': True},
                            {u'resource_id': resource_id,
                             u'async': False,
                             u'ui_dict': ui_dict})
        
        return h.redirect_to(
            u'datastore.dictionary', id=id, resource_id=resource_id
        )
        # h.url_for('validation_read',id=id,resource_id=resource_id)