# coding=utf-8
import re
import datetime
from ckan.model import Package
from ckan.common import config
import ckan.plugins.toolkit as toolkit

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


'''

Helpers used by harvest

'''

def strip_html_tags(name):
    '''Very quick and dirty cleaner.
    '''
    cleaned_name = re.sub("<\s*[^>]*>|<\s*\s*>", '', name)
    return cleaned_name

def remove_odd_chars_from_keywords(keyword_list):
    '''Keywords must be alphanumeric characters or symbols: -_.
    commas and slashes cannot be accepted.
    '''
    #cleaned_keyword_list = [str(keyword).replace("'", '') for keyword in keyword_list]
    cleaned_keyword_list = [re.sub("[\W_-]+", ' ', str(keyword)) for keyword in keyword_list]
    return cleaned_keyword_list

def name_cleaner(name):
    ''' Clean Title to make it suitable for name field.
    Example:
        " non-Integrated Community   Profiles (ICP) "
        becomes
        "non-integrated-community-profiles-icp"
    '''

    # Remove leading and trailing whitespace
    cleaned_name = name.strip()
    # Lower case
    cleaned_name = cleaned_name.lower()
    # Remove html elements.
    cleaned_name = strip_html_tags(cleaned_name)
    # Remove odd chars
    cleaned_name = re.sub("[^A-Za-z0-9 -]", '', cleaned_name)
    # Remove duplicate white space
    cleaned_name = re.sub(' +', ' ', cleaned_name)
    # Replace whitespace with dash
    cleaned_name = cleaned_name.replace(' ', '-')
    # Remove duplicate dashes
    cleaned_name = re.sub('-+', '-', cleaned_name)
    # Make sure it's < 100 chars
    cleaned_name = cleaned_name[0:99]

    return cleaned_name

def date_parse(date_str, format):
    '''Takes a date string and parses to date object.
    '''
    date_format = format

    if not date_str:
        return ""

    return datetime.datetime.strptime(date_str, date_format).isoformat()