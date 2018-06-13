# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


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

    def create_package_schema(self):
        # Get the default schema.
        schema = super(ExtrafieldsPlugin, self).create_package_schema()
        # Add custom field(s).
        schema.update({
            'other_title': [toolkit.get_validator('ignore_missing'),
                            toolkit.get_converter('convert_to_extras')]
        },
        {
            'short_description': [toolkit.get_validator('ignore_missing'),
                                  toolkit.get_converter('convert_to_extras')]
        },
        {
            'maintainer_branch': [toolkit.get_validator('ignore_missing'),
                                  toolkit.get_converter('convert_to_extras')]
        },
        {
            'data_range_start': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
        },
        {
            'data_range_end': [toolkit.get_validator('ignore_missing'),
                               toolkit.get_conveter('convert_to_extras')]
        },
        {
            'data_birth_date': [toolkit.get_validator('ignore_missing'),
                                toolkit.get_converter('convert_to_extras')]
        },
        {
            'contains_geographic_markers': [toolkit.get_validator('ignore_missing'),
                                            toolkit.get_converter('convert_to_extras')]
        },
        {
            'geographic_coverage': [toolkit.get_validator('ignore_missing'),
                                    toolkit.get_converter('convert_to_extras')]
        },
        {
            'update_frequency': [toolkit.get_validator('ignore_missing'),
                                 toolkit.get_converter('convert_to_extras')]
        },
        {
            'access_level': [toolkit.get_validator('ignore_missing'),
                             toolkit.get_converter('convert_to_extras')]
        },
        {
            'exemption': [toolkit.get_validator('ignore_missing'),
                          toolkit.get_converter('convert_to_extras')]
        },
        {
            'exemption_rationale': [toolkit.get_validator('ignore_missing'),
                                    toolkit.get_converter('convert_to_extras')]
        },
        {
            'comments': [toolkit.get_validator('ignore_missing'),
                         toolkit.get_converter('convert_to_extras')]
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
