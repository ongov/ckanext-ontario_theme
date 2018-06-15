
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

    def _modify_package_schema(self, schema):
        # Custom fields for update and create of packages.
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
                                 toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'data_range_end': [toolkit.get_validator('ignore_missing'),
                               toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'data_birth_date': [toolkit.get_validator('ignore_missing'),
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
                                 toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'access_level': [toolkit.get_validator('ignore_missing'),
                             toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'exemption': [toolkit.get_validator('ignore_missing'),
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
                                 toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'data_range_end': [toolkit.get_converter('convert_from_extras'),
                               toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'data_birth_date': [toolkit.get_converter('convert_from_extras'),
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
                                 toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'access_level': [toolkit.get_converter('convert_from_extras'),
                             toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'exemption': [toolkit.get_converter('convert_from_extras'),
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
