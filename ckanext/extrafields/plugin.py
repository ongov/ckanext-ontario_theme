
# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.plugins.toolkit import Invalid
import datetime

# Custome Validators

def update_frequency_validator(value):
    try:
        value = value.lower()
    except:
        raise Invalid('Invalid update frequency input value, must be string')
    if value not in ['as_required',
                     'biannually',
                     'current',
                     'daily',
                     'historical',
                     'monthly',
                     'never',
                     'on_demand',
                     'other',
                     'periodically',
                     'quarterly',
                     'weekly',
                     'yearly']:
        raise Invalid('Invalid update frequency input value')
    return value

def access_level_validator(value):
    try:
        value = value.lower()
    except:
        raise Invalid('Invalid access level input value, must be string')
    if value not in ['open',
                     'restricted',
                     'to_be_opened',
                     'under_review']:
        raise Invalid('Invalid access level input value')
    return value

def exemption_validator(value):
    if value == '':
      return 'none'
    try:
        value = value.lower()
    except:
      raise Invalid('Invalid access level input value, must be string')
    if value not in ['commercial_sensitivity',
                     'confidentiality',
                     'legal_and_contractual_obligations',
                     'none',
                     'privacy',
                     'security']:
        raise Invalid('Invalid exemption input value')
    return value

def date_validator(value):
    '''Create custom date_validator that modifies the existing 
    validation for isodate. The original throws errors when 
    trying to use with extra_fields and date inputs and the api.
    This seemed to be appropriate solution.
    There was a little mention of this on github but nothing solid.
    '''
    if value == '':
        return None
    try:
        datetime.datetime.strptime(value, '%Y-%m-%d')
    except:
        raise Invalid('Date format incorrect, should be YYYY-MM-DD')
    return value

class ExtrafieldsPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IConfigurer)

    # IConfigurer

    def update_config(self, config_):
        # Add plugin's template directory to CKAN's extra_template_paths
        # to use the new templates.
        toolkit.add_template_directory(config_, 'templates')
        # toolkit.add_public_directory(config_, 'public')
        # toolkit.add_resource('fanstatic', 'extrafields')

    # IDatasetForm

    def _modify_package_schema(self, schema):
        # Custom fields for update and create of packages.
        schema.update({
            # TODO: Look into issues with using is_positive_integer validator. 
            #       When it's missing its still triggered.
            'node_id': [toolkit.get_validator('ignore_missing'),
                        toolkit.get_validator('int_validator'),
                        toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'technical_title': [toolkit.get_validator('ignore_missing'),
                                toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'short_description': [toolkit.get_validator('ignore_missing'),
                                  toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'maintainer_branch': [toolkit.get_validator('ignore_missing'),
                                  toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'data_range_start': [toolkit.get_validator('ignore_missing'),
                                 date_validator,
                                 toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'data_range_end': [toolkit.get_validator('ignore_missing'),
                               date_validator,
                               toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'data_birth_date': [toolkit.get_validator('ignore_missing'),
                                date_validator,
                                toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'contains_geographic_markers': [toolkit.get_validator('ignore_missing'),
                                            toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'geographic_coverage': [toolkit.get_validator('ignore_missing'),
                                    toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'update_frequency': [toolkit.get_validator('ignore_missing'),
                                 update_frequency_validator,
                                 toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'access_level': [toolkit.get_validator('ignore_missing'),
                             access_level_validator,
                             toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'exemption': [toolkit.get_validator('ignore_missing'),
                          exemption_validator,
                          toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'exemption_rationale': [toolkit.get_validator('ignore_missing'),
                                    toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'comments': [toolkit.get_validator('ignore_missing'),
                         toolkit.get_converter('convert_to_extras')]
        })
        return schema

    def create_package_schema(self):
        # Get the default schema.
        schema = super(ExtrafieldsPlugin, self).create_package_schema()
        # Add custom field(s).
        schema = self._modify_package_schema(schema)
        return schema

    def update_package_schema(self):
        # Get the default schema.
        schema = super(ExtrafieldsPlugin, self).update_package_schema()
        # Add custom field(s).
        schema = self._modify_package_schema(schema)
        return schema

    def show_package_schema(self):
        schema = super(ExtrafieldsPlugin, self).show_package_schema()
        schema.update({
            'node_id': [toolkit.get_converter('convert_from_extras'),
                        toolkit.get_validator('ignore_missing'),
                        toolkit.get_validator('int_validator')]
        })

        schema.update({
            'technical_title': [toolkit.get_converter('convert_from_extras'),
                                toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'short_description': [toolkit.get_converter('convert_from_extras'),
                                  toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'maintainer_branch': [toolkit.get_converter('convert_from_extras'),
                                  toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'data_range_start': [toolkit.get_converter('convert_from_extras'),
                                 date_validator,
                                 toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'data_range_end': [toolkit.get_converter('convert_from_extras'),
                               date_validator,
                               toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'data_birth_date': [toolkit.get_converter('convert_from_extras'),
                                date_validator,
                                toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'contains_geographic_markers': [toolkit.get_converter('convert_from_extras'),
                                            toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'geographic_coverage': [toolkit.get_converter('convert_from_extras'),
                                    toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'update_frequency': [toolkit.get_converter('convert_from_extras'),
                                 update_frequency_validator,
                                 toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'access_level': [toolkit.get_converter('convert_from_extras'),
                             access_level_validator,
                             toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'exemption': [toolkit.get_converter('convert_from_extras'),
                          exemption_validator,
                          toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'exemption_rationale': [toolkit.get_converter('convert_from_extras'),
                                    toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'comments': [toolkit.get_converter('convert_from_extras'),
                         toolkit.get_validator('ignore_missing')]
        })
        return schema

    def is_fallback(self):
       # Register as default this plugin as the default handler for
       # packages not handled by other IDatasetForm plugins.
       return True

    def package_types(self):
        # Register as the default for all package types.
        # e.g. package type is none so go to default (above).
        return []
