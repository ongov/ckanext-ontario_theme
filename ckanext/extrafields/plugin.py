
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

def num_resources_filter_scrub(search_params):
    u'''Remove any quotes around num_resources value to enable prober filter
    query.

    This is an exact match for the fq filter range of `[1 TO *]`. This means
    it only works for the exact range I've set which is alright because I can
    still access 0 datasets (the opposite of what I've set) by using
    `?num_resources=0`.
    '''
    # Just a note: this was replacing any double quotes in 
    #       the value string so had to change back to exact match
    #       which isn't very re-usable. I started looking at splitting
    #       this out into a dict to loop over easily and find the match
    #       and just replace it but splitting on spaces also breaks things
    #       due to num_resources value.
    #       Issue came to light when filtering by licence and num_resources.
    #       This would remove results that should be visible (with licence
    #       and has resources).
    for (param, value) in search_params.items():
        if param == 'fq' and 'num_resources:"[' in value:
            v = value.replace('num_resources:"[1 TO *]"', 'num_resources:[1 TO *]')
            search_params[param] = v

    return search_params

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
        return num_resources_filter_scrub(search_params)

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