# -*- coding: utf-8 -*-

from pylons.i18n import _
from ckantoolkit import Invalid
from ckan.authz import is_sysadmin

import logging
log = logging.getLogger(__name__)

def __get_original_resource(context, data, key):
	'''
		Retrieves an original resource (before the form was submitted)
	'''

	resource_id_key = key[0:2] + (u'id',)
	resource_id = data.get(resource_id_key)
	if resource_id:
		model = context['model']
		session = context['session']
		original_resource = session.query(model.Resource).get(resource_id)
		return original_resource if original_resource else False	
	return False


def __is_public_resource(context, data, key):
	'''
		Determines whether a resource corresponds to a resource on the Ontario Data Catalogue
	'''

	original_resource = __get_original_resource(context, data, key)
	if original_resource:
		public_resource_id = original_resource.extras.get('public_resource_id', '')
		if public_resource_id:
			return True
	return False


def __is_public_record(context):
	'''
		Determines whether a package corresponds to a package on the Ontario Data Catalogue
	'''

	package = context.get('package')
	if package:
		public_catalogue_id = package.extras.get('public_catalogue_id', '')
		if public_catalogue_id:
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


def __change_submitted(key, data, context):
	'''
		determines whether a change for a package field has been submitted 
	'''

	package = context.get('package')
	if package:
		current = data.get(key, '')
		original = __get_value(key, package)
		if original != current:
			return True
	return False


def __resource_change_submitted(key, data, context):
	'''
		determines whether a change for a resource field has been submitted 
	'''

	# Get the right resource to check against
	original_resource = __get_original_resource(context, data, key)
	# if there is an original resource, then we can compare current against 
	if original_resource:
		current = data.get(key, '')
		original = __get_value(key[2:3], original_resource)
		if original != current:
			return True
	return False


def lock_if_public(key, data, errors, context):
	''' 
		Don't let the user change any of these values in the package if it has a public_catalogue_id 
	'''

	if __is_public_record(context) and __change_submitted(key, data, context) and not is_sysadmin(context['user']):
		raise Invalid(_(u'This is a public catalogue field and can\'t be changed.'))
	return


def lock_if_public_resource(key, data, errors, context):
	''' 
		Don't let the user change any of these values in the resource if it has a public_resource_id 
	'''
	log.info(__is_public_resource(context, data, key))
	log.info(__resource_change_submitted(key, data, context))
	log.info(not is_sysadmin(context['user']))
	if __is_public_resource(context, data, key) and __resource_change_submitted(key, data, context) and not is_sysadmin(context['user']):
		print("raise invalid")
		raise Invalid(_(u'This is a public catalogue field and can\'t be changed.'))
	return