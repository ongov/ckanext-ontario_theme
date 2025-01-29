from ckan.logic import NotAuthorized, ValidationError
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.model as model
from ckan.common import g, request, _
from ckan.views.group import _get_group_template
import ckan.logic as logic

check_access = logic.check_access
get_action = logic.get_action

def index(group_type='organization', is_organization=True):
    '''Function from ckan.views.group modified to remove pagination
    and return all fields of organizations for easier multilingual sorting
    Specifically for organizations but can be reworked for both
    groups and organizations.'''
    extra_vars = {}
    page = h.get_page_number(request.params) or 1

    # context = {
    #     u'model': model,
    #     u'session': model.Session,
    #     u'user': g.user,
    #     u'for_view': True,
    #     u'with_private': False
    # }

    # This is the new context from ckan/views/groups.py
    context: Context = {
        u'user': current_user.name,
        u'for_view': True,
        u'with_private': False,
    }

    try:
        action_name = 'organization_list' if is_organization else 'group_list'
        check_access(action_name, context)
    except NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    q = request.params.get(u'q', u'')
    sort_by = request.params.get(u'sort')

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.q = q
    g.sort_by_selected = sort_by

    extra_vars["q"] = q
    extra_vars["sort_by_selected"] = sort_by

    # pass user info to context as needed to view private datasets of
    # orgs correctly
    # if g.userobj:
    #     context['user_id'] = g.userobj.id
    #     context['user_is_admin'] = g.userobj.sysadmin
    # This is the new check from ckan/views/groups.py
    if current_user.is_authenticated:
        context['user_id'] = current_user.id
        context['user_is_admin'] = current_user.sysadmin  # type: ignore

    try:
        data_dict_global_results = {
            u'all_fields': True,
            u'q': q,
            u'sort': sort_by,
            u'type': group_type or u'group',
            u'include_extras': True,
        }
        
        action_name = 'organization_list' if is_organization else 'group_list'
        global_results = get_action(action_name)(context,
                                                 data_dict_global_results)
    except ValidationError as e:
        if e.error_dict and e.error_dict.get(u'message'):
            msg = e.error_dict['message']
        else:
            msg = str(e)
        h.flash_error(msg)
        extra_vars["page"] = h.Page([], 0)
        extra_vars["group_type"] = group_type
        return base.render(
            _get_group_template(u'index_template', group_type), extra_vars)

    extra_vars["page"] = h.Page(
        collection=global_results,
        page=page,
        url=h.pager_url,
        items_per_page=len(global_results))

    extra_vars["page"].items = global_results
    extra_vars["group_type"] = group_type

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.page = extra_vars["page"]
    return base.render(
        _get_group_template(u'index_template', group_type), extra_vars)
