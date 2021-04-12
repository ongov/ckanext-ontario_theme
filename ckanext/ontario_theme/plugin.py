# encoding: utf-8

import ckan.plugins as plugins
from ckanext.ontario_theme import validators
import ckan.plugins.toolkit as toolkit
from ckan.lib.plugins import DefaultTranslation

import ckan.logic.schema
from ckan.logic.schema import validator_args
from ckan.common import config, request, g, _
from collections import OrderedDict
import datetime
from webhelpers.html import literal
import ckan.authz as authz
import ckan.lib.i18n as i18n

from flask import Blueprint, make_response
from flask import render_template, render_template_string

import ckanapi_exporter.exporter as exporter
import json
import ckan.lib.helpers as helpers
from ckan.lib.helpers import core_helper

from ckan.model import Package
import ckan.model as model

from ckanext.ontario_theme import controller

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

'''
default_tags_schema added because when tags are validated on 
resource_create/resource_update, it doesn't pull tag validators 
from scheming, rather applies core tag validators.

We considered adding tags back into the schema so we could include new
tag validators for tags, but it seemed neater to continue to keep it out 
of the schema.

We also considered using _modify_package_schema, but it doesn't work with
the scheming plugin.

Instead we're modifying default_tags_schema to include the correct validators.
This is lifted from core and the only change is:
tag_name_validator
to
validators.tag_name_validator
'''
@validator_args
def default_tags_schema(
        not_missing, not_empty, unicode_safe, tag_length_validator,
        tag_name_validator, ignore_missing, vocabulary_id_exists,
        ignore):

    return {
        'name': [not_missing,
                 not_empty,
                 unicode_safe,
                 tag_length_validator,
                 validators.tag_name_validator
                 ],
        'vocabulary_id': [ignore_missing,
                          unicode_safe,
                          vocabulary_id_exists],
        'revision_timestamp': [ignore],
        'state': [ignore],
        'display_name': [ignore],
    }

ckan.logic.schema.default_tags_schema = default_tags_schema

@core_helper
def resource_display_name(resource_dict):
    # TODO: (?) support resource objects as well
    name = helpers.get_translated(resource_dict, 'name')
    description = helpers.get_translated(resource_dict, 'description')
    if name:
        return name
    elif description:
        description = description.split('.')[0]
        max_len = 60
        if len(description) > max_len:
            description = description[:max_len] + '...'
        return description
    else:
        return helpers._("Data")

ckan.lib.helpers.resource_display_name = resource_display_name

def help():
    '''New help page for site.
    '''
    return render_template('home/help.html')


# replace the core get_snippet_actor to anonymize the activity stream when user
# is not logged in

def get_snippet_actor(activity, detail):
    user = authz.auth_is_loggedin_user()
    if not user:
        if i18n.get_lang() == 'fr':
            return literal('''<span class="actor">%s</span>'''
                % "L'équipe de données ouvertes de l'Ontario".decode('utf8')
                )
        else:
            return literal('''<span class="actor">Ontario's Open Data Team \
                </span>'''
                )
    else:
        return literal('''<span class="actor">%s</span>'''
            % (helpers.linked_user(activity['user_id'], 0, 30))
            )

ckan.lib.activity_streams.get_snippet_actor = get_snippet_actor
ckan.lib.activity_streams.activity_snippet_functions['actor'] = get_snippet_actor


def csv_dump():
    '''The pattern allows you to go deeper into the nested structures.
    `["^title_translated$", "en"]` grabs the english title_translated value.
    It doesn't seem to handle returning a dict such as
    `{'en': 'english', 'fr': 'french'}`.
    Exporting resource metadata is limited. It combines resource values
    into single comma seperated string.
    deduplicate needed to be "true" not true.
    '''
    columns = OrderedDict([
        ("Id", {
            "pattern": "^id$"
        }),
        ("Name", {
            "pattern": "^name$"
        }),
        ("Title EN", {
            "pattern": ["^title_translated$", "^en$"]
        }),
        ("Notes EN", {
            "pattern": ["^notes_translated$", "^en$"]
        }),
        ("Organization Title", {
            "pattern": ["^organization$", "^title$"]
        }),
        ("Access Level", {
            "pattern": "^access_level$"
        }),
        ("Type", {
            "pattern": "^type$"
        }),
        ("Update Frequency", {
            "pattern": "^update_frequency$"
        }),
        ("Metadata Created", {
            "pattern": "^metadata_created$"
        }),
        ("Metadata Modified", {
            "pattern": "^metadata_modified$"
        }),
        ("License Title", {
            "pattern": "^license_title$"
        }),
        ("Keywords EN", {
            "pattern": ["^keywords$", "^en$"]
        }),
        ("Package Date Opened", {
            "pattern": "^opened_date$"
        }),
        ("Package Last Validated Date", {
            "pattern": "^current_as_of$"
        }),
        ("Exemption", {
            "pattern": "^exemption$"
        }),
        ("Exemption Rationale EN", {
            "pattern": ["^exemption_rationale$", "^en$"]
        }),
        ("Geographic Coverage EN", {
            "pattern": ["^geographic_coverage_translated$", "^en$"]
        }),
        ("Resources Format", {
            "pattern": ["^resources$", "^format$"],
            "deduplicate": "true"
        }),
        ("Num Resources", {
            "pattern": "^num_resources$"
        }),
        ("Title FR", {
            "pattern": ["^title_translated$", "^fr$"]
        }),
        ("Geographic Coverage FR", {
            "pattern": ["^geographic_coverage_translated$", "^fr$"]
        }),
        ("Exemption Rationale FR", {
            "pattern": ["^exemption_rationale$", "^fr$"]
        }),
        ("Keywords FR", {
            "pattern": ["^keywords$", "^fr$"]
        })
    ])

    site_url = config.get('ckan.site_url')
    csv_string = exporter.export(site_url, columns)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d')
    csv_filename = 'ontario_data_catalogue_inventory_' + timestamp + '.csv'

    resp = make_response(u'\uFEFF'.encode('utf-8') + csv_string, 200)
    resp.headers['Content-Type'] = b'text/csv; charset=utf-8'
    resp.headers['Content-disposition'] = \
        (b'attachment; filename=%s' % csv_filename)
    return resp

def get_group(group_id):
    '''Helper to return the group.
    CKAN core has a get_organization helper but does not have one for groups.
    This also allows us to access the group with all extras which are needed to 
    access the scheming/fluent fields.
    '''
    group_dict = toolkit.get_action('group_show')(
        data_dict={'id': group_id})
    return group_dict

def get_recently_updated_datasets():
    '''Helper to return 3 freshest datasets
    '''
    recently_updated_datasets = toolkit.get_action('package_search')(
        data_dict={'rows': 3,
                    'sort': 'current_as_of desc'})
    return recently_updated_datasets['results']


def get_popular_datasets():
    '''Helper to return most popular datasets, based on ckan core tracking feature
    '''
    popular_datasets = toolkit.get_action('package_search')(
        data_dict={'rows': 3,
                    'sort': 'views_recent desc'})
    return popular_datasets['results']


def get_license(license_id):
    '''Helper to return license based on id.
    '''
    return Package.get_license_register().get(license_id)

def extract_package_name(url):
    import re
    package_pattern = "\/dataset\/([-a-z-0-9A-Z\n\r]*)"
    find_package = re.compile(package_pattern)
    get_package_name = find_package.findall(url)
    if len(get_package_name) > 0:
        return get_package_name[0]
    else:
        return False

def get_translated_lang(data_dict, field, specified_language):
    try:
        return data_dict[field + u'_translated'][specified_language]
    except KeyError:
        return helpers.get_translated(data_dict, field)


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

def get_date_range(date_start, date_end):

    if date_start == 'N/A' or date_end == 'N/A':
        date_range = str(date_start) + ' - ' + str(date_end)
    else:
        dt_start = datetime.datetime.strptime(date_start, "%Y-%m-%d")
        dt_end = datetime.datetime.strptime(date_end, "%Y-%m-%d")

        if dt_start.month == 1 and dt_start.day == 1 and \
                dt_end.month == 12 and dt_end.day == 31:
            if dt_start.year == dt_end.year:
                date_range = str(dt_start.year)
            else:
                date_range = str(dt_start.year)+' - '+str(dt_end.year)
        elif dt_start.month == 4 and dt_start.day == 1 and \
                dt_end.month == 3 and dt_end.day == 31:
            date_range = helpers._("Fiscal: ")+str(dt_start.year) \
                +' - '+str(dt_end.year)
        else:
            date_range = str(date_start) + ' - ' + str(date_end)

    return date_range

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
        config_['scheming.group_schemas'] = """
ckanext.ontario_theme:schemas/ontario_theme_group.json
"""

class OntarioThemePlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IUploader, inherit=True)
    plugins.implements(plugins.IFacets)
    plugins.implements(plugins.IPackageController)
    plugins.implements(plugins.IValidators)

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
        config_['ckan.tracking_enabled'] = """
true
"""
        config_['ckan.extra_resource_fields'] = """
type data_last_updated
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
                'ontario_theme_extract_package_name': extract_package_name,
                'ontario_theme_get_translated_lang': get_translated_lang,
                'ontario_theme_get_popular_datasets': get_popular_datasets,
                'ontario_theme_get_group': get_group,
                'ontario_theme_get_recently_updated_datasets': get_recently_updated_datasets,
                'ontario_theme_get_date_range' : get_date_range,
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
            (u'/ckan-admin/image-uploader', u'image_uploader', image_uploader),
            (u'/ckan-admin/image-uploaded', u'image_uploaded', image_uploaded),
            (u'/dataset/inventory', u'inventory', csv_dump)
        ]
        for rule in rules:
            blueprint.add_url_rule(*rule)

        return blueprint

    # IUploader

    def get_resource_uploader(self, data_dict):
        return ResourceUpload(data_dict)

    # IFacets

    def dataset_facets(self, facets_dict, package_type):
        '''Add new search facet (filter) for datasets.
        '''
        facets_dict['access_level'] = toolkit._('Access Level')
        facets_dict['asset_type'] = toolkit._('Asset Type')
        facets_dict['update_frequency'] = toolkit._('Update Frequency')
        facets_dict['keywords_en'] = toolkit._('Keywords')
        facets_dict['keywords_fr'] = toolkit._('Keywords')
        facets_dict.pop('tags', None) # Remove tags in favor of keywords
        facets_dict['organization_jurisdiction'] = toolkit._('Jurisdiction')
        facets_dict['organization_category'] = toolkit._('Category')
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

        # Index some organization extras fields from fluent/scheming.
        organization_dict = toolkit.get_action('organization_show')(data_dict={'id': pkg_dict['organization']})
        pkg_dict['organization_jurisdiction'] = organization_dict.get('jurisdiction', '')
        pkg_dict['organization_category'] = organization_dict.get('category', '')
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

    # IValidators

    def get_validators(self):
       return {
            'ontario_theme_copy_fluent_keywords_to_tags': validators.ontario_theme_copy_fluent_keywords_to_tags,
            'ontario_tag_name_validator': validators.tag_name_validator
       }
