# -*- coding: utf-8 -*-

from pylons.i18n import _
from ckantoolkit import Invalid
import logging
import json
log = logging.getLogger(__name__)

def has_missing_value(value):
	try:
		check_value = json.loads(value)
		if isinstance(check_value, dict):
			for fkey, fvalue in check_value.items():
				if not fvalue:
					return True
		else:
			if not value:
				return True	
	except:
		if not value:
			return True
	return False


def required_if(dependent_field, dependent_value):
    ''' require this field only if the dependent field has a certain value'''

    def callable(key, data, errors, context):
    	value = data.get(key)
    	
    	if data.get((dependent_field,)) == dependent_value:
    		if has_missing_value(value):
    			raise Invalid(_(u'This is required'))
    			#errors[key].append(_(u'This is required'))  			
    return callable

def conditional_save(dependent_field, dependent_value):
    '''only save the value in this field if the dependent field has a certain value'''

    def callable(key, data, errors, context):
		if data.get((dependent_field,)) != dependent_value:
			data[key] = None     
		return

    return callable
