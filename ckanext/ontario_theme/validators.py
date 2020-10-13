# -*- coding: utf-8 -*-

import re
from ckan.common import _
from ckantoolkit import Invalid

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
                        'characters or symbols: \'-_.') % (value))
    return value