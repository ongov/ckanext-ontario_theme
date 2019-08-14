import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.plugins import DefaultTranslation
from ckan.common import config

from flask import Blueprint, make_response
from flask import render_template, render_template_string

import ckanapi_exporter.exporter as exporter

from ckan.model import Package

from resource_upload import ResourceUpload

import logging
log = logging.getLogger(__name__)

def help():
    '''New help page for site.
    '''
    return render_template('home/help.html')


def csv_dump():
    '''The pattern allows you to go deeper into the nested structures.
    `["^title_translated$", "en"]` grabs the english title_translated value.
    It doesn't seem to handle returning a dict such as
    `{'en': 'english', 'fr': 'french'}`.
    Exporting resource metadata is limited. It combines resource values
    into single comma seperated string.
    deduplicate needed to be "true" not true.
    '''
    columns = {
                "Title EN": {
                    "pattern": ["^title_translated$", "^en$"]
                },
                "Title FR": {
                    "pattern": ["^title_translated$", "^fr$"]
                },
                "Notes EN": {
                    "pattern": ["^notes_translated$", "^en$"]
                },
                "Notes FR": {
                    "pattern": ["^notes_translated$", "^fr$"]
                },
                "Met Service Standard": {
                    "pattern": "^met_service_standard$"
                },
                "License Title": {
                    "pattern": "^license_title$"
                },
                "Technical Documents": {
                    "pattern": "^technical_documents$"
                },
                "Contains geopgrapic markers": {
                    "pattern": "^contains_geographic_markers$"
                },
                "Maintainer Branch EN": {
                    "pattern": ["^maintainer_branch$", "^en$"]
                },
                "Maintainer Branch FR": {
                    "pattern": ["^maintainer_branch$", "^fr$"]
                },
                "Keywords EN": {
                    "pattern": ["^keywords$", "^en$"]
                },
                "Keywords FR": {
                    "pattern": ["^keywords$", "^fr$"]
                },
                "Broken Links": {
                    "pattern": "^broken_links$"
                },
                "Id": {
                    "pattern": "^id$"
                },
                "Metadata Created": {
                    "pattern": "^metadata_created$"
                },
                "Open Access": {
                    "pattern": "^open_access$"
                },
                "Removed": {
                    "pattern": "^removed$"
                },
                "Metadata Modified": {
                    "pattern": "^metadata_modified$"
                },
                "Meets Update Frequency": {
                    "pattern": "^meets_update_frequency$"
                },
                "Comments EN": {
                    "pattern": ["^comments$", "^en$"]
                },
                "Comments FR": {
                    "pattern": ["^comments$", "^fr$"]
                },
                "Access Level": {
                    "pattern": "^access_level$"
                },
                "Data Range End": {
                    "pattern": "^data_range_end$"
                },
                "Exemption Rationale EN": {
                    "pattern": ["^exemption_rationale$", "^en$"]
                },
                "Exemption Rationale FR": {
                    "pattern": ["^exemption_rationale$", "^fr$"]
                },
                "Issues": {
                    "pattern": "^issues$"
                },
                "Short Description EN": {
                    "pattern": ["^short_description$", "^en$"]
                },
                "Short Description FR": {
                    "pattern": ["^short_description$", "^fr$"]
                },
                "Type": {
                    "pattern": "^type$"
                },
                "Resources Format": {
                    "pattern": ["^resources$", "^format$"],
                    "deduplicate": "true"
                },
                "Num Resources": {
                    "pattern": "^num_resources$"
                },
                "Tags": {
                    "pattern": ["^tags$", "^name$"],
                    "deduplicate": "true"
                },
                "Data Range Start": {
                    "pattern": "^data_range_start$"
                },
                "State": {
                    "pattern": "^state$"
                },
                "License Id": {
                    "pattern": "^license_id$"
                },
                "Exemption": {
                    "pattern": "^exemption$"
                },
                "Submission Comments EN": {
                    "pattern": ["^submission_comments$", "^en$"]
                },
                "Submission Comments FR": {
                    "pattern": ["^submission_comments$", "^fr$"]
                },
                "Geographic Coverage EN": {
                    "pattern": ["^geographic_coverage$", "^en$"]
                },
                "Geographic Coverage FR": {
                    "pattern": ["^geographic_coverage$", "^fr$"]
                },
                "Rush": {
                    "pattern": "^rush$"
                },
                "Organization Title": {
                    "pattern": ["^organization$", "^title$"]
                },
                "Submission Communication Plan EN": {
                    "pattern": ["^submission_communication_plan$", "^en$"]
                },
                "Submission Communication Plan FR": {
                    "pattern": ["^submission_communication_plan$", "^fr$"]
                },
                "Name": {
                    "pattern": "^name$"
                },
                "Is Open": {
                    "pattern": "^isopen$"
                },
                "URL": {
                    "pattern": "^url$"
                },
                "Technical Title EN": {
                    "pattern": ["^technical_title$", "^en$"]
                },
                "Technical Title FR": {
                    "pattern": ["^technical_title$", "^fr$"]
                },
                "Node Id": {
                    "pattern": "^node_id$"
                },
                "Removal Rationale EN": {
                    "pattern": ["^removal_rationale$", "^en$"]
                },
                "Removal Rationale FR": {
                    "pattern": ["^removal_rationale$", "^fr$"]
                },
                "Update Frequency": {
                    "pattern": "^update_frequency$"
                }
              }

    site_url = config.get('ckan.site_url')
    csv_string = exporter.export(site_url, columns)
    resp = make_response(csv_string, 200)
    resp.headers['Content-Type'] = b'text/csv; charset=utf-8'
    resp.headers['Content-disposition'] = \
        (b'attachment; filename="output.csv"')
    return resp


def get_license(license_id):
    '''Helper to return license based on id.
    '''
    return Package.get_license_register().get(license_id)


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


class OntarioThemePlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IUploader, inherit=True)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IFacets)
    plugins.implements(plugins.IPackageController)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'ontario_theme')
        # Uncomment these to use bootstrap 2 theme and comment out
        # the above template and resource directories.
        # toolkit.add_template_directory(config_, 'templates-bs2')
        # toolkit.add_resource('fanstatic-bs2', 'ontario_theme')

    # ITemplateHelpers

    def get_helpers(self):
        return {'ontario_theme_get_license': get_license,
                'extrafields_default_locale': default_locale}

    # IBlueprint

    def get_blueprint(self):
        '''Return a Flask Blueprint object to be registered by the app.
        '''

        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates'
        # Add url rules to Blueprint object.
        rules = [
            (u'/help', u'help', help),
            (u'/dataset/csv_dump', u'csv_dump', csv_dump)
        ]
        for rule in rules:
            blueprint.add_url_rule(*rule)

        return blueprint

    # IUploader

    def get_resource_uploader(self, data_dict):
        return ResourceUpload(data_dict)

    # IDatasetForm

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []

    # IFacets

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

    # IPackageController

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
