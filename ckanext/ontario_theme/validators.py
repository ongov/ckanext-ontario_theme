# -*- coding: utf-8 -*-

from pylons.i18n import _
from ckantoolkit import Invalid
import logging
import json
log = logging.getLogger(__name__)

def extract_fluent(value):
	try:
		check_value = json.loads(value)
		if isinstance(check_value, dict):
			return check_value
		else:
			return value		
	except:
		return value


def required_if(dependent_field, dependent_value):
    ''' require this field only if the dependent field has a certain value'''

    def callable(key, data, errors, context):
    	value = data.get(key)
    	check_value = extract_fluent(value)
    	if data.get((dependent_field,)) == dependent_value:
    		# is this a fluent field?
			if isinstance(check_value, dict):
				for fkey, fvalue in check_value.items():
					if not fvalue:
						raise Invalid(
		                	_(u'This is required'))    			
			else:
				if not check_value:
					raise Invalid(
		                _(u'This is required'))
        return

    return callable

def conditional_save(dependent_field, dependent_value):
    '''only save the value in this field if the dependent field has a certain value'''

    def callable(key, data, errors, context):
		if data.get((dependent_field,)) != dependent_value:
			data[key] = None     
		return

    return callable
