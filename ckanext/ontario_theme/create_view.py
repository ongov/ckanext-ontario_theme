import ckan.logic as logic
import ckan.lib.base as base
from ckan.common import _, config, g, request
import ckan.lib.navl.dictization_functions as dict_fns
from ckan.views.dataset import CreateView as CKANCreateView
from ckan.lib.search import SearchError, SearchQueryError, SearchIndexError
import ckan.lib.helpers as h

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
get_action = logic.get_action

import logging
log = logging.getLogger(__name__)


class CreateView(CKANCreateView):
    def post(self, package_type):
        # The staged add dataset used the new functionality when the dataset is
        # partially created so we need to know if we actually are updating or
        # this is a real new.
        context = self._prepare()
        is_an_update = False
        ckan_phase = request.form.get(u'_ckan_phase')
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
            )
        except dict_fns.DataError:
            return base.abort(400, _(u'Integrity Error'))
        try:
            if ckan_phase:
                # prevent clearing of groups etc
                context[u'allow_partial_update'] = True
                # sort the tags
                if u'tag_string' in data_dict:
                    data_dict[u'tags'] = _tag_string_to_list(
                        data_dict[u'tag_string']
                    )
                if data_dict.get(u'pkg_name'):
                    is_an_update = True
                    # This is actually an update not a save
                    data_dict[u'id'] = data_dict[u'pkg_name']
                    del data_dict[u'pkg_name']
                    # don't change the dataset state
                    data_dict[u'state'] = u'draft'
                    # this is actually an edit not a save
                    pkg_dict = get_action(u'package_update')(
                        context, data_dict
                    )

                    # redirect to add dataset resources
                    url = h.url_for(
                        u'{}_resource.new'.format(package_type),
                        id=pkg_dict[u'name']
                    )
                    return h.redirect_to(url)
                # Make sure we don't index this dataset
                # MODIFICATION START
                # add "save-and-finish" to the list
                if request.form[u'save'] not in [
                    u'go-resource', u'go-metadata', u'save-and-finish'
                ]:
                    data_dict[u'state'] = u'draft'
                # MODIFICATION END
                # allow the state to be changed
                context[u'allow_state_change'] = True

            data_dict[u'type'] = package_type
            context[u'message'] = data_dict.get(u'log_message', u'')
            pkg_dict = get_action(u'package_create')(context, data_dict)

            # MODIFICATION START
            # Add the ability to submit a package and save it without moving
            # on to the add resource screen.

            if request.form[u'save'] == 'save-and-finish':
                url = h.url_for(u'{}.read'.format(package_type),
                    id=pkg_dict[u'name'])
                return h.redirect_to(url)

            # MODIFICATION END

            elif ckan_phase:
                # redirect to add dataset resources
                url = h.url_for(
                    u'{}_resource.new'.format(package_type),
                    id=pkg_dict[u'name']
                )
                return h.redirect_to(url)

            return _form_save_redirect(
                pkg_dict[u'name'], u'new', package_type=package_type
            )
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized to read package'))
        except NotFound as e:
            return base.abort(404, _(u'Dataset not found'))
        except SearchIndexError as e:
            try:
                exc_str = text_type(repr(e.args))
            except Exception:  # We don't like bare excepts
                exc_str = text_type(str(e))
            return base.abort(
                500,
                _(u'Unable to add package to search index.') + exc_str
            )
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            if is_an_update:
                # we need to get the state of the dataset to show the stage we
                # are on.
                pkg_dict = get_action(u'package_show')(context, data_dict)
                data_dict[u'state'] = pkg_dict[u'state']
                return EditView().get(
                    package_type,
                    data_dict[u'id'],
                    data_dict,
                    errors,
                    error_summary
                )
            data_dict[u'state'] = u'none'
            return self.get(package_type, data_dict, errors, error_summary)