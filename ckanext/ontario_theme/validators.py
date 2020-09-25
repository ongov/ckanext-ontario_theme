# -*- coding: utf-8 -*-

from pylons.i18n import _
from ckantoolkit import Invalid
from ckan.authz import is_sysadmin

import logging
log = logging.getLogger(__name__)

def __is_public_record(context):
	package = context.get('package')
	if package:
		public_catalogue_id = package.extras.get('public_catalogue_id', '')
		if public_catalogue_id:
			return True
	return False

# gets the value from the package or resource whether or not it's an extra or not
def __get_value(key, original_values):
	#check if the key is present in the package/resource
    if hasattr(original_values, key[0]):
        return getattr(original_values, key[0])
	#if not, check in extras
    else:
        return original_values.extras.get(key[0], '')


def __change_submitted(key, data, context):
	package = context.get('package')
	if package:
		current = data.get(key, '')
		original = __get_value(key, package)
		if original != current:
			return True
	return False


def lock_if_public(key, data, errors, context):
	''' don't let the user change any of these values if the record has a public id '''
	if __is_public_record(context) and __change_submitted(key, data, context) and not is_sysadmin(context['user']):
		raise Invalid(_(u'This is a public catalogue field and can\'t be changed.'))
	return
