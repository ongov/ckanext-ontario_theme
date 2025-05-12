from six.moves import zip_longest

from flask import Blueprint
from flask.views import MethodView

import ckan.lib.navl.dictization_functions as dict_fns
from ckan.logic import (
    tuplize_dict,
    parse_params,
)
from ckan.plugins.toolkit import (
    ObjectNotFound,
    NotAuthorized,
    get_action,
    _,
    request,
    abort,
    render,
    c,
    h,
)
import copy
from .plugin_for_validation import reformat_ui_dict

datastore = Blueprint("datastore", __name__)


class DictionaryView(MethodView):

    def _prepare(self, id, resource_id):
        # resource_edit_base template uses these
        pkg_dict = get_action("package_show")(None, {"id": id})
        resource = get_action("resource_show")(None, {"id": resource_id})
        try:
            rec = get_action("datastore_search")(
                None, {"resource_id": resource_id, "limit": 0}
            )
            return {
                "pkg_dict": pkg_dict,
                "resource": resource,
                "fields": [f for f in rec["fields"] if not f["id"].startswith("_")],
            }

        except ObjectNotFound:
            return {
                "pkg_dict": pkg_dict,
                "resource": resource,
            }
        except NotAuthorized:
            abort(404, _("Resource not found"))

    def get(self, id, resource_id):
        """Data dictionary view: show field labels and descriptions"""

        data_dict = self._prepare(id, resource_id)

        # global variables for backward compatibility
        c.pkg_dict = data_dict["pkg_dict"]
        c.resource = data_dict["resource"]

        return render("datastore/dictionary.html", data_dict)

    def post(self, id, resource_id):
        """Data dictionary view: edit field labels and descriptions"""
        data_dict = self._prepare(id, resource_id)
        fields = data_dict["fields"]
        data = dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
        info = data.get("info")
        if not isinstance(info, list):
            info = []
        info = info[: len(fields)]
        # create dictionary outside of datastore_create
        # use a copy of dictionary['fields'] for ui_dict to be reformated
        dict_fields = {
            "fields": [
                {
                    "id": f["id"],
                    "type": f["type"],
                    "info": fi if isinstance(fi, dict) else {},
                }
                for f, fi in zip_longest(fields, info)
            ]
        }
        try:
            has_override = True if [x for x in dict_fields['fields'] if len(x['info']['type_override'])>0] else False
            if has_override:
                # Reformat dictionary into structure used by ckanext-validation and
                # replace PostgreSQL data types with Frictionless equivalents
                ui_dict_fields = copy.deepcopy(dict_fields)
                ui_dict = reformat_ui_dict(ui_dict_fields["fields"])
                for row in dict_fields["fields"]:
                    if "info" in row:
                        col_name = row["id"]
                        row["info"]["frictionless_dict"] = [
                            item for item in ui_dict["fields"] if item.get("name") == col_name
                        ]
                # Push the Frictionless data dictionary to database so that
                # ckanext-validation can retrieve it in _run_sync_validation (logic.py)
                get_action("datastore_create")(
                    None,
                    {
                        "resource_id": resource_id,
                        "force": True,
                        "fields": dict_fields.get("fields"),
                    },
                )
                # Trigger ckanext-validation
                get_action("resource_validation_run")(
                    {"ignore_auth": True},
                    {"resource_id": resource_id, "async": False, "ui_dict": ui_dict},
                )
                # Get status of validation to submit
                # to xloader when status is successful
                status = get_action(u"resource_validation_show")(
                    {u'ignore_auth': True},
                    {u"resource_id": resource_id}
                )
                if status['status'] == 'success':
                    get_action("xloader_submit")(
                        None,
                        {"resource_id": resource_id, "ignore_hash": False}
                    )
                    return h.redirect_to("ontario_theme.new_resource_publish", id=id, resource_id=resource_id)
                elif not status:
                    return h.redirect_to("ontario_theme.new_resource_publish", id=id, resource_id=resource_id)
                else:
                    return h.redirect_to("datastore.dictionary", id=id, resource_id=resource_id)
        except:
            return h.redirect_to("ontario_theme.new_resource_publish", id=id, resource_id=resource_id)
