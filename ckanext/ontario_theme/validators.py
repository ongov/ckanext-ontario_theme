# -*- coding: utf-8 -*-

def tag_name_validator(value, context):
    import re
    from ckan.common import _

    value = value.strip()

    if u',' in value:
        raise Invalid(_(u'Tag "%s" may not contain commas') % (value,))
    if u'  ' in value:
        raise Invalid(
            _(u'Tag "%s" may not contain consecutive spaces') % (value,))

    tagname_match = re.compile(ur'[\w \’\'\-.]*$', re.UNICODE)

    if not tagname_match.match(value):
        raise Invalid(_('Tag "%s" must be alphanumeric '
                        'characters or symbols: \'’-_.') % (value))
    return value