# -*- coding: utf-8 -*-

from pylons.i18n import _
from ckantoolkit import Invalid

def __is_public_record(context):
	package = context.get('package')
	if package:
		public_catalogue_id = package.extras.get('public_catalogue_id', '')
		if public_catalogue_id:
			return True
	return False




def lock_if_public(key, data, errors, context):
	''' don't let the user change any of these values if the record has a public id '''
	if __is_public_record(context):
		raise Invalid(_(u'This is a public catalogue field and can\'t be changed.'))
	return
