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
            'custom_text': [toolkit.get_validator('ignore_missing'),
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
