u'''
Overrides ckan/views/resource.py
'''

from ckan.views.resource import CreateView as CreateView #as CKANMethodView
#import ckan.views.resource 
from flask.views import MethodView
import ckan.model as model
import six
import ckan.lib.datapreview as lib_datapreview
import ckan.plugins as plugins
import cgi

from ckan.common import _, g, request
from ckan.views.dataset import (
    _get_pkg_template, _get_package_type, _setup_template_variables
)

import ckan.lib.navl.dictization_functions as dict_fns
import ckan.lib.base as base
import ckan.logic as logic
import ckan.lib.helpers as h
from ckan.views.home import CACHE_PARAMETERS

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
get_action = logic.get_action

class CreateView(MethodView):
#class OntarioThemeResourceCreateView(MethodView):
    def post(self, package_type, id):
        save_action = request.form.get(u'save')
        print('HEJ oma def post')
        print('HEJ save action: ', save_action)
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
            print('HEJ save action step2', save_action)
            pkg_dict = get_action(u'package_show')(context, {u'id': id})
            resource_dict = pkg_dict.get('resources')
            resource_id_array = [p['id'] for p in resource_dict]
            last_id = resource_id_array[-1]

            return h.redirect_to(
                u'datastore.dictionary', id=id, resource_id=last_id
            )

            # return h.redirect_to(h.url_for(
            #                             u'{}_resource.edit_step2'.format(package_type),
            #                                                         resource_id=last_id,
            #                                                         id=id
            #                             )
            #                 )
        

            # this_redirect = h.url_for(
            #                                 u'{}_resource.edit_step2'.format(package_type),
            #                                                            resource_id=last_id,
            #                                                            id=id
            #                               )
            # print('HEI this redirect: ', this_redirect)

            # return h.redirect_to(h.url_for(
            #                                 u'{}_resource.edit_step2'.format(package_type),
            #                                                            resource_id=last_id,
            #                                                            id=id
            #                               )
            #                     )
            # From scheming:
            # return h.redirect_to(
            #     '{}.scheming_new_page'.format(package_type),
            #     id=complete_data['name'],
            #     page=page + 1,
            # )

        else:
            # add more resources
            return h.redirect_to(
                u'{}_resource.new'.format(package_type),
                id=id
            )

    def get(
        self, package_type, id, data=None, errors=None, error_summary=None
    ):
        print('HEJ ontario theme get')
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

# FIXME: could anyone think about better name?
class EditResourceViewView(MethodView):
    def _prepare(self, id, resource_id):
        print('HEJ ont theme EditResourceViewView def prepare')
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'for_view': True,
            u'auth_user_obj': g.userobj
        }

        # update resource should tell us early if the user has privilages.
        try:
            check_access(u'resource_update', context, {u'id': resource_id})
        except NotAuthorized:
            return base.abort(
                403,
                _(u'User %r not authorized to edit %s') % (g.user, id)
            )

        # get resource and package data
        try:
            pkg_dict = get_action(u'package_show')(context, {u'id': id})
            pkg = context[u'package']
        except (NotFound, NotAuthorized):
            return base.abort(404, _(u'Dataset not found'))
        try:
            resource = get_action(u'resource_show')(
                context, {
                    u'id': resource_id
                }
            )
        except (NotFound, NotAuthorized):
            return base.abort(404, _(u'Resource not found'))

        # TODO: remove
        g.pkg_dict = pkg_dict
        g.pkg = pkg
        g.resource = resource

        extra_vars = dict(
            data={},
            errors={},
            error_summary={},
            view_type=None,
            to_preview=False,
            pkg_dict=pkg_dict,
            pkg=pkg,
            resource=resource
        )
        return context, extra_vars

    def post(self, package_type, id, resource_id, view_id=None):
        print('HEJ ont theme EditResourceViewView def post')
        context, extra_vars = self._prepare(id, resource_id)
        data = clean_dict(
            dict_fns.unflatten(
                tuplize_dict(
                    parse_params(request.form, ignore_keys=CACHE_PARAMETERS)
                )
            )
        )
        data.pop(u'save', None)

        to_preview = data.pop(u'preview', False)
        if to_preview:
            context[u'preview'] = True
        to_delete = data.pop(u'delete', None)
        data[u'resource_id'] = resource_id
        data[u'view_type'] = request.args.get(u'view_type')

        try:
            if to_delete:
                data[u'id'] = view_id
                get_action(u'resource_view_delete')(context, data)
            elif view_id:
                data[u'id'] = view_id
                data = get_action(u'resource_view_update')(context, data)
            else:
                data = get_action(u'resource_view_create')(context, data)
        except ValidationError as e:
            # Could break preview if validation error
            to_preview = False
            extra_vars[u'errors'] = e.error_dict,
            extra_vars[u'error_summary'] = e.error_summary
        except NotAuthorized:
            # This should never happen unless the user maliciously changed
            # the resource_id in the url.
            return base.abort(403, _(u'Unauthorized to edit resource'))
        else:
            if not to_preview:
                return h.redirect_to(
                    u'{}_resource.views'.format(package_type),
                    id=id, resource_id=resource_id
                )
        extra_vars[u'data'] = data
        extra_vars[u'to_preview'] = to_preview
        return self.get(package_type, id, resource_id, view_id, extra_vars)

    def get(
        self, package_type, id, resource_id, view_id=None, post_extra=None
    ):
        print('HEJ ont theme EditResourceViewView def get')
        context, extra_vars = self._prepare(id, resource_id)
        to_preview = extra_vars[u'to_preview']
        if post_extra:
            extra_vars.update(post_extra)

        package_type = _get_package_type(id)
        data = extra_vars[u'data'] if u'data' in extra_vars else None
        if data and u'view_type' in data:
            view_type = data.get(u'view_type')
        else:
            view_type = request.args.get(u'view_type')

        # view_id exists only when updating
        if view_id:
            if not data or not view_type:
                try:
                    view_data = get_action(u'resource_view_show')(
                        context, {
                            u'id': view_id
                        }
                    )
                    view_type = view_data[u'view_type']
                    if data:
                        data.update(view_data)
                    else:
                        data = view_data
                except (NotFound, NotAuthorized):
                    return base.abort(404, _(u'View not found'))

            # might as well preview when loading good existing view
            if not extra_vars[u'errors']:
                to_preview = True

        data[u'view_type'] = view_type
        view_plugin = lib_datapreview.get_view_plugin(view_type)
        if not view_plugin:
            return base.abort(404, _(u'View Type Not found'))

        _setup_template_variables(
            context, {u'id': id}, package_type=package_type
        )

        data_dict = {
            u'package': extra_vars[u'pkg_dict'],
            u'resource': extra_vars[u'resource'],
            u'resource_view': data
        }

        view_template = view_plugin.view_template(context, data_dict)
        form_template = view_plugin.form_template(context, data_dict)

        extra_vars.update({
            u'form_template': form_template,
            u'view_template': view_template,
            u'data': data,
            u'to_preview': to_preview,
            u'datastore_available': plugins.plugin_loaded(u'datastore')
        })
        extra_vars.update(
            view_plugin.setup_template_variables(context, data_dict) or {}
        )
        extra_vars.update(data_dict)

        if view_id:
            return base.render(u'package/edit_view.html', extra_vars)

        return base.render(u'package/new_view.html', extra_vars)
