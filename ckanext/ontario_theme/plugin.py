import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.plugins import DefaultTranslation
from ckan.common import config, request, g, _

from flask import Blueprint, make_response
from flask import render_template, render_template_string

import ckanapi_exporter.exporter as exporter
import json

from ckan.model import Package
import ckan.model as model

from resource_upload import ResourceUpload

# For Image Uploader
from ckan.controllers.home import CACHE_PARAMETERS
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import os
import ckan.lib.uploader as uploader
import ckan.lib.helpers as h

import logging
log = logging.getLogger(__name__)

def image_uploader():
    '''View function that renders the image uploader form.
    Passes `'image_url': 'submitted-image-path'` and `'uploads': {'path',}'`
    to template.
    '''
    try:
        uploads_with_path = []
        try:
            # Get all the images from the home uploader.
            path = uploader.get_storage_path()
            storage_path = os.path.join(path,
                                        'storage',
                                        'uploads',
                                        'home')
            uploads = sorted(os.listdir(storage_path))

            # Build the static content paths for each image.
            for upload in uploads:
                image_path = 'uploads/home/'
                value = h.url_for_static('{0}{1}'.format(image_path, upload))
                uploads_with_path.append(value)
        except OSError:
            log.error("The uploads directory does not exist yet. Upload an image.")

        # This is somewhat odd, toolkit.render calls flask.render_template.
        # But toolkit.render unpacks the args properly to access them in the
        # template without needing 'extra_vars["data"]'. Lots of time trouble
        # shooting to get this combo working.
        return toolkit.render('admin/ontario_theme_image_uploader.html',
                              extra_vars={
                                  'data': {},
                                  'errors': {},
                                  'image_url': request.args.get("image_url", ''),
                                  'uploads': uploads_with_path
                              })
    except Exception as e:
        log.error(e)


def image_uploaded():
    '''View function to handle uploading arbitrary images for the home page.
    Passes `'image_url': 'submitted-image-path'` to template/view function.
    '''
    data_dict = {}
    try:
        # Cleanup the data_dict for the uploader.
        req = request.form.copy()
        req.update(request.files.to_dict())
        data_dict = logic.clean_dict(
            dict_fns.unflatten(
                logic.tuplize_dict(
                    logic.parse_params(req,
                                       ignore_keys=CACHE_PARAMETERS))))

        # Upload the image.
        upload = uploader.get_uploader('home')
        upload.update_data_dict(data_dict, 'image_url',
                                'image_upload', 'clear_upload')
        upload.upload(uploader.get_max_image_size())

        image_url = ''
        # Build and return the image url.
        for key, value in data_dict.iteritems():
            if key == 'image_url' and value and not value.startswith('http')\
                    and not value.startswith('/'):
                image_path = 'uploads/home/'
                value = h.url_for_static('{0}{1}'.format(image_path, value))
                image_url = value
    except Exception as e:
        log.error(e)
    return h.redirect_to(u'ontario_theme.image_uploader', image_url=image_url)
# Had to add the extra options for methods here instead of in the blueprint add_url_rule to avoid invalid syntax error.
# See https://flask.palletsprojects.com/en/1.1.x/api/#view-function-options
image_uploaded.methods = ['POST', 'OPTIONS']


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


def get_package_keywords(language='en'):
    '''Helper to return a list of the top 3 keywords based on specified
    language.

    List structure matches the get_facet_items_dict() helper which doesn't
    load custom facets on the home page.
    [{
        'count': 1,
        'display_name': u'English Tag',
        'name': u'English Tag'
    },
    {
        'count': 1,
        'display_name': u'Second Tag',
        'name': u'Second Tag'
    }]
    '''
    facet = "keywords_{}".format(language)
    package_top_keywords = toolkit.get_action('package_search')(
        data_dict={'facet.field': [facet],
                   'facet.limit': 3,
                   'rows': 0})
    package_top_keywords = package_top_keywords['search_facets'][facet]['items']
    return package_top_keywords


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


def home_block(block='one'):
    '''Helper to make the new configuration available to templates.
    Returns the configuration or empty string for the specified home block
    markdown content. Defaults to English but returns french if language is
    french.
    '''
    value = config.get('ckanext.ontario_theme.home_block_{}-en'.format(block), '')
    if h.lang() == 'fr':
        value = config.get('ckanext.ontario_theme.home_block_{}-fr'.format(block), '')
    return value


def home_block_image(block='one'):
    '''Helper to make the new configuration available to templates.
    Returns the configuration or empty string for the specified home block
    image path.
    '''
    value = config.get('ckanext.ontario_theme.home_block_{}_image'.format(block), '')
    return value


def home_block_link(block='one'):
    '''Helper to make the new configuraiton avialable to templates. Returns
    the configuraiton or empty string for the specified home block link.
    Defaults to English but returns french if language is french.
    '''
    value = config.get('ckanext.ontario_theme.home_block_{}_link-en'.format(block), '')
    if h.lang() == 'fr':
        value = config.get('ckanext.ontario_theme.home_block_{}_link-fr'.format(block), '')
    return value


class OntarioThemeExternalPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IConfigurer)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates/external')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic/external', 'ontario_theme_external')

        config_['scheming.dataset_schemas'] = """
ckanext.ontario_theme:schemas/external/ontario_theme_dataset.json
"""
        config_['scheming.presets'] = """
ckanext.scheming:presets.json
ckanext.fluent:presets.json
"""

        config_['scheming.organization_schemas'] = """
ckanext.ontario_theme:schemas/ontario_theme_organization.json
"""


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
        toolkit.add_template_directory(config_, 'templates/internal')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic/internal', 'ontario_theme')

        if 'scheming.dataset_schemas' not in config_:
            config_['scheming.dataset_schemas'] = """
ckanext.ontario_theme:schemas/internal/ontario_theme_dataset.json
"""
        config_['scheming.presets'] = """
ckanext.scheming:presets.json
ckanext.fluent:presets.json
"""

        config_['scheming.organization_schemas'] = """
ckanext.ontario_theme:schemas/ontario_theme_organization.json
"""

    def update_config_schema(self, schema):
        '''Add's new fields to the schema for run-time editable configuration
        options.
        '''
        ignore_missing = toolkit.get_validator('ignore_missing')
        # Added piece of mind.
        ignore_not_sysadmin = toolkit.get_validator('ignore_not_sysadmin')
        unicode_safe = toolkit.get_validator('unicode_safe')
        # Remove leading and trailing whitespace.
        remove_whitespace = toolkit.get_converter('remove_whitespace')

        schema.update({
            # Custom configuration options for home page content.
            'ckanext.ontario_theme.home_block_one-en':      [ignore_missing,
                                                             ignore_not_sysadmin,
                                                             unicode_safe],
            'ckanext.ontario_theme.home_block_one-fr':      [ignore_missing,
                                                             ignore_not_sysadmin,
                                                             unicode_safe],
            'ckanext.ontario_theme.home_block_one_image':   [ignore_missing,
                                                             ignore_not_sysadmin,
                                                             unicode_safe,
                                                             remove_whitespace],
            'ckanext.ontario_theme.home_block_one_link-en': [ignore_missing,
                                                             ignore_not_sysadmin,
                                                             unicode_safe,
                                                             remove_whitespace],
            'ckanext.ontario_theme.home_block_one_link-fr': [ignore_missing,
                                                             ignore_not_sysadmin,
                                                             unicode_safe,
                                                             remove_whitespace],

            'ckanext.ontario_theme.home_block_two-en':      [ignore_missing,
                                                             ignore_not_sysadmin,
                                                             unicode_safe],
            'ckanext.ontario_theme.home_block_two-fr':      [ignore_missing,
                                                             ignore_not_sysadmin,
                                                             unicode_safe],
            'ckanext.ontario_theme.home_block_two_image':   [ignore_missing,
                                                             ignore_not_sysadmin,
                                                             unicode_safe,
                                                             remove_whitespace],
            'ckanext.ontario_theme.home_block_two_link-en': [ignore_missing,
                                                             ignore_not_sysadmin,
                                                             unicode_safe,
                                                             remove_whitespace],
            'ckanext.ontario_theme.home_block_two_link-fr': [ignore_missing,
                                                             ignore_not_sysadmin,
                                                             unicode_safe,
                                                             remove_whitespace],

            'ckanext.ontario_theme.home_block_three-en':      [ignore_missing,
                                                               ignore_not_sysadmin,
                                                               unicode_safe],
            'ckanext.ontario_theme.home_block_three-fr':      [ignore_missing,
                                                               ignore_not_sysadmin,
                                                               unicode_safe],
            'ckanext.ontario_theme.home_block_three_image':   [ignore_missing,
                                                               ignore_not_sysadmin,
                                                               unicode_safe,
                                                               remove_whitespace],
            'ckanext.ontario_theme.home_block_three_link-en': [ignore_missing,
                                                               ignore_not_sysadmin,
                                                               unicode_safe,
                                                               remove_whitespace],
            'ckanext.ontario_theme.home_block_three_link-fr': [ignore_missing,
                                                               ignore_not_sysadmin,
                                                               unicode_safe,
                                                               remove_whitespace],
        })

        return schema


    # ITemplateHelpers

    def get_helpers(self):
        return {'ontario_theme_get_license': get_license,
                'extrafields_default_locale': default_locale,
                'ontario_theme_get_package_keywords': get_package_keywords,
                'ontario_theme_home_block': home_block,
                'ontario_theme_home_block_image': home_block_image,
                'ontario_theme_home_block_link': home_block_link}

    # IBlueprint

    def get_blueprint(self):
        '''Return a Flask Blueprint object to be registered by the app.
        '''

        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates'

        @blueprint.before_request
        def before_request():
            '''Could call this from within the applicable views but this pattern I like better I think.
            Could also add this as it's own IAuthFunctions as a new auth function, then call that, 
            but I don't want to override or really create a new one, I want to use the existing sysadmin
            auth function from my own views.
            '''
            if request.endpoint in ['ontario_theme.image_uploader', 'ontario_theme.image_uploaded']:
                try:
                    context = dict(model=model, user=g.user, auth_user_obj=g.userobj)
                    logic.check_access(u'sysadmin', context)
                except logic.NotAuthorized:
                    toolkit.abort(403, _(u'Need to be system administrator to administer'))

        # Add url rules to Blueprint object.
        rules = [
            (u'/help', u'help', help),
            (u'/dataset/csv_dump', u'csv_dump', csv_dump),
            (u'/ckan-admin/image-uploader', u'image_uploader', image_uploader),
            (u'/ckan-admin/image-uploaded', u'image_uploaded', image_uploaded)
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
        facets_dict['keywords_en'] = toolkit._('Keywords')
        facets_dict['keywords_fr'] = toolkit._('Keywords')
        return facets_dict

    def group_facets(self, facets_dict, group_type, package_type):
        u'''Modify and return the ``facets_dict`` for a group's page.
        Throws AttributeError: no attribute 'organization_facets' without function.
        '''
        return self.dataset_facets(facets_dict, package_type)

    def organization_facets(self, facets_dict, organization_type, package_type):
        u'''Modify and return the ``facets_dict`` for an organization's page.
        Throws AttributeError: no attribute 'organization_facets' without function.
        '''
        return self.dataset_facets(facets_dict, package_type)

    # IPackageController

    def before_search(self, search_params):
        u'''Extensions will receive a dictionary with the query parameters,
        and should return a modified (or not) version of it.
        '''
        return num_resources_filter_scrub(search_params)

    def after_search(self, search_results, search_params):
        return search_results

    def before_index(self, pkg_dict):
        kw = json.loads(pkg_dict.get('extras_keywords', '{}'))
        pkg_dict['keywords_en'] = kw.get('en', [])
        pkg_dict['keywords_fr'] = kw.get('fr', [])
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
