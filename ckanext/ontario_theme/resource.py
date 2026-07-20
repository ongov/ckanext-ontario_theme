u'''
Overrides ckan/views/resource.py
'''

from ckan.views.resource import CreateView as CreateView
from ckan.views.resource import EditView as EditView
from flask.views import MethodView
import ckan.model as model
import six
import cgi

from ckan.common import _, g, request
from ckan.views.dataset import (
    _get_pkg_template
)

import ckan.lib.navl.dictization_functions as dict_fns
import ckan.lib.base as base
import ckan.logic as logic
import ckan.lib.helpers as h

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
get_action = logic.get_action

from flask import Blueprint
datastore = Blueprint(u'datastore', __name__)

class CreateView(MethodView):
    def post(self, package_type, id):
        save_action = request.form.get(u'save')
        data = clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
        )
        data.update(clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.files)))
        ))

        # we don't want to include save as it is part of the form
        del data[u'save']
        resource_id = data.pop(u'id')

        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }

        # see if we have any data that we are trying to save
        data_provided = False
        for key, value in six.iteritems(data):
            if (
                    (value or isinstance(value, cgi.FieldStorage))
                    and key != u'resource_type'):
                data_provided = True
                break

        if not data_provided and save_action != u"go-dataset-complete":
            if save_action == u'go-dataset':
                # go to final stage of adddataset
                return h.redirect_to(u'{}.edit'.format(package_type), id=id)
            # see if we have added any resources
            try:
                data_dict = get_action(u'package_show')(context, {u'id': id})
            except NotAuthorized:
                return base.abort(403, _(u'Unauthorized to update dataset'))
            except NotFound:
                return base.abort(
                    404,
                    _(u'The dataset {id} could not be found.').format(id=id)
                )
            if not len(data_dict[u'resources']):
                # no data so keep on page
                msg = _(u'You must add at least one data resource')
                # On new templates do not use flash message

                errors = {}
                error_summary = {_(u'Error'): msg}
                return self.get(package_type, id, data, errors, error_summary)

            # XXX race condition if another user edits/deletes
            data_dict = get_action(u'package_show')(context, {u'id': id})
            get_action(u'package_update')(
                dict(context, allow_state_change=True),
                dict(data_dict, state=u'active')
            )
            return h.redirect_to(u'{}.read'.format(package_type), id=id)

        data[u'package_id'] = id
        try:
            if resource_id:
                data[u'id'] = resource_id
                get_action(u'resource_update')(context, data)
            else:
                get_action(u'resource_create')(context, data)
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            if data.get(u'url_type') == u'upload' and data.get(u'url'):
                data[u'url'] = u''
                data[u'url_type'] = u''
                data[u'previous_upload'] = True
            return self.get(package_type, id, data, errors, error_summary)
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized to create a resource'))
        except NotFound:
            return base.abort(
                404, _(u'The dataset {id} could not be found.').format(id=id)
            )
        if save_action == u'go-metadata':
            # XXX race condition if another user edits/deletes
            data_dict = get_action(u'package_show')(context, {u'id': id})
            get_action(u'package_update')(
                dict(context, allow_state_change=True),
                dict(data_dict, state=u'active')
            )
            return h.redirect_to(u'{}.read'.format(package_type), id=id)
        elif save_action == u'go-dataset':
            # go to first stage of add dataset
            return h.redirect_to(u'{}.edit'.format(package_type), id=id)
        elif save_action == u'go-dataset-complete':
            return h.redirect_to(u'{}.read'.format(package_type), id=id)
        elif save_action == u'go-dataset-step2':
            pkg_dict = get_action(u'package_show')(context, {u'id': id})
            resource_dict = pkg_dict.get('resources')
            resource_id_array = [p['id'] for p in resource_dict]
            resource_id = resource_id_array[-1]
            return h.redirect_to(
                "ontario_theme.resource_validation",
                id=id,
                resource_id=resource_id
            )
        else:
            # add more resources
            return h.redirect_to(
                u'{}_resource.new'.format(package_type),
                id=id
            )

    def get(
        self, package_type, id, data=None, errors=None, error_summary=None
    ):
        # get resources for sidebar
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        try:
            pkg_dict = get_action(u'package_show')(context, {u'id': id})
        except NotFound:
            return base.abort(
                404, _(u'The dataset {id} could not be found.').format(id=id)
            )
        try:
            check_access(
                u'resource_create', context, {u"package_id": pkg_dict["id"]}
            )
        except NotAuthorized:
            return base.abort(
                403, _(u'Unauthorized to create a resource for this package')
            )

        package_type = pkg_dict[u'type'] or package_type
        errors = errors or {}
        error_summary = error_summary or {}
        extra_vars = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary,
            u'action': u'new',
            u'resource_form_snippet': _get_pkg_template(
                u'resource_form', package_type
            ),
            u'dataset_type': package_type,
            u'pkg_name': id,
            u'pkg_dict': pkg_dict
        }
        template = u'package/new_resource_not_draft.html'
        if pkg_dict[u'state'].startswith(u'draft'):
            extra_vars[u'stage'] = ['complete', u'active']
            template = u'package/new_resource.html'
        return base.render(template, extra_vars)

class EditView(MethodView):
    def _prepare(self, id):
        context = {
            u'model': model,
            u'session': model.Session,
            u'api_version': 3,
            u'for_edit': True,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        try:
            check_access(u'package_update', context, {u'id': id})
        except NotAuthorized:
            return base.abort(
                403,
                _(u'User %r not authorized to edit %s') % (g.user, id)
            )
        return context

    def post(self, package_type, id, resource_id):
        context = self._prepare(id)
        data = clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
        )
        data.update(clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.files)))
        ))

        # we don't want to include save as it is part of the form
        del data[u'save']

        data[u'package_id'] = id
        try:
            if resource_id:
                data[u'id'] = resource_id
                get_action(u'resource_update')(context, data)
            else:
                get_action(u'resource_create')(context, data)

        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(
                package_type, id, resource_id, data, errors, error_summary
            )
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized to edit this resource'))
        return h.redirect_to(
            "ontario_theme.resource_validation",
            id=id,
            resource_id=resource_id
        )

    def get(
        self,
        package_type,
        id,
        resource_id,
        data=None,
        errors=None,
        error_summary=None
    ):
        context = self._prepare(id)
        pkg_dict = get_action(u'package_show')(context, {u'id': id})

        try:
            resource_dict = get_action(u'resource_show')(
                context, {
                    u'id': resource_id
                }
            )
        except NotFound:
            return base.abort(404, _(u'Resource not found'))

        if pkg_dict[u'state'].startswith(u'draft'):
            return CreateView().get(package_type, id, data=resource_dict)

        # resource is fully created
        resource = resource_dict
        # set the form action
        form_action = h.url_for(
            u'{}_resource.edit'.format(package_type),
            resource_id=resource_id, id=id
        )
        if not data:
            data = resource_dict

        package_type = pkg_dict[u'type'] or package_type

        errors = errors or {}
        error_summary = error_summary or {}
        extra_vars = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary,
            u'action': u'edit',
            u'resource_form_snippet': _get_pkg_template(
                u'resource_form', package_type
            ),
            u'dataset_type': package_type,
            u'resource': resource,
            u'pkg_dict': pkg_dict,
            u'form_action': form_action
        }
        return base.render(u'package/resource_edit.html', extra_vars)