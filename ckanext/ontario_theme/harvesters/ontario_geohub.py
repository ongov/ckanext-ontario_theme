# coding=utf-8

'''
This harvester works specifically for the Ontario Geohub geospatial catalogue at:

https://geohub.lio.gov.on.ca/api/feed/dcat-ap/2.1.1.json

''' 
import json
import datetime
import re
import logging
import requests
import html2text
import lxml.etree
from collections import Counter
from hashlib import sha1
import traceback
import uuid

import six
from ckan import model
from ckan import logic
from ckan import plugins as p
from ckanext.harvest.model import HarvestObject, HarvestObjectExtra
from ckanext.harvest.harvesters import HarvesterBase
from ckanext.harvest.harvesters.ckanharvester import CKANHarvester
from ckan.lib.navl.validators import ignore_missing, ignore
from ckanext.harvest.logic.schema import unicode_safe

from ckanext.ontario_theme import helpers as ontario_theme_helpers
import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)

DEFAULT_GEOHUB_DCAT_FEED_URL = 'https://geohub.lio.gov.on.ca/api/feed/dcat-ap/2.1.1.json'
MINIMUM_GEOHUB_MINISTRY_DATASET_COUNT = 3
GEOHUB_PUBLISHER_OPTIONS_CACHE_TTL = datetime.timedelta(hours=24)

blacklist_url = "https://services9.arcgis.com/a03W7iZ8T3s5vB7p/ArcGIS/rest/services/odc_sync_blacklist_vw/FeatureServer/0/query?where=1%3D1&outFields=geohub_dataset_url&f=json"

geohub_publisher_aliases = {
    'Ontario Ministry of Natural Resources':
        'Ontario Ministry of Natural Resources and Forestry',
    'Ontario Ministry of  Natural Resources and Forestry':
        'Ontario Ministry of Natural Resources and Forestry',
    'Ontario Ministry Natural Resources':
        'Ontario Ministry of Natural Resources and Forestry',
    'Ministry of Natural Resources':
        'Ontario Ministry of Natural Resources and Forestry',
    'Ontario Ministry of Natural Resources and Forestry - Provincial Mapping Unit':
        'Ontario Ministry of Natural Resources and Forestry',
    'Provincial Mapping Unit - Ontario Ministry of Natural Resources and Forestry':
        'Ontario Ministry of Natural Resources and Forestry',
    'Ontario Ministry of Agriculture, Food, and Rural Affairs':
        'Ontario Ministry of Agriculture, Food and Rural Affairs',
    'Ontario Ministry of Agriculture, Food, and Rural Affairs, OMAFRA':
        'Ontario Ministry of Agriculture, Food and Rural Affairs',
    'OMAFRA': 'Ontario Ministry of Agriculture, Food and Rural Affairs',
    'OMAFA': 'Ontario Ministry of Agriculture, Food and Rural Affairs',
    'OMAFRA- Environmental Management Branch':
        'Ontario Ministry of Agriculture, Food and Rural Affairs',
    'Ministry of Northern Development, Mines, Natural Resources and Forestry':
        'Ontario Ministry of Northern Development, Mines, Natural Resources and Forestry',
}

fallback_geohub_ministry_counts = {
    'Ontario Ministry of Natural Resources and Forestry': 365,
    'Ontario Ministry of Agriculture, Food and Rural Affairs': 26,
    'Ontario Ministry of Northern Development, Mines, Natural Resources and Forestry': 16,
    'Ontario Ministry of Municipal Affairs and Housing': 14,
    'Ontario Ministry of the Environment, Conservation and Parks': 10,
}

_geohub_publisher_options_cache = {
    'expires_at': None,
    'options': None,
}

ORG_LOOKUP_CACHE_TTL = datetime.timedelta(minutes=10)
_org_lookup_cache = {}
_org_lookup_cache_expires_at = None
_missing_org_warning_cache = set()


def _get_active_organization_lookup():
    global _org_lookup_cache_expires_at

    now = datetime.datetime.utcnow()
    if (_org_lookup_cache_expires_at and
            _org_lookup_cache_expires_at > now and
            _org_lookup_cache):
        return _org_lookup_cache

    lookup = {}
    organizations = model.Session.query(
        model.Group.id,
        model.Group.name,
        model.Group.title
    ).filter(
        model.Group.type == 'organization'
    ).filter(
        model.Group.state == 'active'
    ).all()

    for organization_id, organization_name, organization_title in organizations:
        if organization_name:
            lookup[organization_name.strip().lower()] = organization_id
        if organization_title:
            lookup[organization_title.strip().lower()] = organization_id

    _org_lookup_cache.clear()
    _org_lookup_cache.update(lookup)
    _org_lookup_cache_expires_at = now + ORG_LOOKUP_CACHE_TTL
    return _org_lookup_cache


def normalize_geohub_publisher_name(publisher_name):
    if not publisher_name:
        return ''

    normalized_name = re.sub(r'\s+', ' ', publisher_name).strip()
    return geohub_publisher_aliases.get(normalized_name, normalized_name)


def get_ontario_geohub_publisher_options(
        minimum_dataset_count=MINIMUM_GEOHUB_MINISTRY_DATASET_COUNT):
    now = datetime.datetime.utcnow()
    cache_expires_at = _geohub_publisher_options_cache['expires_at']
    if (cache_expires_at and cache_expires_at > now and
            _geohub_publisher_options_cache['options'] is not None):
        return list(_geohub_publisher_options_cache['options'])

    counts = Counter()
    try:
        response = requests.get(DEFAULT_GEOHUB_DCAT_FEED_URL, timeout=60)
        response.raise_for_status()
        doc = response.json()
        datasets = doc.get('dcat:dataset', []) if isinstance(doc, dict) else doc

        for dataset in datasets:
            publisher_name = normalize_geohub_publisher_name(
                dataset.get('ontario_geohub_publisher', ''))
            log.debug('publisher_name after normalize: %s', publisher_name)
            if publisher_name.startswith('Ontario Ministry'):
                counts[publisher_name] += 1
    except (requests.exceptions.RequestException, ValueError, TypeError) as e:
        log.warning('Unable to load Ontario GeoHub ministry options: %s', e)
        counts.update(fallback_geohub_ministry_counts)

    if not counts:
        counts.update(fallback_geohub_ministry_counts)

    options = [
        {
            'value': ministry_name,
            'text': '{} ({})'.format(ministry_name, dataset_count)
        }
        for ministry_name, dataset_count in counts.most_common()
        if dataset_count >= minimum_dataset_count
    ]

    _geohub_publisher_options_cache['options'] = options
    _geohub_publisher_options_cache['expires_at'] = (
        now + GEOHUB_PUBLISHER_OPTIONS_CACHE_TTL)

    return list(options)


def get_ontario_geohub_harvest_organization_options(
        minimum_dataset_count=MINIMUM_GEOHUB_MINISTRY_DATASET_COUNT):
    organization_options = []
    seen_organization_ids = set()

    for publisher_option in get_ontario_geohub_publisher_options(
            minimum_dataset_count=minimum_dataset_count):
        publisher_name = publisher_option['value']
        organization_name = publisher_ministries.get(publisher_name)
        if not organization_name:
            continue

        organization = model.Group.by_name(organization_name)
        if not organization or organization.id in seen_organization_ids:
            continue

        organization_title = organization.title or publisher_name

        organization_options.append({
            'value': organization.id,
            'text': organization_title,
        })
        seen_organization_ids.add(organization.id)

    # Prepend "All ministries" option
    all_ministries_option = [{'value': '', 'text': 'All ministries'}]
    return all_ministries_option + organization_options

restricted_tags = {
    "MNRFNHICClassifiedData": {
        "access_instructions" : {
            "en": "Email the Natural Heritage Information Centre or phone us at 705-755-2159 to inquire about a Sensitive Data Use Licence.",
            "fr": "Veuillez envoyer un courriel au Centre d'information sur le patrimoine naturel ou communiquer avec nous par téléphone au numéro 705 755-2159 pour demander une convention de droits d'utilisation de données sensibles."
        },
        "exemption" : "security",
        "exemption_rationale": {
            "en": "Potential for deliberate harm to critical infrastructure (some data include sensitive values or locations of at-risk species)",
            "fr": "Des dommages pourraient délibérément être causés à l’infrastructure essentielle (certaines données incluent des valeurs sensibles ou l’emplacement d’espèces en péril)"
        }
    },
    "RUL": {
        "exemption":"security",
        "exemption_rationale": {
            "en": "Potential for deliberate harm to critical infrastructure (some data include sensitive values or locations of at-risk species). Data subject to existing licensing agreement.",
            "fr": "Des dommages pourraient délibérément être causés à l’infrastructure essentielle (certaines données incluent des valeurs sensibles ou l’emplacement d’espèces en péril). Les données sont assujetties à un contrat de licence existant."
        } 
    },
    "OGDE": {
        "exemption": "security",
        "exemption_rationale": {
            "en": "Potential for deliberate harm to critical infrastructure (some data include sensitive values or locations of at-risk species). Data subject to existing licensing agreement.",
            "fr": "Des dommages pourraient délibérément être causés à l’infrastructure essentielle (certaines données incluent des valeurs sensibles ou l’emplacement d’espèces en péril). Les données sont assujetties à un contrat de licence existant."
        },  
        "access_instructions": {
            "en": "Complete and sign the [OGDE Membership Application Form](https://www.sdc.gov.on.ca/sites/MNRF-PublicDocs/EN/CMID/LIO-OGDE-MembershipForm.pdf) and submit it to the Ontario Ministry of Natural Resources and Forestry.",
            "fr": "[Remplir le formulaire](https://www.sdc.gov.on.ca/sites/MNRF-PublicDocs/EN/CMID/LIO-OGDE-MembershipForm.pdf) and submit it to the Ontario Ministry of Natural Resources and Forestry."
        }  
    },
    "OntarioParcel": {
        "exemption": "legal",
        "exemption_rationale": {
            "en": "Subject to other restrictions, do not have the right to release publicly (tri-party commercial product).",
            "fr": "Sous réserve d’autres restrictions, il est interdit de publier les données publiquement (produit commercial tripartite)."
        } 
    }
}

class OntarioGeohubHarvester(HarvesterBase):

    force_import = False
    config = None
    # modified from the DCATHarvester harvester from https://github.com/ckan/ckanext-dcat

    def _set_config(self, config_str):
        if config_str:
            try:
                self.config = json.loads(config_str)
            except ValueError:
                log.warning('Invalid harvest source config for Ontario GeoHub, ignoring it')
                self.config = {}
        else:
            self.config = {}

    def validate_config(self, config):
        if not config:
            return config

        config_obj = json.loads(config)
        if not isinstance(config_obj, dict):
            raise ValueError('Configuration must be a JSON object')

        publisher_name = config_obj.get('ontario_geohub_publisher')
        if publisher_name:
            config_obj['ontario_geohub_publisher'] = \
                normalize_geohub_publisher_name(publisher_name)

        return json.dumps(config_obj)

    def extra_schema(self):
        return {
            'ontario_geohub_publisher': [ignore_missing, unicode_safe]
        }

    def _get_content_and_type(self, url, harvest_job, page=1,
                              content_type=None):
        '''
        Gets the content and type of the given url.
        :param url: a web url (starting with http) or a local path
        :param harvest_job: the job, used for error reporting
        :param page: adds paging to the url
        :param content_type: will be returned as type
        :return: a tuple containing the content and content-type
        '''
        max_retries = 3
        for attempt in range(max_retries):
            try:

                log.debug('Getting file %s (attempt %d/%d)', url, attempt + 1, max_retries)

                # get the `requests` session object
                session = requests.Session()

                # Do NOT use stream=True: the GeoHub DCAT feed uses chunked
                # transfer-encoding + gzip, and stream=True can return empty
                # or truncated content for large responses like this one.
                r = session.get(url, timeout=120)
                content = r.content

                if not six.PY2:
                    content = content.decode('utf-8')

                if content_type is None and r.headers.get('content-type'):
                    content_type = r.headers.get('content-type').split(";", 1)[0]

                # Validate we actually got content before returning
                if not content:
                    if attempt < max_retries - 1:
                        log.warning('Empty response from %s on attempt %d, retrying...', url, attempt + 1)
                        continue
                    msg = 'Empty response from %s after %d attempts' % (url, max_retries)
                    self._save_gather_error(msg, harvest_job)
                    return None, None

                # Validate JSON is not truncated (the GeoHub feed
                # sometimes returns incomplete chunked responses)
                try:
                    json.loads(content)
                except (json.JSONDecodeError, ValueError):
                    if attempt < max_retries - 1:
                        log.warning('Truncated/invalid JSON from %s on attempt %d (%d chars), retrying...', url, attempt + 1, len(content))
                        continue
                    log.warning('Truncated/invalid JSON from %s after %d attempts, proceeding with best effort', url, max_retries)

                return content, content_type

            except requests.exceptions.HTTPError as error:
                msg = 'Could not get content from %s. Server responded with %s %s'\
                    % (url, error.response.status_code, error.response.reason)
                self._save_gather_error(msg, harvest_job)
                return None, None
            except requests.exceptions.ConnectionError as error:
                if attempt < max_retries - 1:
                    log.warning('Connection error from %s on attempt %d, retrying... %s', url, attempt + 1, error)
                    continue
                msg = '''Could not get content from %s because a
                                    connection error occurred. %s''' % (url, error)
                self._save_gather_error(msg, harvest_job)
                return None, None
            except requests.exceptions.Timeout as error:
                if attempt < max_retries - 1:
                    log.warning('Timeout from %s on attempt %d, retrying...', url, attempt + 1)
                    continue
                msg = 'Could not get content from %s because the connection timed'\
                    ' out.' % url
                self._save_gather_error(msg, harvest_job)
                return None, None
            except Exception as error:
                if attempt < max_retries - 1:
                    log.warning('Unexpected error from %s on attempt %d: %s, retrying...', url, attempt + 1, error)
                    continue
                msg = 'Could not get content from %s: %s' % (url, error)
                self._save_gather_error(msg, harvest_job)
                return None, None
        return None, None

    def _get_object_extra(self, harvest_object, key):
        '''
        Helper function for retrieving the value from a harvest object extra,
        given the key
        '''
        for extra in harvest_object.extras:
            if extra.key == key:
                return extra.value
        return None

    def _get_package_name(self, harvest_object, title):

        package = harvest_object.package
        if package is None or package.title != title:
            name = self._gen_new_name(title)
            if not name:
                raise Exception(
                    'Could not generate a unique name from the title or the '
                    'GUID. Please choose a more unique title.')
        else:
            name = package.name

        return name

    def get_original_url(self, harvest_object_id):
        obj = model.Session.query(HarvestObject). \
            filter(HarvestObject.id == harvest_object_id).\
            first()
        if obj:
            return obj.source.url
        return None

    def _read_datasets_from_db(self, guid):
        '''
        Returns a database result of datasets matching the given guid.
        '''

        datasets = model.Session.query(model.Package.id) \
                                .join(model.PackageExtra) \
                                .filter(model.PackageExtra.key == 'guid') \
                                .filter(model.PackageExtra.value == guid) \
                                .filter(model.Package.state == 'active') \
                                .all()
        return datasets

    def _get_existing_dataset(self, guid):
        '''
        Checks if a dataset with a certain guid extra already exists
        Returns a dict as the ones returned by package_show
        '''

        datasets = self._read_datasets_from_db(guid)

        if not datasets:
            return None
        elif len(datasets) > 1:
            log.error('Found more than one dataset with the same guid: {0}'
                      .format(guid))

        return p.toolkit.get_action('package_show')({}, {'id': datasets[0][0]})


    def _make_package_dict(self, geohub_dict, harvest_object, selected_odc_organization_id=None):
        english_xml = english_metadata_xml_response(geohub_dict)
        french_xml = french_metadata_xml_response(geohub_dict) 
        english_json = english_metadata_json_response(geohub_dict)

        package_dict = {
            "id": geohub_dict['ontario_geohub_id'], # Use geohub ID.
            "url": geohub_dict["dct:identifier"],
            "license_id": "other-open", 
            "title_translated": {
                "en": geohub_dict["dct:title"],
                "fr": french_title(french_xml)
            },
            "notes_translated": {
                "en": html2text.html2text(geohub_dict["dct:description"]),
                "fr": html2text.html2text(french_notes(french_xml))
            },
            "keywords": {
                "en": ontario_theme_helpers.remove_odd_chars_from_keywords(geohub_dict["dcat:keyword"]) + ['ontario-geohub'],
                "fr": ontario_theme_helpers.remove_odd_chars_from_keywords(french_keywords(french_xml)) + ['ontario-geohub']
            },
            "opened_date": get_create_date_from_json(english_json), #ontario_theme_helpers.date_parse(geohub_dict["dct:issued"], '%Y-%m-%dT%H:%M:%S.%fZ'),
            "current_as_of": get_current_as_of_date_from_json(english_json), #ontario_theme_helpers.date_parse(geohub_dict["dct:modified"], '%Y-%m-%dT%H:%M:%S.%fZ'),
            "metadata_created" : get_create_date_from_json(english_json),
            "maintainer_translated": {
                "en" : "Land Information Ontario",
                "fr" : "Information sur les terres de l'Ontario"
            },
            "maintainer_email": "lio@ontario.ca",
            "access_level": "open",
            "resources": build_resources(geohub_dict['ontario_geohub_id'], geohub_dict,
                                         english_xml, english_json),
            "update_frequency": "other",
            "exemption": "none",
            "exemption_rationale": {
                "en": "",
                "fr": ""
            },
            "name": ontario_theme_helpers.name_cleaner(geohub_dict["dct:title"]),
            "private": False,
            "state": "active",
            "groups": [{'name': 'ontario-geohub'}] # optional
        }



        if package_dict["notes_translated"]["en"] == "" and get_backup_description_from_xml(english_xml):
            package_dict["notes_translated"]["en"] = get_backup_description_from_xml(english_xml)

        # Remove ODCSYNC tag from keywords (used only for filtering, not display)
        if 'ODCSYNC' in package_dict['keywords']['en']:
            package_dict['keywords']['en'].remove('ODCSYNC')
        if 'ODCSYNC' in package_dict['keywords']['fr']:
            package_dict['keywords']['fr'].remove('ODCSYNC')

        # get license
        # license = get_license_from_xml(english_xml)
        if 'open data' in package_dict['keywords']['en']:
            package_dict["license_id"] = "OGL-ON-1.0"
            package_dict['keywords']['en'].remove('open data')

        for restricted_tag in restricted_tags:
            if restricted_tag in package_dict['keywords']['en']:
                package_dict['access_level'] = "restricted"
                package_dict["license_id"] = restricted_tag.lower()  
                package_dict.update(restricted_tags[restricted_tag])                                  
                break

        geohub_update_frequency = extract_update_frequency(package_dict['notes_translated']['en'])
        if geohub_update_frequency:
            package_dict['update_frequency'] = update_frequencies[geohub_update_frequency]

        # get maintainer name and maintainer email
        geohub_contact_info = extract_contact_info(package_dict['notes_translated']['en'])
        if geohub_contact_info:
                geohub_fr_contact_info = extract_fr_contact_info(package_dict['notes_translated']['fr'])
                package_dict['maintainer_email'] = geohub_contact_info['maintainer_email']
                package_dict['maintainer_translated']['en'] = geohub_contact_info['maintainer_name']

                if "maintainer_branch" in geohub_contact_info:
                    package_dict['maintainer_branch'] = {
                        'en' : geohub_contact_info['maintainer_branch']  
                    }
                if geohub_fr_contact_info:
                    package_dict['maintainer_translated']['fr'] = geohub_fr_contact_info['maintainer_name']
                    if "maintainer_branch" in geohub_fr_contact_info:
                        package_dict['maintainer_branch']['fr'] = geohub_fr_contact_info['maintainer_branch']                
                else: 
                    package_dict['maintainer_translated']['fr'] = package_dict['maintainer_translated']['en']
                    
                if not package_dict.get("owner_org", False) and 'ministry' in geohub_contact_info:
                    package_dict['owner_org'] = get_org_id(geohub_contact_info['ministry'])
        else:

            contact = extract_ontario_email(package_dict['notes_translated']['en'])
            if not contact:
                # Try the DCAT contactPoint email (strip mailto: prefix)
                cp_email = geohub_dict.get('dcat:contactPoint', {}).get('vcard:hasEmail', '')
                if cp_email:
                    contact = cp_email.replace('mailto:', '').strip()
            if contact:
                package_dict['maintainer_email'] = contact.strip()
                if geohub_dict["dcat:contactPoint"]["vcard:fn"]:
                    package_dict['maintainer_translated']['en'] = geohub_dict["dcat:contactPoint"]["vcard:fn"]
                elif package_dict['maintainer_email'].replace("@ontario.ca","").find(".") == -1:
                    package_dict['maintainer_translated']['en'] = package_dict['maintainer_email'].replace("@ontario.ca","").strip()
                else:
                    package_dict['maintainer_translated']['en'] = get_ontario_employee_name(package_dict['maintainer_email'])
                package_dict['maintainer_translated']['fr'] = package_dict['maintainer_translated']['en']


        # first, check whether the ministry is in the metadata
        if not package_dict.get("owner_org", False):
            ministry = get_ministry_from_xml(english_xml)
            if ministry:
                package_dict['owner_org'] = get_org_id(ministry) 
            # if it isn't there, look in the description for ministry names           
            else:
                # extract ministry
                ministry = extract_ministry(package_dict['notes_translated']['en'], package_dict['maintainer_email'])
                if ministry:
                    package_dict['owner_org'] = get_org_id(ministry)
                else:
                    ministry = publisher_ministry(geohub_dict)
                    if ministry:
                        package_dict['owner_org'] = get_org_id(ministry)
                    else:
                        package_dict['owner_org'] = get_org_id("northern-development-mines-natural-resources-and-forestry")

        # If a specific organization was selected via harvest source config, use it
        if selected_odc_organization_id:
            package_dict['owner_org'] = selected_odc_organization_id

        return package_dict


    def has_french(self, dataset_obj):
        '''Returns boolean.
        '''

        french_xml = french_metadata_xml_response(dataset_obj) 

        if french_notes(french_xml) == "Placeholder":
            return False
        else:
            return True

    def not_blacklisted(self, dataset_obj):
        if "ODCSYNC" in dataset_obj['dcat:keyword']:
            return True
        return False


    def hubtype_table(self, dataset_obj):
        '''Returns boolean.
        If hubtype_table returns true, skip the record.
        hubtype: "table" ignore it.  These are "sub-sets" of existing datasets.
        relations will be in the description for now anyway. 
        This value is only available through the geohub api and requires its own call.
        '''
        identifier = dataset_obj['ontario_geohub_id']
        geohub_endpoint = "https://geohub.lio.gov.on.ca/api/v3/datasets/{}".format(identifier)

        try:
            geohub_response = requests.get(geohub_endpoint, timeout=30)
            if geohub_response.status_code != 200:
                log.warning(
                    'hubtype_table: HTTP %s for %s, skipping hubtype check',
                    geohub_response.status_code, identifier)
                return False
            hubType = geohub_response.json()["data"]["attributes"]["hubType"]
            if hubType == "Table":
                return True
        except (requests.exceptions.RequestException, KeyError,
                ValueError, TypeError) as e:
            log.warning(
                'hubtype_table: Error checking hubtype for %s: %s',
                identifier, e)

        return False

    def info(self):
        return {
            'name': 'ontario_geohub',
            'title': 'Ontario Geohub',
            'description': 'Harvester for Ontario Geohub'
        }


    def _get_blacklist(self):
        blacklist_response = requests.get(blacklist_url)
        # Extract dataset IDs from the blacklist URLs so that the
        # comparison against ontario_geohub_id (a plain ID) works.
        # URLs look like: https://geohub.lio.gov.on.ca/datasets/<id>
        blacklist_urls = list(map(
            lambda x: x['attributes']['geohub_dataset_url'],
            blacklist_response.json()['features']))
        return [url.rstrip('/').split('/')[-1] for url in blacklist_urls]

    def _get_guids_and_datasets(self, content, selected_publisher=None):
        log.warning(f"[HARVEST] Selected publisher: {selected_publisher}")

        blacklist = self._get_blacklist()

        doc = json.loads(content)

        if isinstance(doc, list):
            # Assume a list of datasets
            datasets = doc
        elif isinstance(doc, dict):
            datasets = doc.get('dcat:dataset', [])
        else:
            raise ValueError('Wrong JSON object')

        for dataset in datasets:

            if selected_publisher:
                dataset_publisher = normalize_geohub_publisher_name(
                    dataset.get('ontario_geohub_publisher', ''))
                log.warning(f"[HARVEST] Dataset publisher: {dataset_publisher}")
                if dataset_publisher != selected_publisher:
                    log.warning(f"[HARVEST] SKIP (no match)")
                    continue                
                else:
                    log.warning(f"[HARVEST] MATCH")

            as_string = json.dumps(dataset)

            # Get identifier
            guid = dataset.get('ontario_geohub_id')

            if not guid:
                # This is bad, any ideas welcomed
                guid = sha1(as_string).hexdigest()

            # Check ODCSYNC tag first (no API call needed) before
            # expensive hubtype_table and has_french checks which each
            # make external HTTP requests per dataset.
            if guid not in blacklist and self.not_blacklisted(dataset) and not self.hubtype_table(dataset) and self.has_french(dataset):
                log.warning(f"[HARVEST] ACCEPTED GUID: {guid}")
                yield guid, as_string

    def fetch_stage(self, harvest_object):
        return True

    def _get_package_dict(self, harvest_object, selected_odc_organization_id=None):

        content = harvest_object.content

        geohub_dict = json.loads(content)

        package_dict = self._make_package_dict(geohub_dict,
                                                harvest_object,
                                                selected_odc_organization_id=selected_odc_organization_id)

        return package_dict, geohub_dict


    # -------------------------------------------------------------------
    # Single-dataset harvesting support
    #
    # These methods allow a tester to enter a single GeoHub dataset URL
    # (by name/slug or by geo-ID) in the Harvest UI instead of the full
    # DCAT feed.  This avoids the 45+ min download of all ~490 datasets.
    # -------------------------------------------------------------------

    def _is_single_dataset_url(self, url):
        """Determine if the harvest source URL points to a single GeoHub
        dataset rather than the full DCAT feed.

        Returns True for URLs like:
          - https://geohub.lio.gov.on.ca/datasets/<slug>/...
          - https://geohub.lio.gov.on.ca/maps/<id>/...
          - https://geohub.lio.gov.on.ca/documents/<id>/...
          - Raw hex IDs (32 chars, optionally with _N suffix)

        Returns False for the full DCAT feed URL:
                    - https://geohub.lio.gov.on.ca/api/feed/dcat-ap/2.1.1.json
        """
        url = url.strip()

        # Full DCAT feed URL – use the normal gather path
        if '/api/feed/' in url:
            return False

        # Single dataset URL patterns on geohub.lio.gov.on.ca
        if 'geohub.lio.gov.on.ca' in url:
            if any(p in url for p in ['/datasets/', '/maps/', '/documents/']):
                return True

        # Raw hex ID (32 chars, optionally with _N layer index suffix)
        if re.match(r'^[a-f0-9]{32}(_\d+)?$', url):
            return True

        return False

    def _extract_dataset_identifier(self, url):
        """Extract the dataset slug or ID from various GeoHub URL formats.

        Handles:
          https://geohub.lio.gov.on.ca/datasets/mnrf::contour/explore?...
          https://geohub.lio.gov.on.ca/datasets/provincially-tracked-species-1km-grid
          https://geohub.lio.gov.on.ca/maps/882a9059ec7c4881abbdb6afa0ae73e6/about
          https://geohub.lio.gov.on.ca/documents/some-doc-id
          882a9059ec7c4881abbdb6afa0ae73e6       (raw ID)
          882a9059ec7c4881abbdb6afa0ae73e6_29    (raw ID with layer index)

        Returns the identifier string (slug or ID).
        """
        url = url.strip()

        # Raw hex ID
        if re.match(r'^[a-f0-9]{32}(_\d+)?$', url):
            return url

        from urllib.parse import urlparse, unquote
        parsed = urlparse(url)
        path = unquote(parsed.path).rstrip('/')
        parts = [p for p in path.split('/') if p]

        # /datasets/<slug_or_id>/... or /maps/<id>/... or /documents/<id>/...
        for i, part in enumerate(parts):
            if part in ('datasets', 'maps', 'documents') and i + 1 < len(parts):
                return parts[i + 1]

        return None

    def _search_geohub_v3(self, param, value, harvest_job):
        """Search the GeoHub v3 search API with the given parameter.

        Returns a list of dataset dicts from the API response, or None.
        """
        import urllib.parse
        search_url = (
            "https://geohub.lio.gov.on.ca/api/v3/search?{}={}".format(
                param, urllib.parse.quote(value, safe=''))
        )

        try:
            response = requests.get(search_url, timeout=60)
            if response.status_code != 200:
                log.warning(
                    'GeoHub v3 search returned HTTP %s for %s=%s',
                    response.status_code, param, value)
                return None

            data = response.json().get('data', [])
            return data if data else None
        except Exception as e:
            log.warning(
                'Error searching GeoHub v3 API (%s=%s): %s',
                param, value, e)
            return None

    @staticmethod
    def _timestamp_to_iso(timestamp_ms):
        """Convert a Unix timestamp in milliseconds to an ISO-format string."""
        if timestamp_ms:
            try:
                return datetime.datetime.utcfromtimestamp(
                    timestamp_ms / 1000
                ).strftime('%Y-%m-%dT%H:%M:%S.000Z')
            except (TypeError, ValueError, OSError):
                pass
        return ''

    def _build_dcat_dict_from_v3(self, v3_dataset):
        """Build a DCAT-compatible dict from a GeoHub v3 search API dataset.

        The returned dict has the field names expected by _make_package_dict
        and the rest of the harvester pipeline.
        """
        dataset_id = v3_dataset.get('id', '')
        attrs = v3_dataset.get('attributes', {})

        # Build the dct:identifier URL
        slug = attrs.get('slug', '')
        if slug:
            identifier_url = (
                "https://geohub.lio.gov.on.ca/datasets/{}".format(slug))
        else:
            identifier_url = (
                "https://geohub.lio.gov.on.ca/datasets/{}".format(dataset_id))

        # ---- distributions ----
        distributions = []

        # Hub page link
        distributions.append({
            "title": "ArcGIS Hub Dataset",
            "accessURL": identifier_url,
            "format": "Web Page"
        })

        # Service URL (if available)
        server_url = attrs.get('url', '') or ''
        if server_url:
            distributions.append({
                "title": "ArcGIS GeoService",
                "accessURL": server_url,
                "format": "ArcGIS GeoService"
            })

        # Additional resources from the v3 API
        for extra_res in attrs.get('additionalResources', []):
            if extra_res.get('url'):
                distributions.append({
                    "title": extra_res.get('name', extra_res['url']),
                    "accessURL": extra_res['url'],
                    "format": ""
                })

        # Standard download-format links for feature layers
        hub_type = attrs.get('hubType', '')
        if hub_type in ('Feature Layer', 'Feature Service'):
            base_id = dataset_id.split('_')[0]
            for fmt_id, fmt_label in [('geojson', 'GeoJSON'),
                                      ('csv', 'CSV'),
                                      ('kml', 'KML')]:
                distributions.append({
                    "title": fmt_label,
                    "accessURL": (
                        "https://geohub.lio.gov.on.ca/api/download/v1"
                        "/items/{}/{}?layers=0".format(base_id, fmt_id)),
                    "format": fmt_label
                })

        # ---- contact info from metadata ----
        metadata = attrs.get('metadata', {})
        if isinstance(metadata, dict):
            metadata = metadata.get('metadata', {})
        md_contact = metadata.get('mdContact', {}) if metadata else {}
        contact_email = ''
        if isinstance(md_contact, dict):
            cnt_info = md_contact.get('rpCntInfo', {})
            if isinstance(cnt_info, dict):
                cnt_addr = cnt_info.get('cntAddress', {})
                if isinstance(cnt_addr, dict):
                    contact_email = cnt_addr.get('eMailAdd', '')

        owner = attrs.get('owner', '')

        # ---- assemble the DCAT dict ----
        dcat_dict = {
            "ontario_geohub_id": dataset_id,
            "dct:title": attrs.get('name', ''),
            "dct:description": attrs.get('description', ''),
            "dct:identifier": identifier_url,
            "dcat:keyword": (
                attrs.get('tags', [])
                if isinstance(attrs.get('tags'), list)
                else []),
            "dct:issued": self._timestamp_to_iso(attrs.get('created')),
            "dct:modified": self._timestamp_to_iso(attrs.get('modified')),
            "dcat:contactPoint": {
                "vcard:fn": owner,
                "vcard:hasEmail": contact_email
            },
            "publisher": {
                "name": attrs.get('source', '')
            },
            # Use the simplified 'distribution' key so build_resources
            # can process them (the DCAT-AP 2.0.1 key 'dcat:distribution'
            # is not read by the current code).
            "distribution": distributions,
        }
        dcat_dict["ontario_geohub_publisher"] = normalize_geohub_publisher_name(
            attrs.get('source', '') or owner)

        return dcat_dict

    def _resolve_single_dataset(self, url, harvest_job):
        """Resolve a single dataset URL to DCAT-compatible content.

        Uses the GeoHub v3 search API to look up the dataset by ID or slug,
        then constructs a DCAT-compatible dict for the harvester pipeline.

        Returns a JSON string in the same format as the DCAT feed, or None.
        """
        identifier = self._extract_dataset_identifier(url)
        if not identifier:
            self._save_gather_error(
                'Could not extract dataset identifier from URL: %s' % url,
                harvest_job)
            return None

        log.info('Resolving single GeoHub dataset: %s (identifier: %s)',
                 url, identifier)

        v3_data = None

        # Strategy 1: filter by ID (for hex IDs)
        if re.match(r'^[a-f0-9]{32}(_\d+)?$', identifier):
            v3_data = self._search_geohub_v3(
                'filter[id]', identifier, harvest_job)

        # Strategy 2: filter by slug (for slug-style identifiers)
        if not v3_data:
            v3_data = self._search_geohub_v3(
                'filter[slug]', identifier, harvest_job)

        # Strategy 3: text search as fallback
        if not v3_data:
            search_term = identifier.replace('-', ' ').replace('::', ' ')
            v3_data = self._search_geohub_v3(
                'q', search_term, harvest_job)
            if v3_data and len(v3_data) > 1:
                # Multiple results – try to find an exact match
                exact = [
                    d for d in v3_data
                    if d['id'] == identifier
                    or d.get('attributes', {}).get('slug', '') == identifier
                    or (d.get('attributes', {}).get('slug') or '').endswith(
                        '::' + identifier)
                ]
                if exact:
                    v3_data = exact

        if not v3_data:
            self._save_gather_error(
                'Could not find dataset with identifier "%s" on GeoHub. '
                'Please check the URL or dataset ID.' % identifier,
                harvest_job)
            return None

        # Use the first matching result
        dataset = v3_data[0]
        dcat_dict = self._build_dcat_dict_from_v3(dataset)

        log.info(
            'Resolved dataset: %s (ID: %s)',
            dcat_dict.get('dct:title', 'Unknown'),
            dcat_dict.get('ontario_geohub_id', 'Unknown'))

        return json.dumps({'dcat:dataset': [dcat_dict]})

    def _gather_single_dataset(self, harvest_job):
        """Gather stage for a single GeoHub dataset URL.

        This allows testing individual datasets without downloading the full
        DCAT feed (~490 datasets, 45+ min).  Filters like ODCSYNC-tag check,
        blacklist, hubtype, and French-metadata availability are skipped
        because the user has explicitly chosen this dataset for harvesting.
        """
        log.info('Single dataset mode: resolving %s', harvest_job.source.url)

        content = self._resolve_single_dataset(
            harvest_job.source.url, harvest_job)
        if not content:
            return None

        ids = []

        # Get the previous guids for this source
        query = (
            model.Session.query(HarvestObject.guid, HarvestObject.package_id)
            .filter(HarvestObject.current == True)
            .filter(
                HarvestObject.harvest_source_id == harvest_job.source.id)
        )
        guid_to_package_id = {}
        for guid, package_id in query:
            guid_to_package_id[guid] = package_id

        guids_in_db = list(guid_to_package_id.keys())
        guids_in_source = []

        doc = json.loads(content)
        datasets = doc.get('dcat:dataset', [])

        for dataset in datasets:
            as_string = json.dumps(dataset)
            guid = dataset.get('ontario_geohub_id')
            if not guid:
                guid = sha1(as_string.encode('utf-8')).hexdigest()

            guids_in_source.append(guid)

            log.info(
                'Single dataset mode: processing %s (ID: %s)',
                dataset.get('dct:title', 'Unknown'), guid)

            if guid in guids_in_db:
                # Dataset needs to be updated
                obj = HarvestObject(
                    guid=guid, job=harvest_job,
                    package_id=guid_to_package_id[guid],
                    content=as_string,
                    extras=[HarvestObjectExtra(
                        key='status', value='change')])
            else:
                # Dataset needs to be created
                obj = HarvestObject(
                    guid=guid, job=harvest_job,
                    content=as_string,
                    extras=[HarvestObjectExtra(
                        key='status', value='new')])
            obj.save()
            ids.append(obj.id)

        # Check datasets that need to be deleted
        guids_to_delete = set(guids_in_db) - set(guids_in_source)
        for guid in guids_to_delete:
            obj = HarvestObject(
                guid=guid, job=harvest_job,
                package_id=guid_to_package_id[guid],
                extras=[HarvestObjectExtra(
                    key='status', value='delete')])
            ids.append(obj.id)
            model.Session.query(HarvestObject).\
                filter_by(guid=guid).\
                update({'current': False}, False)
            obj.save()

        return ids

    def gather_stage(self, harvest_job):
        log.debug('In DCAT JSON Harvester gather_stage')

        self._set_config(harvest_job.source.config)
        selected_publisher = normalize_geohub_publisher_name(
            (self.config or {}).get('ontario_geohub_publisher', ''))
        log.warning(f"[HARVEST] Selected publisher from config: {selected_publisher}")

        # Check if the source URL points to a single dataset rather than
        # the full DCAT feed.  This enables fast testing of individual
        # datasets without downloading all ~490 entries.
        url = harvest_job.source.url
        if self._is_single_dataset_url(url):
            return self._gather_single_dataset(harvest_job)

        ids = []

        # Get the previous guids for this source
        query = \
            model.Session.query(HarvestObject.guid, HarvestObject.package_id) \
            .filter(HarvestObject.current == True) \
            .filter(HarvestObject.harvest_source_id == harvest_job.source.id)
        guid_to_package_id = {}

        for guid, package_id in query:
            guid_to_package_id[guid] = package_id

        guids_in_db = list(guid_to_package_id.keys())

        guids_in_source = []

        # Get file contents
        url = harvest_job.source.url

        previous_guids = []
        page = 1
        while True:

            try:
                content, content_type = \
                    self._get_content_and_type(url, harvest_job, page)
            except requests.exceptions.HTTPError as error:
                if error.response.status_code == 404:
                    if page > 1:
                        # Server returned a 404 after the first page, no more
                        # records
                        log.debug('404 after first page, no more pages')
                        break
                    else:
                        # Proper 404
                        msg = 'Could not get content. Server responded with ' \
                            '404 Not Found'
                        self._save_gather_error(msg, harvest_job)
                        return None
                else:
                    # This should never happen. Raising just in case.
                    raise

            if not content:
                return None

            try:

                batch_guids = []
                for guid, as_string in self._get_guids_and_datasets(
                        content, selected_publisher=selected_publisher):

                    log.debug('Got identifier: {0}'
                              .format(guid.encode('utf8')))
                    batch_guids.append(guid)

                    if guid not in previous_guids:

                        if guid in guids_in_db:
                            # actually, does dataset need to be updated?


                            # Dataset needs to be updated
                            obj = HarvestObject(
                                guid=guid, job=harvest_job,
                                package_id=guid_to_package_id[guid],
                                content=as_string,
                                extras=[HarvestObjectExtra(key='status',
                                                           value='change')])
                        else:
                            # Dataset needs to be created
                            obj = HarvestObject(
                                guid=guid, job=harvest_job,
                                content=as_string,
                                extras=[HarvestObjectExtra(key='status',
                                                           value='new')])
                        obj.save()
                        ids.append(obj.id)

                if len(batch_guids) > 0:
                    guids_in_source.extend(set(batch_guids)
                                           - set(previous_guids))
                else:
                    log.debug('Empty document, no more records')
                    # Empty document, no more ids
                    break

            except ValueError as e:
                msg = 'Error parsing file: {0}'.format(str(e))
                self._save_gather_error(msg, harvest_job)
                return None

            if sorted(previous_guids) == sorted(batch_guids):
                # Server does not support pagination or no more pages
                log.debug('Same content, no more pages')
                break

            page = page + 1

            previous_guids = batch_guids

        # Check datasets that need to be deleted
        guids_to_delete = set(guids_in_db) - set(guids_in_source)
        for guid in guids_to_delete:
            obj = HarvestObject(
                guid=guid, job=harvest_job,
                package_id=guid_to_package_id[guid],
                extras=[HarvestObjectExtra(key='status', value='delete')])
            ids.append(obj.id)
            model.Session.query(HarvestObject).\
                filter_by(guid=guid).\
                update({'current': False}, False)
            obj.save()

        return ids


    def import_stage(self, harvest_object):
        log.debug('In Ontario Geohub Harvester import_stage')
        if not harvest_object:
            log.error('No harvest object received')
            return False

        if self.force_import:
            status = 'change'
        else:
            status = self._get_object_extra(harvest_object, 'status')

        if status == 'delete':
            # Don't delete package quite yet. we'll have to manually delete it later
            context = {'model': model, 'session': model.Session,
                       'user': self._get_user_name()}

            p.toolkit.get_action('package_delete')(
                context, {'id': harvest_object.package_id})
            log.info('Deleted package {0} with guid {1}'
                     .format(harvest_object.package_id, harvest_object.guid))

            # what we need here is something to notify opendata@ontario.ca that we're deleting 
            return True

        if harvest_object.content is None:
            self._save_object_error(
                'Empty content for object %s' % harvest_object.id,
                harvest_object, 'Import')
            return False

        # Get the last harvested object (if any)
        previous_object = model.Session.query(HarvestObject) \
            .filter(HarvestObject.guid == harvest_object.guid) \
            .filter(HarvestObject.current == True) \
            .first()

        # Flag previous object as not current anymore
        if previous_object and not self.force_import:
            previous_object.current = False
            previous_object.add()

        # Get the selected organization from harvest source config (if set)
        selected_odc_organization_id = harvest_object.job.source.owner_org or None

        package_dict, geohub_dict = self._get_package_dict(
            harvest_object,
            selected_odc_organization_id=selected_odc_organization_id)
        if not package_dict:
            return False

        # owner_org is mandatory: only harvest records that map to a CKAN org.
        # Skip objects where we can't resolve a valid organization id string.
        owner_org = package_dict.get('owner_org')
        if isinstance(owner_org, six.string_types):
            owner_org = owner_org.strip()
        else:
            owner_org = None

        if not owner_org or owner_org.lower() in ('false', 'none', 'null'):
            package_dict.pop('owner_org', None)
            skip_msg = (
                'Skipping dataset guid={0}: no matching CKAN owner_org '
                'for source organization metadata'
            ).format(harvest_object.guid)
            log.warning('[HARVEST] %s', skip_msg)
            self._save_object_error(skip_msg, harvest_object, 'Import')
            return False

        package_dict['owner_org'] = owner_org
        log.warning(
            '[HARVEST] owner_org resolved guid=%s status=%s owner_org=%s',
            harvest_object.guid,
            status,
            owner_org
        )


        if not package_dict.get('name'):
            package_dict['name'] = \
                self._get_package_name(harvest_object, package_dict['title_translated']['en'])

        # copy across resource ids from the existing dataset, otherwise they'll
        # be recreated with new ids

        if status == 'change':
            existing_dataset = self._get_existing_dataset(harvest_object.guid)
            if existing_dataset:
                copy_across_resource_ids(existing_dataset, package_dict)
                # Augment existing ODC tags with GeoHub tags
                # (don't replace, merge unique tags)
                existing_keywords = existing_dataset.get('keywords', {})
                if existing_keywords:
                    if isinstance(existing_keywords, str):
                        try:
                            existing_keywords = json.loads(existing_keywords)
                        except (json.JSONDecodeError, TypeError):
                            existing_keywords = {}
                    for lang in ['en', 'fr']:
                        existing_tags = existing_keywords.get(lang, [])
                        new_tags = package_dict.get('keywords', {}).get(lang, [])
                        # Merge: keep all existing + add any new ones
                        merged = list(existing_tags)
                        for tag in new_tags:
                            if tag not in merged:
                                merged.append(tag)
                        if 'keywords' not in package_dict:
                            package_dict['keywords'] = {}
                        package_dict['keywords'][lang] = merged


        # Unless already set by an extension, get the owner organization (if
        # any) from the harvest source dataset
        
        context = {
            'user': self._get_user_name(),
            'return_id_only': True,
            'ignore_auth': True,
        }

        # Flag this object as the current one
        harvest_object.current = True
        harvest_object.add()

        try:
            if status == 'new':
                package_schema = logic.schema.default_create_package_schema()
                package_schema['id'] = [ignore_missing, unicode_safe]
                package_schema['__junk'] = [ignore]
                context['schema'] = package_schema

                # We need to explicitly provide a package 

                package_dict['id'] = geohub_dict['ontario_geohub_id']
                if 'extras' not in package_dict:
                    package_dict['extras'] = []    
                package_dict['extras'].append(
                    { 
                        "key": "guid",
                        "value": geohub_dict['ontario_geohub_id']
                    })
                #package_schema['id'] = [unicode]

                # Save reference to the package on the object
                harvest_object.package_id = package_dict['id']
                harvest_object.add()

                # Defer constraints and flush so the dataset can be indexed with
                # the harvest object id (on the after_show hook from the harvester
                # plugin)
                model.Session.execute(
                    'SET CONSTRAINTS harvest_object_package_id_fkey DEFERRED')
                model.Session.flush()

            elif status == 'change':
                package_dict['id'] = harvest_object.package_id

            if status in ['new', 'change']:
                action = 'package_create' if status == 'new' else 'package_update'
                message_status = 'Created' if status == 'new' else 'Updated'
                package_id = p.toolkit.get_action(action)(context, package_dict)
                log.info('%s dataset with id %s', message_status, package_id)

        except Exception as e:
            dataset = json.loads(harvest_object.content)
            dataset_name = dataset.get('name', '')

            self._save_object_error('Error importing dataset %s: %r / %s' % (dataset_name, e, traceback.format_exc()), harvest_object, 'Import')
            return False

        finally:
            model.Session.commit()

        return True


def copy_across_resource_ids(existing_dataset, harvested_dataset):
    '''Compare the resources in a dataset existing in the CKAN database with
    the resources in a freshly harvested copy, and for any resources that are
    the same, copy the resource ID into the harvested_dataset dict.
    '''
    # take a copy of the existing_resources so we can remove them when they are
    # matched - we don't want to match them more than once.
    existing_resources_still_to_match = \
        [r for r in existing_dataset.get('resources')]

    # we match resources a number of ways. we'll compute an 'identity' of a
    # resource in both datasets and see if they match.
    # start with the surest way of identifying a resource, before reverting
    # to closest matches.
    resource_identity_functions = [
        lambda r: r['uri'],  # URI is best
        lambda r: (r['url'], r['title'], r['format']),
        lambda r: (r['url'], r['title']),
        lambda r: r['url'],  # same URL is fine if nothing else matches
    ]

    for resource_identity_function in resource_identity_functions:
        # calculate the identities of the existing_resources
        existing_resource_identities = {}
        for r in existing_resources_still_to_match:
            try:
                identity = resource_identity_function(r)
                existing_resource_identities[identity] = r
            except KeyError:
                pass

        # calculate the identities of the harvested_resources
        for resource in harvested_dataset.get('resources'):
            try:
                identity = resource_identity_function(resource)
            except KeyError:
                identity = None
            if identity and identity in existing_resource_identities:
                # we got a match with the existing_resources - copy the id
                matching_existing_resource = \
                    existing_resource_identities[identity]
                resource['id'] = matching_existing_resource['id']
                # make sure we don't match this existing_resource again
                del existing_resource_identities[identity]
                existing_resources_still_to_match.remove(
                    matching_existing_resource)
        if not existing_resources_still_to_match:
            break

today = datetime.datetime.now()
today_iso = today.strftime("%Y-%m-%d")

# pattens for digging around in the ontario geohub description
geohub_contact_pattern = re.compile("\*\*Contact(?:[\*\s\n]*)([a-zA-Z0-9&\(\)\/\. \-,\s\n@ \]\[]*)(?:\s*)(?:\n*)\[([\na-zA-Z0-9\.]*@[oO]ntario.ca)\]")
geohub_fr_contact_pattern = re.compile(u"\*\*Personne-resource(?:[\*\s\n]*)([\u00A0-\u017Fa-zA-Z0-9&\(\)\/\. \-,\s\n@ \]\[]*)(?:\s*)(?:\n*)\[([\na-zA-Z0-9\.]*@[oO]ntario.ca)\]")
ontario_email_pattern = re.compile("[a-zA-Z0-9\.]*@[oO]ntario.ca")
iso_date_pattern = re.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}")
geohub_update_frequency_pattern = re.compile("\*\*Maintenance and Update Frequency(?:[\s\n]*)\*\*(?:[\s\n]*)([a-zA-Z0-9 ]*):")

''' calls_to_infogo hold previous calls to infogo in the same harvest/session
        so that we don't make multiples of the same call
'''
calls_to_infogo = {}

''' ministries is used to look for mention of ministries in the body of the english 
        description to determine what ministry the dataset belongs to.
'''
ministries = {
    "Ontario Ministry of Natural Resources and Forestry" : "northern-development-mines-natural-resources-and-forestry",
    #"Ontario Ministry of Natural Resources" : "natural-resources-and-forestry",
    "Ontario Ministry of Children, Community and Social Services" : "children-community-and-social-services",
    "Ontario Ministry of Health" : "health",
    "Ontario Ministry of Long-term care" : "long-term-care",
    "Ontario Ministry of Government and Consumer Services" : "government-and-consumer-services",
    "Ontario Ministry of Environment, Conservation and Parks" : "environment-conservation-and-parks",
    "Ontario Ministry of Energy, Northern Development and Mines" : "northern-development-mines-natural-resources-and-forestry",
    "Ontario Ministry of Municipal Affairs and Housing" : "municipal-affairs-and-housing",
    "Ontario Ministry of Education" : "education",
    "Ontario Ministry of Agriculture Food and Rural Affairs" : "agriculture-food-and-rural-affairs",
    "Ontario Ministry of Transportation" : "transportation"
}

''' geohub_metadata_ministry_names maps the terms that show up in geohub's
        metadata to the corresponding organization_name in the catalogue
'''
geohub_metadata_ministry_names = {
    "Ontario Ministry of Natural Resources and Forestry" : "northern-development-mines-natural-resources-and-forestry",
    "Ontario Ministry of Natural Resources" : "northern-development-mines-natural-resources-and-forestry",
    "Ontario Ministry of Agriculture, Food and Rural Affairs" : "agriculture-food-and-rural-affairs",
    "Ontario Ministry of the Environment, Conservation and Parks" : "environment-conservation-and-parks",
    "Ontario Ministry of Transportation" : "transportation",
    "Ontario Ministry of Health" : "health",
    "Ontario Ministry of Education" : "education",
    "Ontario Ministry of Municipal Affairs and Housing" : "municipal-affairs-and-housing",
    "Ontario Ministry of Natural Resources and Forestry - Provincial Mapping Unit" : "northern-development-mines-natural-resources-and-forestry",
    "Ontario Ministry of Indigenous Affairs": "indigenous-affairs",
    "Ontario Ministry of Energy, Northern Development and Mines" : "northern-development-mines-natural-resources-and-forestry"    
}

''' infogo_ministry_names maps the ministry labels in infogo to the 
        corresponding organization_name in the catalogue
'''
infogo_ministry_names = {
    "Agriculture, Food and Rural Affairs" : "agriculture-food-and-rural-affairs",
    "Attorney General" : "attorney-general",
    "Cabinet Office" : "cabinet-office",
    "Children, Community and Social Services" : "children-community-and-social-services",
    "Colleges and Universities" : "colleges-and-universities",
    "Economic Development, Job Creation and Trade" : "economic-development-job-creation-and-trade",
    "Education" : "education",
    "Energy, Northern Development and Mines" : "northern-development-mines-natural-resources-and-forestry",
    "Environment, Conservation and Parks" : "environment-conservation-and-parks",
    "Finance" : "finance",
    "Francophone Affairs" : "francophone-affairs",
    "Government and Consumer Services" : "government-and-consumer-services",
    "Health" : "health",
    "Heritage, Sport, Tourism and Culture Industries" : "heritage-sport-tourism-and-culture-industries",
    "Indigenous Affairs" : "indigenous-affairs",
    "Infrastructure" : "infrastructure",
    "Intergovernmental Affairs" : "intergovernmental-affairs",
    "Labour, Training and Skills Development" : "labour-training-and-skills-development",
    "Long-Term Care" : "long-term-care",
    "Municipal Affairs and Housing" : "municipal-affairs-and-housing",
    "Natural Resources and Forestry" : "northern-development-mines-natural-resources-and-forestry",
    "Seniors and Accessibility" : "seniors-and-accessibility",
    "Solicitor General" : "solicitor-general",
    "Transportation" : "transportation",
    "Treasury Board Secretariat" : "treasury-board-secretariat"
}

publisher_ministries = {
    "Ontario Ministry of Agriculture, Food and Rural Affairs" : "agriculture-food-and-rural-affairs",
    "Ontario Ministry of Natural Resources and Forestry" : "northern-development-mines-natural-resources-and-forestry",
    "Ontario Ministry of Natural Resources" : "northern-development-mines-natural-resources-and-forestry",
    "Land Information Ontario" : "northern-development-mines-natural-resources-and-forestry",
    "OMAFRA" : "agriculture-food-and-rural-affairs",
    "OMAFA" : "agriculture-food-and-rural-affairs",
    "Ontario Ministry of Energy, Northern Development and Mines" : "northern-development-mines-natural-resources-and-forestry",
    "Ontario Ministry of Municipal Affairs and Housing" : "municipal-affairs-and-housing",
    "Ontario Ministry of the Environment, Conservation and Parks" : "environment-conservation-and-parks",
    "Ontario Ministry of Agriculture, Food, and Rural Affairs" : "agriculture-food-and-rural-affairs",
    "Ontario Ministry of Agriculture, Food, and Rural Affairs, OMAFRA" : "agriculture-food-and-rural-affairs",
    "OMAFRA- Environmental Management Branch" : "agriculture-food-and-rural-affairs",
    "Ontario Ministry of Natural Resources and Forestry - Provincial Mapping Unit" : "northern-development-mines-natural-resources-and-forestry",
    "Ontario Ministry of Health" : "health",
    "Ontario Ministry of Education" : "education",
    "Ontario Ministry of Indigenous Affairs" : "indigenous-affairs",
    "Ontario Ministry of Northern Development, Mines, Natural Resources and Forestry" : "northern-development-mines-natural-resources-and-forestry",
    "Ontario Ministry of Transportation" : "transportation"
}


def get_org_id(organization_name):  
    ''' return the local org id that matches the organization name
    '''
    if not organization_name:
        return None

    source_name = organization_name.strip()
    normalized_name = normalize_geohub_publisher_name(source_name)
    mapped_name = publisher_ministries.get(source_name) or \
        publisher_ministries.get(normalized_name)

    organization_lookup = _get_active_organization_lookup()

    candidate_keys = [
        source_name,
        normalized_name,
        mapped_name,
        (mapped_name or '').replace('-', ' '),
        (mapped_name or '').replace('-', ' ').title(),
    ]

    seen_keys = set()
    for candidate in candidate_keys:
        if not candidate:
            continue
        key = candidate.strip().lower()
        if key in seen_keys:
            continue
        seen_keys.add(key)

        organization_id = organization_lookup.get(key)
        if organization_id:
            return organization_id

    warning_key = (source_name, normalized_name, mapped_name)
    if warning_key not in _missing_org_warning_cache:
        _missing_org_warning_cache.add(warning_key)
        log.warning(
            '[HARVEST] No CKAN organization match for source org="%s" '
            '(normalized="%s", mapped="%s")',
            source_name,
            normalized_name,
            mapped_name
        )

    return None


def call_to_infogo(email):
    if email not in calls_to_infogo:
        try:
            infogo_request = requests.get(
                "http://www.infogo.gov.on.ca/infogo/v1/individuals/search?&keywords={}".format(email),
                timeout=15)
            calls_to_infogo[email] = infogo_request.json()
        except (requests.exceptions.RequestException, ValueError, TypeError) as e:
            log.warning('InfoGo API call failed for %s: %s', email, e)
            calls_to_infogo[email] = {}
    return calls_to_infogo[email]

''' update_frequencies is all the update frequencies that appear in the
        description of a dataset on geohub mapped to catalogue update frequency values 
'''
update_frequencies = {
    "Irregular": "periodically",
    "Continual": "current",
    "Annually": "yearly",
    "Unknown": "other",
    "Weekly": "weekly",
    "Monthly": "monthly",
    "Fortnightly": "fortnightly",
    "Quarterly": "quarterly",
    "Biannually": "biannually",
    "As needed": "as_required",
    "On going": "as_required",
    "Not planned": "never",
    "As Needed": "as_required"
}

def extract_update_frequency(description):
    '''
    Geohub records often have an update frequency in their description.

    It looks like this:

    Maintenance and Update Frequency
    As needed: data is updated as deemed necessary

    We're using regular expressions to peel out any update frequency in the english description
    '''
    search_results = geohub_update_frequency_pattern.findall(description)
    if len(search_results) > 0:
        return search_results[0].strip()
    else:
        return None


geohub_description_fr_ministry_names = {
    "Ministère des Richesses naturelles et des Forêts de l'Ontario": "northern-development-mines-natural-resources-and-forestry",
    "Ministère de l'Agriculture, de l'Alimentation et des Affaires rurales de l'Ontario": "agriculture-food-and-rural-affairs",
    "Ministère des Richesses naturelles et des Forêts": "northern-development-mines-natural-resources-and-forestry",
    "Ministère de l’Environnement, de la Protection de la nature et des Parcs de l'Ontario": "environment-conservation-and-parks",    
    "Ministère de l’Environnement, de la Protection de la nature et des Parcs": "environment-conservation-and-parks",
    "Ministère des Richesses naturelles": "northern-development-mines-natural-resources-and-forestry",
    "Ministère de l’Énergie, Développement du Nord et Mines": "energy-northern-development-and-mines"
}


def extract_fr_contact_info(description):
    ''' In order to get maintainer_name in french (we already know email and ministry),
            we extract french contact info (then strip out email and ministry and use
            the rest as the maintainer name)

    '''
    search_results = geohub_contact_pattern.findall(description)
    if len(search_results) > 0:
        contact_info = search_results[0]
        # split into maintainer name, ministry, branch, email
        contact_info_dict = {
            "maintainer_email" : contact_info[1]
        }
        non_email_contact_info = contact_info[0].replace("\n"," ").replace("  "," ")
        for ministry in geohub_description_fr_ministry_names.keys():
            ministry_pattern = re.compile("("+ministry+"[\s\n-,.]*)")
            look_for_ministry = ministry_pattern.findall(non_email_contact_info, re.IGNORECASE)
            if len(look_for_ministry) > 0:
                ministry_result = look_for_ministry[0]
                # there's a ministry name in there. let's take it out and use the rest as a maintainer name
                non_email_contact_info = non_email_contact_info.replace(ministry_result[0], "").strip()
                contact_info_dict['ministry'] = geohub_description_fr_ministry_names[ministry.strip()]
                break
            if non_email_contact_info.lower().find("direction") != -1:
                contact_info_chunks = non_email_contact_info.split(",")
                for chunk in contact_info_chunks:
                    if chunk.lower().find("direction") != -1:
                       contact_info_dict['maintainer_branch'] = chunk
                       break  
        contact_info_dict['maintainer_name'] = non_email_contact_info.strip()
        if contact_info_dict['maintainer_name'][-1] in ["-",","]:
            contact_info_dict['maintainer_name'] = contact_info_dict['maintainer_name'][:-1].strip() 
        return contact_info_dict
    else:
        return None


geohub_description_ministry_names = {
    "Ontario Ministry of Natural Resources and Forestry": "northern-development-mines-natural-resources-and-forestry",
    "Ontario Ministry of Agriculture, Food and Rural Affairs": "agriculture-food-and-rural-affairs",
    "Ontario Ministry of the Environment, Conservation and Parks": "environment-conservation-and-parks",
    "Ontario Ministry of Natural Resources": "northern-development-mines-natural-resources-and-forestry",
    "Ministry of Natural Resources and Forestry": "northern-development-mines-natural-resources-and-forestry",
    "Ministry of the Environment Conservation and Parks": "environment-conservation-and-parks",
    "Ministry of the Environment, Conservation and Parks": "environment-conservation-and-parks",
    "Ministry of Energy, Northern Development and Mines": "energy-northern-development-and-mines",
    "Ministry of Environment, Conservation and Parks" : "environment-conservation-and-parks",
    "Ministry of Health and Long-Term Care (MOHLTC)": "health"
}


def extract_contact_info(description):
    search_results = geohub_contact_pattern.findall(description)
    if len(search_results) > 0:
        contact_info = search_results[0]
        # split into maintainer name, ministry, branch, email
        contact_info_dict = {
            "maintainer_email" : contact_info[1].strip()
        }
        non_email_contact_info = contact_info[0].replace("\n"," ").replace("  "," ")
        for ministry in geohub_description_ministry_names.keys():
            ministry_pattern = re.compile("("+ministry+"[\s\n-,.]*)")
            look_for_ministry = ministry_pattern.findall(non_email_contact_info, re.IGNORECASE)
            if len(look_for_ministry) > 0:
                # there's a ministry name in there. let's take it out and use the rest as a maintainer name
                non_email_contact_info = non_email_contact_info.replace(look_for_ministry[0], "").strip()
                contact_info_dict['ministry'] = geohub_description_ministry_names[ministry.strip()]
                break
            if non_email_contact_info.lower().find("branch") != -1:
                contact_info_chunks = non_email_contact_info.split(",")
                for chunk in contact_info_chunks:
                    if chunk.lower().find("branch") != -1:
                       contact_info_dict['maintainer_branch'] = chunk
                       break  
        contact_info_dict['maintainer_name'] = non_email_contact_info.strip()
        if contact_info_dict['maintainer_name'][-1] in ["-",","]:
            contact_info_dict['maintainer_name'] = contact_info_dict['maintainer_name'][:-1].strip()
        return contact_info_dict
    else:
        return None


def extract_date(date_str):
    search_results = iso_date_pattern.findall(date_str)
    if len(search_results) > 0:
        return search_results[0]
    else:
        return None


def publisher_ministry(geohub_dict):
    publisher_name = normalize_geohub_publisher_name(
        geohub_dict.get('ontario_geohub_publisher', ''))
    if publisher_name and publisher_name in publisher_ministries:
        return publisher_ministries[publisher_name]

    # Support both v3-API style ('publisher' / 'name') and DCAT feed
    # style ('dct:publisher' / 'foaf:name').
    pub = geohub_dict.get('publisher') or geohub_dict.get('dct:publisher')
    if pub:
        pub_name = normalize_geohub_publisher_name(
            pub.get('name') or pub.get('foaf:name', ''))
        if pub_name in publisher_ministries:
            return publisher_ministries[pub_name]
    return False

def extract_ministry(description, email):
    for ministry_search_text, ministry_name in ministries.items():
        if description.find(ministry_search_text) != -1:
            return ministry_name

    infogo_response = call_to_infogo(email)
    if 'individuals' in infogo_response:
        for individual_record in infogo_response['individuals']:
            if individual_record['topOrgName'] in infogo_ministry_names:
                return infogo_ministry_names[individual_record['topOrgName']]
    else:
        return "northern-development-mines-natural-resources-and-forestry"


def extract_ontario_email(description):
    search_results = ontario_email_pattern.findall(description)
    if len(search_results) > 0:
        return search_results[0]
    else:
        return None


def get_ontario_employee_name(email):
    return " ".join(list(map(lambda x: x.capitalize(), re.sub(r'[0-9]+', '', email).replace("@ontario.ca","").split(".", 1))))
    # request timing out right now. reenable this later
    infogo_response = call_to_infogo(email)
    if infogo_response['total'] > 0:
        calls_to_infogo[email] = infogo_response
        return " ".join(list(map(lambda x: infogo_response['individuals'][0][x] if x in infogo_response['individuals'][0] else "", ["firstname", "middleName","lastName"])))
    else:
        return " ".join(list(map(lambda x: x.capitalize(), re.sub(r'[0-9]+', '', email).replace("@ontario.ca","").split(".", 1))))


def french_notes(french_xml):
    '''Returns the french notes from the xml response.
    <dataIdInfo><idAbs>
    '''
    french_notes_text = 'Placeholder'

    root = french_xml
    #root = lxml.etree.fromstring(french_xml.content)
    french_notes_element = root.xpath("//dataIdInfo/idAbs")
    if french_notes_element:
        french_notes_text = french_notes_element[0].text

    return french_notes_text


def french_title(french_xml):
    '''Returns the french title from the xml response.
    <dataIdInfo><idCitation><resTitle>
    '''
    french_title_text = 'Placeholder'

    root = french_xml
    #root = lxml.etree.fromstring(french_xml.content)
    french_title_element = root.xpath("//dataIdInfo/idCitation/resTitle")
    if french_title_element:
        french_title_text = french_title_element[0].text

    return french_title_text


def french_keywords(french_xml):
    '''Returns array of french keywords from the xml response.
    searchKeys matches data.json keywords that are used for english record.
    '''

    french_keywords = []

    root = french_xml
    #root = lxml.etree.fromstring(french_xml.content)
    french_keywords_element = root.xpath("//searchKeys")
    if french_keywords_element:
        for keyword in french_keywords_element[0]:
            if len(keyword.text) < 100:
                french_keywords.append(keyword.text)
      
    return french_keywords


def get_license_from_xml(root):
    '''Returns the license for that dataset.
    '''
    license_path = root.xpath("//dataIdInfo/resConst/LegConsts/useLimit")
    if license_path:
        license_text = license_path[0].text
        return license_text
    return False

def get_backup_description_from_xml(root):
    '''Returns the revise date (comparable to data_range_end) for that dataset.
    '''
    desc_path = root.xpath("//dataIdInfo/idPurp")
    if desc_path:
        desc_text = desc_path[0].text
        if desc_text:
            return desc_text
    return False



def get_data_last_updated_from_json(json_metadata):
    '''
            json[“data”][“attributes”][“modified”] – Date that the data was last updated.

    '''
    return datetime.datetime.utcfromtimestamp(json_metadata["data"]["attributes"]["modified"]/1000).isoformat()


def get_current_as_of_date_from_json(json_metadata):
    '''
            This can be obtained from a combination of two values.

            Using this API endpoint: https://opendata.arcgis.com/api/v3/datasets/{id}

            json[“data”][“attributes”][“itemModified”] – Date that the ArcGIS Online item was last modified, including metadata updates. Equivalent to ModDate + ModTime from the metadata XML

            json[“data”][“attributes”][“modified”] – Date that the data was last updated.

            The values returned are unix timestamps in milliseconds. Compare and use the larger one of the two.

    '''
    current_as_of = max(json_metadata["data"]["attributes"]["itemModified"],json_metadata["data"]["attributes"]["modified"])
    return datetime.datetime.utcfromtimestamp(current_as_of/1000).isoformat()

def get_revise_date_from_xml(root):
    '''Returns the revise date (comparable to data_range_end) for that dataset.
    '''
    revise_date_path = root.xpath("//metadata/Esri/ModDate") #//dataIdInfo/idCitation/date/reviseDate
    if revise_date_path:
        revise_date_text = revise_date_path[0].text
        revise_date = extract_date(revise_date_text)
        if revise_date:
            return revise_date
    return False

def get_create_date_from_json(json_metadata):
    return datetime.datetime.utcfromtimestamp(json_metadata["data"]["attributes"]["created"]/1000).isoformat()

def get_create_date_from_xml(root):
    '''Returns the create date (comparable to data_range_start) for that dataset.
    '''
    create_date_path = root.xpath("//metadata/Esri/CreaDate") #//dataIdInfo/idCitation/date/createDate
    if create_date_path:
        create_date_text = create_date_path[0].text
        create_date = extract_date(create_date_text)
        if create_date:
            return create_date
    return False


def get_ministry_from_xml(root):
    '''Returns the license for that dataset.
    '''
    ministry_path = root.xpath("//dataIdInfo/idCitation/citRespParty/rpOrgName")
    if ministry_path:
        ministry = ministry_path[0].text
        if ministry in geohub_metadata_ministry_names:
            return geohub_metadata_ministry_names[ministry]
    return False

def get_file_type(resource):
    '''
        Returns the file format of a resource.
        Handles both flat dicts (from v3 API / normalized) and DCAT-prefixed
        dicts (dct:format may be {"@id": "ftype/CSV"}).
    '''
    # Try flat format key first (already normalized or from v3 API)
    fmt = resource.get('format') or resource.get('dct:format', '')
    if isinstance(fmt, dict):
        fmt = fmt.get('@id', '')
    if isinstance(fmt, str) and fmt.startswith('ftype/'):
        fmt = fmt[len('ftype/'):]
    if fmt:
        return fmt

    media = resource.get('mediaType') or resource.get('dcat:mediaType', '')
    if isinstance(media, dict):
        media = media.get('@id', '')
    if media:
        return media

    raw_url = resource.get('accessURL') or resource.get('dcat:accessURL', '')
    if isinstance(raw_url, dict):
        raw_url = raw_url.get('@id', '')
    if raw_url:
        from urllib.parse import urlparse as _urlparse
        import os
        path = _urlparse(raw_url).path
        ext = os.path.splitext(path)[1]
        if ext:
            return ext
    return False

def _normalize_dcat_distribution(dist_entry):
    """Convert a DCAT-AP 2.0.1 distribution entry to the flat format
    expected by build_resources / get_file_type.

    DCAT feed entries look like:
        {"dct:title": "CSV",
         "dcat:accessURL": {"@id": "https://..."},
         "dct:format": {"@id": "ftype/CSV"}}

    The v3-API path already produces flat dicts:
        {"title": "CSV", "accessURL": "https://...", "format": "CSV"}

    This helper normalises to the flat style so downstream code works
    regardless of which path produced the dict.
    """
    norm = {}

    # title
    norm['title'] = (
        dist_entry.get('title')
        or dist_entry.get('dct:title', '')
    )

    # accessURL  –  may be a plain string or {"@id": "..."}
    raw_url = dist_entry.get('accessURL') or dist_entry.get('dcat:accessURL', '')
    if isinstance(raw_url, dict):
        raw_url = raw_url.get('@id', '')
    norm['accessURL'] = raw_url

    # format  –  may be a plain string or {"@id": "ftype/CSV"}
    raw_fmt = dist_entry.get('format') or dist_entry.get('dct:format', '')
    if isinstance(raw_fmt, dict):
        raw_fmt = raw_fmt.get('@id', '')
    # Strip the "ftype/" prefix that DCAT uses (e.g. "ftype/CSV" → "CSV")
    if isinstance(raw_fmt, str) and raw_fmt.startswith('ftype/'):
        raw_fmt = raw_fmt[len('ftype/'):]
    norm['format'] = raw_fmt

    # description (optional)
    norm['description'] = (
        dist_entry.get('description')
        or dist_entry.get('dct:description', '')
    )

    # mediaType (optional)
    raw_media = dist_entry.get('mediaType') or dist_entry.get('dcat:mediaType', '')
    if isinstance(raw_media, dict):
        raw_media = raw_media.get('@id', '')
    norm['mediaType'] = raw_media

    return norm


def build_resources(id, geohub_dict, english_xml, english_json):
    ''' Harvest all resources/files for the dataset
    '''
    metadata_titles = ["ArcGIS Hub Dataset","Esri Rest API"]
    resources = []
    resource_links = []
    # Support both the v3-API key ('distribution') and the DCAT feed key
    raw_distributions = geohub_dict.get('distribution') or geohub_dict.get('dcat:distribution')
    if raw_distributions:
        for raw_resource in raw_distributions:
            resource = _normalize_dcat_distribution(raw_resource)
            resource_dict = { 
                        "name_translated": {
                            "en": resource["title"],
                            "fr": resource["title"]
                        },
                        "type": 'data',
                        "url": resource.get("accessURL", "") }
            resource_links.append(resource.get("accessURL", ""))
            revise_date = get_revise_date_from_xml(english_xml)
            resource_dict['data_range_end'] = get_data_last_updated_from_json(english_json)
            if revise_date:
                resource_dict['data_last_updated'] = revise_date
            create_date = get_create_date_from_xml(english_xml)
            if create_date:
                resource_dict['data_range_start'] = create_date
            file_type = get_file_type(resource)
            if file_type:
                resource_dict['format'] = file_type
            if resource.get("title", "") in metadata_titles:
                resource_dict['type'] = "metadata"
            resources.append(
                        resource_dict
                      ) # Some resources are missing links

    distribution = english_xml.xpath("//distInfo/distTranOps/onLineSrc")

    for resource in distribution:
        if len(resource.xpath("//linkage")) == 1 and len(resource.xpath("//orName")) == 1:
            link = resource.xpath("//linkage")[0].text
            name= resource.xpath("//orName")[0].text

            if link not in resource_links:
                resource_dict = { 
                            "name_translated": {
                                "en": name,
                                "fr": name
                            },
                            "type": 'data',
                            "url": link }
                revise_date = get_revise_date_from_xml(english_xml)
                resource_dict['data_range_end'] = get_data_last_updated_from_json(english_json)
                if revise_date:
                    resource_dict['data_last_updated'] = revise_date
                create_date = get_create_date_from_xml(english_xml)
                if create_date:
                    resource_dict['data_range_start'] = create_date
                file_type = get_file_type(resource)
                if file_type:
                    resource_dict['format'] = file_type
                if name in metadata_titles:
                    resource_dict['type'] = "metadata"

                resources.append(
                            resource_dict
                          ) # Some resources are missing links


    # Add in the metadata URLs
    resources.append(
                  { 
                    "name_translated": {
                        "en": "Metadata in ISO 19115 NAP Format",
                        "fr": "Métadonnées dans ISO 19115"
                        },
                    "type": 'technical_document',
                    "format": "html",
                    "url": "https://www.arcgis.com/sharing/rest/content/items/{}/info/metadata/metadata.xml?format=default&output=html".format(id) })
    resources.append(
                  { 
                    "name_translated": {
                        "en": "Metadata in Full Esri Format",
                        "fr": "Métadonnées au format ESRI"
                      },
                    "type": 'technical_document',
                    "format": "xml",
                    "url": metadata_url(id) })

    # Include resources from XML, putting them first.
    additional_resources = additional_resources_from_xml(english_xml)
    resource_links = list(map(lambda x: x['url'], resources))
    for r in additional_resources:
        if r['url'] not in resource_links:
            resources.append(r)

    return resources


def geohub_french_id_from_xml(dataset_obj):
    '''Return the french id from the english xml or empty string if not record.
    It's only available in the ?format=default version, so a seperate call.
    '''

    # Prime for no French ID.
    geohub_french_record_id_text = ''

    # Get resources from XML.
    root = english_metadata_xml_response(dataset_obj)

    # Get the element then grab the text.
    
    # this works if using xml?format=default which I thought I had to use to access the ID value but turns out I don't. this also required namespacing.
    #geohub_french_record_id_element = root.xpath("//default:MD_Identifier[default:authority/default:CI_Citation/default:title/gco:CharacterString/text() = 'Ontario GeoHub French Record ID']/default:code/gco:CharacterString", namespaces=ns)
    geohub_french_record_id_element = root.xpath("//citId[identAuth/resTitle/text() = 'Ontario GeoHub French Record ID']/identCode")
    if geohub_french_record_id_element:
        geohub_french_record_id_text = geohub_french_record_id_element[0].text

    return geohub_french_record_id_text



def identifier_from_url(identifier):
    '''Accepts a string of the identifier URL that's part of data.json for 
    each dataset/record, and parses into just ID.
    '''
    # ID is at the end but sometimes there's extra bits we dont want that are
    # the underlying layer index.
    #identifier = identifier_url.split('/')[-1].split('_')[0]
    identifier = identifier.split('_')[0]
    return identifier


def identifier_from_url_with_index(identifier_url):
    '''Returns a string id with the layer index if it exists.
    '''
    identifier = identifier_url.split('/')[-1] # keep layer index.
    return identifier

def metadata_url(id):
    '''Returns a url for the metadata XML.
    '''
    return "https://www.arcgis.com/sharing/rest/content/items/{}/info/metadata/metadata.xml".format(id)


def additional_resources_from_xml(root):
    '''Returns array of dicts for additional resources.
    '''
    additional_resources = []
    for onLineSrc in root.iter('onLineSrc'):
        # Some datasets/records don't have additional resources so setting 
        # default values. They seem to use the data source instead without a name.
        additional_resources.append(
            {"url": onLineSrc.findtext('linkage'),
             "name_translated": {
                "en": onLineSrc.findtext('orName',
                                        default=onLineSrc.findtext('linkage')),
                "fr": onLineSrc.findtext('orName',
                                        default=onLineSrc.findtext('linkage'))
            },
             "type": 'data'}
            )
    return additional_resources

def english_metadata_json_response(dataset_obj):
    english_id = dataset_obj['ontario_geohub_id']
    english_metadata_url = "https://opendata.arcgis.com/api/v3/datasets/{}".format(english_id)
    metadata_json_request = requests.get(english_metadata_url)
    return metadata_json_request.json()
    

def english_metadata_xml_response(dataset_obj):
    '''Returns the english metadata xml
    '''

    english_id = identifier_from_url(dataset_obj['ontario_geohub_id'])
    english_metadata_url = metadata_url(english_id)
    try:
        metadata_xml_request = requests.get(english_metadata_url, timeout=60)
        # parse the response to get the additional resources.
        return lxml.etree.fromstring(metadata_xml_request.content)
    except (requests.exceptions.RequestException,
            lxml.etree.XMLSyntaxError) as e:
        log.warning(
            'Exception raised. Cannot load/parse english metadata for '
            'english_id: %s. Using empty root element instead. %r',
            english_id,
            e)
        return lxml.etree.Element("root")

def french_metadata_xml_response(dataset_obj):
    '''Returns the french metadata xml.
    To build this we need to grab the french values for some fields. Easiest
    so far is to loop over english and make a call to the matching french
    record. This will be used for a few payload values so calling once here.
    '''

    english_id = dataset_obj['ontario_geohub_id']
    french_id = geohub_french_id_from_xml(dataset_obj)
    if not french_id:
        return lxml.etree.Element("root")

    #french_id = identifier_from_url(french_id)
    french_metadata_xml_url = metadata_url(identifier_from_url(french_id))

    try:
        # Now can make request for xml.
        french_xml_response = requests.get(french_metadata_xml_url, timeout=60)
        # TODO: fix bug.  if geohub_french_id_from_xml: continue on, else abort french and use defaults. in some cases there is an ID but the request fails (outdated data I think). In this case it tries to parse the html I think and uses the defaults (den-site is an example).
        # TODO: Error handle for non-existent French record.
        french_xml_root = lxml.etree.fromstring(french_xml_response.content)
    except (requests.exceptions.RequestException,
            lxml.etree.XMLSyntaxError) as e:
        logging.warning('Exception raised. Cannot load/parse response for english_id: {} and french_id: {}. Using empty root element instead. {}'
            .format(english_id, french_id, repr(e)))
        # Create an empty root element 
        french_xml_root = lxml.etree.Element("root")

    return french_xml_root