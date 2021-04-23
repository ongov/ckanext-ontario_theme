# -*- coding: utf-8 -*-

import re
from ckan.common import _
from ckantoolkit import Invalid
from ckanext.scheming.validation import scheming_validator
from ckanext.fluent.validators import fluent_text_output
from pylons.i18n import _
from ckantoolkit import Invalid
from ckan.authz import is_sysadmin
import json


def tag_name_validator(value, context):
    '''
        Replaces core tag_name_validator to make the following changes:
        - strip tag
        - replace non-space separators with space separators
        - throw a specific exception when commas are included
        - throw a specific exception when double-spaces are included
        - allows apostrophes ' and ’

    '''
    value = value.strip()

    # replace any other separators with a space
    separator_search = re.compile(ur'[\s]', re.UNICODE)
    value = separator_search.sub(" ", value)

    if u',' in value:
        raise Invalid(_(u'Tag "%s" may not contain commas') % (value))
    if u'  ' in value:
        raise Invalid(
            _(u'Tag "%s" may not contain consecutive spaces') % (value))

    # same as core tag_name_validator except for the addition of ' and ’
    tagname_match = re.compile(ur'[\w ’\'\-.]*$', re.UNICODE)

    if not tagname_match.match(value):
        raise Invalid(_(u'Tag "%s" must be alphanumeric '
                        u'characters or symbols: ’\'-_.') % (value))
    return value

def exemption_validator(key, data, errors, context):
    '''
        If access level is restricted then an exemption must be selected
    '''

    if data[('access_level'),] == 'restricted' and data[key] == '':
        raise Invalid('Exemption must be specified if access is Restricted')


@scheming_validator
def ontario_theme_copy_fluent_keywords_to_tags(field, schema):
    def validator(key, data, errors, context):
        """
        Copy keywords to tags.
        This will let the tag autocomplete endpoint to work as desired.

        Fluent tag validation and CKAN's tag validation handles validation.

        This replaces tags with the keywords for all languages in the schema
        so it will remove (deactivate) tags as necessary as well.

        This validator is dependent on scheming and fluent.

        Usage:
        "validators": "fluent_tags ontario_theme_copy_fluent_keywords_to_tags",
        """

        fluent_tags = fluent_text_output(data[key])
        data[('tags'),] = []
        for key, value in fluent_tags.items():
            for tag in value:
                data[('tags'),].append(
                    {'name': tag}
                )

    return validator


def __lock_value(value, original_value):
    '''
        compares two values
    '''

    # avoid mismatches due to extra spaces, etc
    if type(value) == str:
        value = value.strip().replace("\r\n", "\n")
    if type(original_value) == str:
        original_value = original_value.strip().replace("\r\n", "\n")
    if value != original_value:
        return False
    return True

def __add_error_message(errors, key, message):
    '''
        adds error messages to error dict
    '''

    if key not in errors:
        errors[key] = []
    errors[key].append(message)
    return errors

def __check_all_values(key, value, original_value, errors, message, sub_validator):
    '''
        Adds error for fluent and non-fluent fields
    '''

    try:
        check_value = json.loads(value)
        original_value = json.loads(original_value)
        if isinstance(check_value, dict):
            for fkey, fvalue in check_value.items():
                if fkey not in original_value:
                    original_value[fkey] = ""
                if not sub_validator(fvalue, original_value[fkey]):
                    errors = __add_error_message(errors, (key[:-1] + (key[-1] + '-' + fkey,)), message)
        else:
            if not sub_validator(value, original_value):
                errors = __add_error_message(errors, key, message)
    except:
        if not sub_validator(value, original_value):
            errors = __add_error_message(errors, key, message)

    return errors

def __is_public_record(context):
    '''
        Determines whether a package corresponds to a package on the Ontario Data Catalogue
    '''

    package = context.get('package')
    if package:
        harvester_id = package.extras.get('harvester', '')
        if harvester_id == "ontario-data-catalogue":
            return True
    return False


def __get_value(key, original_values):
    '''
        gets the value from the package or resource whether or not it's an extra or not
    '''

    #check if the key is present in the package/resource
    if hasattr(original_values, key[0]):
        return getattr(original_values, key[0])
    #if not, check in extras
    else:
        return original_values.extras.get(key[0], '')


def __if_change_submitted(key, data, context, errors, message):
    '''
        determines whether a change for a package field has been submitted 
    '''

    package = context.get('package')
    if package:
        current = data.get(key, '')
        original = __get_value(key, package)
        # now we have to run each value (fluent or not, through the validator and add errors)
        errors = __check_all_values(key, current, original, errors, message, __lock_value)

    return errors


def lock_if_odc(key, data, errors, context):
    ''' 
        Don't let the user change any of these values in the package if it has a public_catalogue_id 
    '''

    if __is_public_record(context) and not is_sysadmin(context['user']):
        errors = __if_change_submitted(key, data, context, errors, _(u'This is a public catalogue field and can\'t be changed.')) or errors
    return
