# -*- coding: utf-8 -*-

import re
from ckan.common import _
from ckantoolkit import Invalid

def tag_name_validator(value, context):
    value = value.strip()

    if u',' in value:
        raise Invalid(_(u'Tag "%s" may not contain commas') % (value,))
    if u'  ' in value:
        raise Invalid(
            _(u'Tag "%s" may not contain consecutive spaces') % (value,))

    tagname_match = re.compile(ur'[\w ’\'\-.]*$', re.UNICODE)

    if not tagname_match.match(value):
        raise Invalid(_(u'Tag "%s" must be alphanumeric '
                        'characters or symbols: \'-_.') % (value))
    return value