
# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import config
import logging
log = logging.getLogger(__name__)

def default_locale():
    '''Wrap the ckan default locale in a helper function to access
    in templates.
    Returns 'en' by default.
    :rtype: string
    '''
    value = config.get('ckan.locale_default', 'en')
    return value

class ExtrafieldsPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IFacets)
    plugins.implements(plugins.IPackageController)

    def get_helpers(self):
        '''Register the helper to access the default local.
        '''
        return {'extrafields_default_locale': default_locale}

    # IConfigurer

    def update_config(self, config_):
        # Add plugin's template directory to CKAN's extra_template_paths
        # to use the new templates.
        toolkit.add_template_directory(config_, 'templates')
        # toolkit.add_public_directory(config_, 'public')
        # toolkit.add_resource('fanstatic', 'extrafields')

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []        

    def dataset_facets(self, facets_dict, package_type):
        '''Add new search facet (filter) for datasets.
        '''
        facets_dict['access_level'] = toolkit._('Access Level')
        facets_dict['update_frequency'] = toolkit._('Update Frequency')
        facets_dict['num_resources'] = toolkit._('Number of Resources (data)')
        return facets_dict

    def group_facets(self, facets_dict, group_type, package_type):
        u'''Modify and return the ``facets_dict`` for a group's page.
        Throws AttributeError: no attribute 'organization_facets' without function.
        '''
        facets_dict['access_level'] = toolkit._('Access Level')
        facets_dict['update_frequency'] = toolkit._('Update Frequency')
        return facets_dict

    def organization_facets(self, facets_dict, organization_type, package_type):
        u'''Modify and return the ``facets_dict`` for an organization's page.
        Throws AttributeError: no attribute 'organization_facets' without function.
        '''
        facets_dict['access_level'] = toolkit._('Access Level')
        facets_dict['update_frequency'] = toolkit._('Update Frequency')
        return facets_dict

    def before_search(self, search_params):
        u'''Extensions will receive a dictionary with the query parameters,
        and should return a modified (or not) version of it.
        '''
        log.error(search_params)
        for (param, value) in search_params.items():
            if param == 'fq' and 'num_resources:"[' in value:
                v = value.replace('"', '')
                search_params[param] = v

        log.error(search_params)
        return search_params

    def after_search(self, search_results, search_params):
        return search_results

    def before_index(self, pkg_dict):
        return pkg_dict

    def before_view(self, pkg_dict):
        return pkg_dict

    def read(self, entity):
        return entity

    def create(self, entity):
        return entity

    def edit(self, entity):
        return entity

    def delete(self, entity):
        return entity

    def after_create(self, context, pkg_dict):
        return pkg_dict

    def after_update(self, context, pkg_dict):
        return pkg_dict

    def after_delete(self, context, pkg_dict):
        return pkg_dict

    def after_show(self, context, pkg_dict):
        return pkg_dict