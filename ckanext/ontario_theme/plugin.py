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
import ckan.authz as authz
import ckan.lib.i18n as i18n

from flask import Blueprint, make_response
from flask import render_template, render_template_string

import json
import ckan.lib.helpers as helpers
from ckan.lib.helpers import core_helper

from ckan.model import Package
import ckan.model as model

from ckanext.ontario_theme.resource_upload import ResourceUpload
from ckanext.ontario_theme.create_view import CreateView as OntarioThemeCreateView

# For Image Uploader
#from ckan.controllers.home import CACHE_PARAMETERS
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
                                       ignore_keys=''))))

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
    resource_type = helpers.get_translated(resource_dict, 'type')
    if name:
        return name
    elif description:
        description = description.split('.')[0]
        max_len = 60
        if len(description) > max_len:
            description = description[:max_len] + '...'
        return description
    elif resource_type:
        return resource_type.replace('_',' ').capitalize()
    else:
        return helpers._("Supporting file")

ckan.lib.helpers.resource_display_name = resource_display_name

def help():
    '''New help page for site.
    '''
    return render_template('home/help.html')


def csv_dump():
    '''
        This was rewritten to be compatible with python3.6/ckan2.9
        It used to use ckanapi_exporter, but that was replaced with borrowing csv generation 
        from the datastore extension
    '''
    fields = [
        {   "id": "Id",
            "pattern": ["id"],
            "type": "text"
        },
        {
            "id": "Name",
            "pattern": ["name"],
            "type": "text"
        },
        {
            "id":"Title EN",
            "pattern": ["title_translated", "en"],
            "type": "text"
        },
        {
            "id":"Notes EN",
            "pattern": ["notes_translated", "en"],
            "type": "text"
        },
        {
            "id":"Organization Title",
            "pattern": ["organization", "title"],
            "type": "text"
        },
        {
            "id":"Access Level",
            "pattern": ["access_level"],
            "type": "text"
        },
        {
            "id":"Type",
            "pattern": ["type"],
            "type": "text"
        },
        {
            "id":"Update Frequency",
            "pattern": ["update_frequency"],
            "type": "text"
        },
        {
            "id":"Metadata Created",
            "pattern": ["metadata_created"],
            "type": "timestamp"
        },
        {
            "id":"Metadata Modified",
            "pattern": ["metadata_modified"],
            "type": "timestamp"
        },
        {
            "id":"License Title",
            "pattern": ["license_title"],
            "type": "text"
        },
        {
            "id":"Keywords EN",
            "pattern": ["keywords", "en"],
            "type": "text"
        },
        {
            "id":"Package Date Opened",
            "pattern": ["opened_date"],
            "type": "text"
        },
        {
            "id":"Package Last Validated Date",
            "pattern": ["current_as_of"],
            "type": "timestamp"
        },
        {
            "id":"Exemption",
            "pattern": ["exemption"],
            "type": "text"
        },
        {
            "id":"Exemption Rationale EN",
            "pattern": ["exemption_rationale", "en"],
            "type": "text"
        },
        {
            "id":"Geographic Coverage EN",
            "pattern": ["geographic_coverage_translated", "en"],
            "type": "text"
        },
        {
            "id":"Resources Format",
            "pattern": ["resources", "format"],
            "deduplicate": "true",
            "type": "text"
        },
        {
            "id":"Num Resources",
            "pattern": ["num_resources"],
            "type": "int"
        },
        {
            "id":"Title FR",
            "pattern": ["title_translated", "fr"],
            "type": "text"
        },
        {
            "id":"Geographic Coverage FR",
            "pattern": ["geographic_coverage_translated", "fr"],
            "type": "text"
        },
        {
            "id":"Exemption Rationale FR",
            "pattern": ["exemption_rationale", "fr"],
            "type": "text"
        },
        {
            "id":"Keywords FR",
            "pattern": ["keywords", "fr"],
            "type": "text"
        }
    ]

    import csv
    from ckanext.datastore.writer import csv_writer
    
    def returnValues(value, pattern):
        pattern_step = pattern[0]
        if isinstance(value, list) and len(value) > 0:
            for sub_value in value:
                return " ".join(returnValues(sub_value, pattern))
        elif len(pattern) == 1 and pattern_step in value:
            return value[pattern_step]                 
        elif pattern_step in value:
            return returnValues(value[pattern_step], pattern[1:])
        else:
            return ""

    def write_packages(records_chunk):
        rows = []
        for dataset_row in records_chunk:
            row = []
            for v in fields:
                row.append(returnValues(dataset_row, v['pattern']))
            csv.writer(response.stream).writerow(row)            

    def result_page(offs, lim):
        get_packages=toolkit.get_action('package_search')(
                data_dict={
                        'sort': 'title desc',
                        'start': offs,
                        'rows': lim
                        })
        return get_packages

    limit = 1000

    # create file name
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d')
    csv_filename = 'ontario_data_catalogue_inventory_' + timestamp

    #start response
    response = make_response()
    response.headers[u'content-type'] = u'application/octet-stream'

    with csv_writer(response, fields, csv_filename, True) as wr:
        start = 0
        count = 1
        while start < count:
            result = result_page(start, limit)
            if count == 1:
                count = result["count"] 
            write_packages(result["results"])
            start = start + limit

    return response


def get_group(group_id):
    '''Helper to return the group.
    CKAN core has a get_organization helper but does not have one for groups.
    This also allows us to access the group with all extras which are needed to 
    access the scheming/fluent fields.
    '''
    group_dict = toolkit.get_action('group_show')(
        data_dict={'id': group_id})
    return group_dict

def get_group_datasets(group_id):
    '''Helper to return 10 of the most popular datasets in the desired group
    '''
    group_id = 'groups:{}'.format(group_id)
    group_datasets = toolkit.get_action('package_search')(
        data_dict={ 'fq': group_id,
                    'rows': 10,
                    'sort': 'views_recent desc'})
    return group_datasets['results']

def get_keyword_count(keyword_lang, language):
    '''Helper to return the dataset count of the indicated group by language

    keyword_lang
        The topic category string on the Home page.
        e.g. "Housing, Communities and Social Support"

    language
        Current language of the site.
    '''
    facet = "keywords_{}".format(language) # either keywords_en or keywords_fr

    # Keywords of all packages as defined manually in the 
    # dataset page upon creation
    package_keywords = toolkit.get_action('package_search')(
    data_dict={'facet.field': [facet],
        'rows': 0})
    
    # Keywords that are currently selected
    active_keywords = package_keywords['facets'][facet]

    # Determine if any Homepage topics match any currently-selected keywords
    # NB: Commas are not allowed in package keywords, so to match packages
    # containing the keyword string "Housing, Communities and Social Support",
    # with the Homepage topic "Housing, Communities and Social Support", 
    # the comma must be disregarded in the Homepage topic.
    if keyword_lang.replace(',', '') in active_keywords:
        keyword_count_by_lang = active_keywords[keyword_lang.replace(',', '')]
    else:
        keyword_count_by_lang = 0

    return keyword_count_by_lang

def paginate_items(all_items, current_page, items_per_page):
    '''Returns a slice of an array of items for pagination
    based on the current page and the max number of items
    allowed per page.

    current_page
        The page number currently being displayed.

    items_per_page
        Maximum number of items to display per page. 
        Defined somewhere as 20.
    '''
    item_count =  len(all_items)

    # Calculate number of pages in the pagination needed to display
    # all items in input_items
    if item_count > 0:
        first_page = 1
        page_count = int(((item_count - 1) / items_per_page) + 1)
        last_page = first_page + page_count - 1

    # Set index ranges for slicing the sorted_org object
    slice0 = [] 
    slice1 = []
    for idx in range(last_page):
        slice0.append(idx * items_per_page)
        next_max = slice0[idx] + items_per_page
        if item_count < next_max:
            slice1.append(item_count)
        else:
            slice1.append(next_max)

    # Slice the sorted_org object according to the current
    # pagination page and return it for display
    page = 0
    for idx in range(len(slice0)):
        page+=1
        if page == current_page:
            this_slice = all_items[slice0[idx]:slice1[idx]]
    
    return this_slice 

def get_all_packages(**kwargs):
    '''Helper to return the full number of packages matching a 
    search query, including any facet search requests (in the
    case of no searches, all packages are returned). The full
    number of packages is needed because in the search page, 
    only the paginated number of packages for the current page 
    is available, which prohibits application of any custom 
    sorting since sorting must be done on the full list before
    pagination.

    q
        Search query. Passed through c.q.
    
    request_params_items
        Contains the facet search parameters. Passed through
        request.params.

    current_org
        When datasets are accessed by clicking on an Organization,
        the package search must be limited to the current
        organization, which is stored in this variable. This 
        variable is not needed when accessing datasets through
        the Datasets page.

    current_group
        When datasets are accessed by clicking on a Group,
        the package search must be limited to the current
        group, which is stored in this variable. This 
        variable is not needed when accessing datasets through
        the Datasets page.
    
    item_count
        Number of packages matching search. Passed through 
        c.page.item_count.

    '''
    q = kwargs['q']
    request_params_items = kwargs['request_params_items']
    current_org = kwargs['current_org']
    current_group = kwargs['current_group']
    item_count = kwargs['item_count']

    # Excerpt from search() fn in ckan/ckan/controllers/package.py
    # Needed to collect search parameters from facets.
    search_extras = {}
    fq = ''
    for (param, value) in OrderedDict(request_params_items).items():
        if param not in ['q', 'page', 'sort'] \
            and len(value) and not param.startswith('_'):
            if not param.startswith('ext_'):
                fq += ' %s:"%s"' % (param, value)
            else:
                search_extras[param] = value
    
    # Add organization to facet query
    # see e.g. https://localhost/api/action/package_search?fq=organization:helloworld&include_private=true
    if current_org:
        fq += ' %s:"%s"' % ('organization', current_org)
    
    # Add groups to facet query
    # see e.g. https://localhost/api/action/package_search?fq=groups:2019-novel-coronavirus
    if current_group:
        fq += ' %s:"%s"' % ('groups', current_group)

    # Get the full set of packages returned by search query q
    # and any facet queries fq.
    # Note that number of packages matched will be limited to 10
    # unless otherwise specified in 'rows'. Since we already know
    # there are 'item_count' number of matches, we can set rows 
    # to 'item_count'.
    package_search=toolkit.get_action('package_search')(
                data_dict={
                        'q': q,
                        'fq': fq.strip(),
                        'start': 0,
                        'sort': 'title desc',
                        'rows': item_count,
                        'extras': search_extras,
                        'include_private': True
                        })

    return package_search['results']

def get_all_organizations(**kwargs):
    '''Helper function to returns the full list of organizations 
    output from a keyword search (or all organizations in the 
    case of no search). In the search page, only the paginated 
    number of organizations for the current page is available, 
    which prohibits application of any custom sorting since that 
    needs the full list.

    collection_names
        An array of short-hand (hyphenated) organization names 
        (e.g. 'attorney-general') for all items returned from the 
        search. If no search performed, includes all items.
        Passed from c.page.collection.

    '''
    collection_names=kwargs['collection_names']    

    # Get the id of all organizations in the catalogue.
    all_organization_names = toolkit.get_action('organization_list')(data_dict={})
    
    # When there are no organizations in the catalogue (e.g. when application is 
    # first installed and database not yet indexed), the below try will fail and
    # and empty array will be returned, preventing the template from calling 
    # the sort method on organizations.
    try:
        this_name = all_organization_names[0]
        if toolkit.get_action('organization_show')(data_dict={'id':this_name}):
            # Filter only those organizations whose names matching those in 
            # collection_names. Then use helper function h.get_organization() 
            # to extract the full details for each organization, matching on 'id'.
            org_array = []
            for name in collection_names:
                for idx in range(len(all_organization_names)):
                    if name == all_organization_names[idx]:
                        organization_obj = toolkit.get_action('organization_show')(data_dict={'id':name})
                        organization_id = organization_obj['id']
                        org_array.append(h.get_organization(organization_id))
    except:
        org_array = []

    return org_array

def sort_by_title_translated(item_list, **kwargs):
    '''Helper function to sort an array of items by the 
    'title_translated' dict according to the current language. 
    If this dict does not exist, 'title' is used to sort since 
    'title' always exists.

    item_list
        List of items to be sorted.

    current_page
        Current page in the pagination. Passed through c.page.page. 
    
    items_per_page
        Max number of items per page. Defined in ckan/controllers/package.py
        as int(config.get('ckan.datasets_per_page', 20)). 
        Passed through c.page.items_per_page.

    lang
        Current language. Pass through request.environ.CKAN_LANG.

    reverse
        Sort direction. Determined through `asc` or `desc` in request.params['sort']. 

    '''
    field = 'title_translated'
    current_page=kwargs['current_page']
    items_per_page=kwargs['items_per_page']
    lang = kwargs['lang']
    reverse = kwargs['reverse']

    # Sort item_list by translated title
    sorted_items = sorted(item_list, 
                             key=lambda x: x[field][lang].strip() if (field in x and lang in x[field]) else x['title'], 
                             reverse=reverse)

    # Return subset of sorted_items as per the current pagination page
    return paginate_items(sorted_items, current_page, items_per_page)

def get_popular_datasets():
    '''Helper to return most popular datasets, based on ckan core tracking feature
    '''
    popular_datasets = toolkit.get_action('package_search')(
        data_dict={'rows': 10,
                    'sort': 'views_recent desc'})
    return popular_datasets['results']

def get_recently_updated_datasets():
    '''Helper to return 3 freshest datasets
    '''
    recently_updated_datasets = toolkit.get_action('package_search')(
        data_dict={'rows': 3,
                    'sort': 'current_as_of desc'})
    return recently_updated_datasets['results']

def get_license(license_id):
    '''Helper to return license based on id.
    '''
    return Package.get_license_register().get(license_id)

def order_package_facets(orig_ordered_dict):
    ''' Returns an OrderedDict of package facets in the order
    that they should appear in the left panel of the Datasets
    page.

    '''
    # Order that facets should appear in left panel
    facet_order = ['organization', 'res_format', 'access_level', 'update_frequency', 'license_id',
                   'asset_type', 'groups',
                   'organization_jurisdiction', 'organization_category',
                   'keywords_en', 'keywords_fr',
                  ]

    facet_titles_reorg = list()
    for facet in facet_order:
        for idx in range(len(orig_ordered_dict)):
            if list(orig_ordered_dict)[idx]==facet:
                facet_titles_reorg.append((facet, orig_ordered_dict[facet]))

    return OrderedDict(facet_titles_reorg)

def extract_package_name(url):
    ''' Returns the package name or gets resource name if url is for
        a dataset or resource page

        Returns resource type or "Supporting file" if there is no resource name and
        no resource type
    '''
    import re

    package_pattern = "\/dataset\/([-a-z-0-9A-Z\n\r]*)"
    resource_pattern = "\/resource\/([-a-z-0-9A-Z\n\r]*)"
    get_resource_name = re.compile(resource_pattern).findall(url)
    get_package_name = re.compile(package_pattern).findall(url)
    
    if len(get_resource_name) > 0:
        try:
            resource_name = toolkit.get_action('resource_show') (
                data_dict={'id': get_resource_name[0]}
                )
            if 'name' in resource_name and not resource_name['name']:
                if 'type' in resource_name:
                    if not resource_name['type']:
                        return "Unnamed Supporting File"
                    else:
                        return "Unnamed " + resource_name['type'] + " file"
                elif 'resource_type' in resource_name:
                    if not resource_name['resource_type']:
                        return "Unnamed Supporting File"
                    else:
                        return "Unnamed " + resource_name['resource_type'] + " file"
            
            if 'name' in resource_name:
                if len(resource_name['name']) > 0:
                    return resource_name['name']
                else:
                    return "Unnamed Data File"
        except ckan.logic.NotFound:
            return False
    elif len(get_package_name) > 0:
        return get_package_name[0]
    else:
        return False

def get_translated_lang(data_dict, field, specified_language):
    try:
        return data_dict[field + u'_translated'][specified_language]
    except KeyError:
        return helpers.get_translated(data_dict, field)


def resource_update_auth(context, data_dict=None):
    isHarvestedResource = False
    if data_dict: 
        isHarvestedResource = data_dict.get('harvested_resource', False)
    if isHarvestedResource:
        return {'success': False, 'msg': 'This user is not allowed to edit this resource'}
    return {'success': True, 'msg': 'This package is editable.'}


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
    plugins.implements(plugins.IAuthFunctions)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates/internal')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic/internal', 'ontario_theme')
        toolkit.add_resource('fanstatic', 'ontario_theme_common')
        toolkit.add_resource('fanstatic/scripts', 'ontario_theme_scripts')


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


    # IAuthFunctions

    def get_auth_functions(self):
        return {
            'resource_update': resource_update_auth
            } 


    # ITemplateHelpers

    def get_helpers(self):
        return {'ontario_theme_get_license': get_license,
                'ontario_theme_extract_package_name': extract_package_name,
                'ontario_theme_order_package_facets': order_package_facets,
                'ontario_theme_get_translated_lang': get_translated_lang,
                'ontario_theme_get_popular_datasets': get_popular_datasets,
                'ontario_theme_get_group': get_group,
                'ontario_theme_get_date_range' : get_date_range,
                'extrafields_default_locale': default_locale,
                'ontario_theme_get_package_keywords': get_package_keywords,
                'ontario_theme_home_block': home_block,
                'ontario_theme_home_block_image': home_block_image,
                'ontario_theme_home_block_link': home_block_link,
                'ontario_theme_get_group_datasets': get_group_datasets,
                'ontario_theme_get_keyword_count': get_keyword_count,
                'ontario_theme_get_all_packages': get_all_packages,
                'ontario_theme_get_all_organizations': get_all_organizations,
                'ontario_theme_sort_by_title_translated': sort_by_title_translated
                }

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
            (u'/dataset/inventory', u'inventory', csv_dump)
        ]

        for rule in rules:
            blueprint.add_url_rule(*rule)
        blueprint.add_url_rule('/dataset/new', view_func=OntarioThemeCreateView.as_view(str(u'new')), defaults={u'package_type': u'dataset'})
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
        facets_dict['keywords_en'] = toolkit._('Topics')
        facets_dict['keywords_fr'] = toolkit._('Topics')
        facets_dict['license_id'] = toolkit._('Licences')
        facets_dict['organization'] = toolkit._('Ministries')
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
            'lock_if_odc': validators.lock_if_odc,
            'ontario_theme_copy_fluent_keywords_to_tags': validators.ontario_theme_copy_fluent_keywords_to_tags,
            'ontario_tag_name_validator': validators.tag_name_validator
       }
