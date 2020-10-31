# -*- coding: utf-8 -*-

import re
from ckan.common import _
from ckantoolkit import Invalid
from ckanext.scheming.validation import scheming_validator
from ckanext.fluent.validators import fluent_text_output

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