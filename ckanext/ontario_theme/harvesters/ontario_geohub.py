# coding=utf-8

'''
This harvester works specifically for the Ontario Geohub geospatial catalogue at:

https://geohub.lio.gov.on.ca/api/feed/dcat-ap/2.1.1.json

''' 
import json
import datetime
import re
import logging
import time
import requests
import html2text
import lxml.etree
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
GEOHUB_PUBLISHER_OPTIONS_CACHE_TTL = datetime.timedelta(hours=24)
GEOHUB_BLACKLIST_CACHE_TTL = datetime.timedelta(minutes=15)
GEOHUB_FULL_FEED_REJECTION_LOG_LIMIT = 25

blacklist_url = "https://services9.arcgis.com/a03W7iZ8T3s5vB7p/ArcGIS/rest/services/odc_sync_blacklist_vw/FeatureServer/0/query?where=1%3D1&outFields=geohub_dataset_url&f=json"

_geohub_publisher_options_cache = {
    'expires_at': None,
    'options': None,
}

_catalog_organization_cache = {
    'expires_at': None,
    'index': None,
}

_blacklist_cache = {
    'expires_at': None,
    'ids': None,
}


def _requests_get_with_retry(url, timeout=30, max_retries=3, backoff=5,
                             session=None, **kwargs):
    '''GET wrapper with retries for transient network failures.

    Retries on connection errors and timeouts, and raises the final
    exception if all attempts fail.
    '''
    client = session or requests
    for attempt in range(max_retries):
        try:
            return client.get(url, timeout=timeout, **kwargs)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            if attempt < max_retries - 1:
                wait = backoff * (attempt + 1)
                log.warning(
                    '[HARVEST] TRANSIENT_HTTP_ERROR url=%s attempt=%d/%d wait_s=%d error=%s',
                    url, attempt + 1, max_retries, wait, e)
                time.sleep(wait)
                continue
            raise

# Hard-coded mapping/cache dicts consolidated in one section.
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

calls_to_infogo = {}

update_frequencies = {
    "irregular": "periodically",
    "continual": "current",
    "annually": "yearly",
    "unknown": "other",
    "weekly": "weekly",
    "monthly": "monthly",
    "fortnightly": "fortnightly",
    "quarterly": "quarterly",
    "biannually": "biannually",
    "as needed": "as_required",
    "on going": "as_required"
}


def _normalized_catalog_match_text(value):
    '''Normalize publisher text to a comparable key for organization matching.
    '''
    if not value:
        return ''
    text = re.sub(r'\s+', ' ', six.text_type(value)).strip().lower()
    text = re.sub(r'^(ontario\s+)?ministry\s+of\s+', '', text)
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _get_catalog_organization_index():
    '''Build and cache an index of active CKAN organizations by match keys.
    '''
    now = datetime.datetime.utcnow()
    cache_expires_at = _catalog_organization_cache['expires_at']
    if (cache_expires_at and cache_expires_at > now and
            _catalog_organization_cache['index'] is not None):
        return _catalog_organization_cache['index']

    index = {}
    try:
        organization_list = toolkit.get_action('organization_list')(
            data_dict={
                'all_fields': True,
                'include_extras': True,
                'include_tags': False,
            }
        )
    except Exception as e:
        log.warning('Unable to load CKAN organizations for GeoHub matching: %s', e)
        _catalog_organization_cache['index'] = {}
        _catalog_organization_cache['expires_at'] = (
            now + GEOHUB_PUBLISHER_OPTIONS_CACHE_TTL)
        return {}

    for org in organization_list:
        if not isinstance(org, dict):
            continue
        if org.get('state') and org.get('state') != 'active':
            continue

        org_name = org.get('name')
        org_title = org.get('title') or org_name
        org_slug = org.get('slug') or org_name
        if not org_name:
            continue

        keys = set()
        keys.add(org_name.lower())
        keys.add(org_title.lower())

        norm_name = _normalized_catalog_match_text(org_name)
        norm_title = _normalized_catalog_match_text(org_title)
        if norm_name:
            keys.add(norm_name)
        if norm_title:
            keys.add(norm_title)

        org_entry = {
            'id': org.get('id'),
            'name': org_name,
            'slug': org_slug,
            'title': org_title,
        }
        for key in keys:
            if key and key not in index:
                index[key] = org_entry

    _catalog_organization_cache['index'] = index
    _catalog_organization_cache['expires_at'] = (
        now + GEOHUB_PUBLISHER_OPTIONS_CACHE_TTL)
    return index


def _find_catalog_organization_from_publisher(publisher_name):
    '''Resolve a GeoHub publisher name to a CKAN organization from the cached index.
    '''
    if not publisher_name:
        return None

    candidates = [publisher_name]
    index = _get_catalog_organization_index()

    for candidate in candidates:
        if not candidate:
            continue
        normalized_text = _normalized_catalog_match_text(candidate)
        lookup_keys = [
            candidate.strip().lower(),
            normalized_text,
        ]
        for key in lookup_keys:
            if key and key in index:
                return index[key]
    return None


def _resolve_dataset_catalog_organization(geohub_dict):
    '''Resolve the dataset's CKAN organization from ontario_geohub_publisher.
    '''
    publisher_name = normalize_geohub_publisher_name(
        geohub_dict.get('ontario_geohub_publisher', ''))
    if publisher_name:
        organization = _find_catalog_organization_from_publisher(publisher_name)
        if organization:
            return organization
    return None


def normalize_geohub_publisher_name(publisher_name):
    '''Normalize GeoHub publisher text by collapsing internal whitespace.
    '''
    if not publisher_name:
        return ''

    return re.sub(r'\s+', ' ', publisher_name).strip()


def _normalize_blacklist_dataset_id(raw_url):
    '''Extract a blacklist dataset id token from a GeoHub dataset URL.
    '''
    if not raw_url:
        return None

    url = six.text_type(raw_url).strip()
    if not url:
        return None

    # Remove querystring/fragment, trim trailing slash, and return last path token.
    url = url.split('#', 1)[0].split('?', 1)[0].rstrip('/')
    if not url:
        return None

    dataset_id = url.split('/')[-1].strip()
    return dataset_id or None


def _normalize_geohub_dataset_url_for_match(raw_url):
    '''Normalize (parse and clean) GeoHub dataset URLs for reliable equality checks.
    '''
    if not raw_url:
        return ''

    try:
        from urllib.parse import urlparse
        parsed = urlparse(six.text_type(raw_url).strip())
    except Exception:
        return six.text_type(raw_url).strip().rstrip('/').lower()

    host = (parsed.netloc or '').lower()
    path = (parsed.path or '').rstrip('/')

    # Canonicalize known GeoHub URL shapes to just base record path:
    # /datasets/<id_or_slug>/... ; /maps/<id>/... ; /documents/<id>/...
    parts = [p for p in path.split('/') if p]
    if host.endswith('geohub.lio.gov.on.ca') and len(parts) >= 2:
        if parts[0] in ('datasets', 'maps', 'documents'):
            path = '/{}/{}'.format(parts[0], parts[1])

    return '{}{}'.format(host, path).lower()


def _geohub_dataset_urls_match(url_a, url_b):
    '''Return True when two GeoHub dataset URLs normalize to the same value.
    '''
    if not url_a or not url_b:
        log.debug(
            '[HARVEST] URL_MATCH_SKIP reason=missing_url url_a=%s url_b=%s',
            url_a, url_b)
        return False
    norm_a = _normalize_geohub_dataset_url_for_match(url_a)
    norm_b = _normalize_geohub_dataset_url_for_match(url_b)
    result = norm_a == norm_b
    log.debug(
        '[HARVEST] URL_MATCH raw_a=%s raw_b=%s norm_a=%s norm_b=%s match=%s',
        url_a, url_b, norm_a, norm_b, result)
    return result


def _fetch_blacklist_ids():
    '''Fetch and cache blacklist dataset ids from the remote ArcGIS endpoint.
    '''
    now = datetime.datetime.utcnow()
    cache_expires_at = _blacklist_cache['expires_at']
    cached_ids = _blacklist_cache['ids']

    if (cache_expires_at and cache_expires_at > now and
            cached_ids is not None):
        return set(cached_ids)

    try:
        response = _requests_get_with_retry(blacklist_url, timeout=30)
        response.raise_for_status()
        payload = response.json()

        features = payload.get('features', []) if isinstance(payload, dict) else []
        if not isinstance(features, list):
            log.warning(
                '[HARVEST] BLACKLIST_PAYLOAD_INVALID features_type=%s; using empty list',
                type(features).__name__)
            features = []

        blacklist_ids = set()
        invalid_entries = 0
        for entry in features:
            if not isinstance(entry, dict):
                invalid_entries += 1
                continue
            attributes = entry.get('attributes', {})
            if not isinstance(attributes, dict):
                invalid_entries += 1
                continue

            dataset_id = _normalize_blacklist_dataset_id(
                attributes.get('geohub_dataset_url'))
            if dataset_id:
                blacklist_ids.add(dataset_id)
            else:
                invalid_entries += 1

        _blacklist_cache['ids'] = blacklist_ids
        _blacklist_cache['expires_at'] = now + GEOHUB_BLACKLIST_CACHE_TTL

        log.debug(
            '[HARVEST] BLACKLIST_FETCH_OK ids=%s invalid_entries=%s',
            len(blacklist_ids),
            invalid_entries)
        return set(blacklist_ids)

    except (requests.exceptions.RequestException, ValueError, TypeError) as e:
        if cached_ids is not None:
            log.warning(
                '[HARVEST] BLACKLIST_FETCH_FAILED using_cached ids=%s error=%s',
                len(cached_ids),
                e)
            return set(cached_ids)

        # Fail open so gather can continue when blacklist endpoint is unavailable.
        log.warning(
            '[HARVEST] BLACKLIST_FETCH_FAILED no_cache_available fail_open=true error=%s',
            e)
        return set()


def get_ontario_geohub_publisher_options():
    '''Return dropdown values for GeoHub publishers that match CKAN organizations,
       with filtered dataset counts.
    '''
    now = datetime.datetime.utcnow()
    cache_expires_at = _geohub_publisher_options_cache['expires_at']
    if (cache_expires_at and cache_expires_at > now and
            _geohub_publisher_options_cache['options'] is not None):
        return list(_geohub_publisher_options_cache['options'])

    # Counts include only datasets that:
    # 1. have ODCSYNC keyword
    # 2. are not on the blacklist
    # 3. have a publisher name matching an ODC organization
    # Excludes datasets with no French equivalents or hubType "table".
    # Too expensive to do those checks here.
    ministry_counts = {}
    try:
        response = _requests_get_with_retry(
            DEFAULT_GEOHUB_DCAT_FEED_URL,
            timeout=60)
        response.raise_for_status()
        doc = response.json()
        datasets = doc.get('dcat:dataset', []) if isinstance(doc, dict) else doc

        blacklist = _fetch_blacklist_ids()

        for dataset in datasets:
            # Only count datasets with ODCSYNC keyword and not on blacklist
            if "ODCSYNC" not in dataset.get('dcat:keyword', []):
                continue
            if dataset.get('ontario_geohub_id') in blacklist:
                continue
            
            publisher_name = normalize_geohub_publisher_name(
                dataset.get('ontario_geohub_publisher', ''))
            log.debug('publisher_name after normalize: %s', publisher_name)
            organization = _find_catalog_organization_from_publisher(
                publisher_name)
            if organization:
                org_name = organization['name']
                org_title = organization['title']
                if org_name not in ministry_counts:
                    ministry_counts[org_name] = {
                        'title': org_title,
                        'count': 0,
                    }
                ministry_counts[org_name]['count'] += 1
    except (requests.exceptions.RequestException, ValueError, TypeError) as e:
        log.warning('Unable to load Ontario GeoHub ministry options: %s', e)

    options = [
        {
            'value': org_name,
            'text': '{} ({})'.format(
                ministry_counts[org_name]['title'],
                ministry_counts[org_name]['count']),
            'count': ministry_counts[org_name]['count']
        }
        for org_name in sorted(ministry_counts.keys())
    ]

    _geohub_publisher_options_cache['options'] = options
    _geohub_publisher_options_cache['expires_at'] = (
        now + GEOHUB_PUBLISHER_OPTIONS_CACHE_TTL)

    return list(options)


def get_ontario_geohub_harvest_organization_options():
    '''Map GeoHub publisher options to unique CKAN organization id/value options.
    '''
    organization_options = []
    seen_organization_ids = set()

    for publisher_option in get_ontario_geohub_publisher_options():
        organization_name = publisher_option['value']
        organization = model.Group.by_name(organization_name)
        if not organization or organization.id in seen_organization_ids:
            continue

        organization_options.append({
            'value': organization.id,
            'text': publisher_option['text'],
        })
        seen_organization_ids.add(organization.id)

    return organization_options

class OntarioGeohubHarvester(HarvesterBase):

    force_import = False
    config = None
    # modified from the DCATHarvester harvester from https://github.com/ckan/ckanext-dcat

    def _set_config(self, config_str):
        '''Parse and store harvest source configuration JSON from the UI template.
        '''
        if config_str:
            try:
                self.config = json.loads(config_str)
            except ValueError:
                log.warning('Invalid harvest source config for Ontario GeoHub, ignoring it')
                self.config = {}
        else:
            self.config = {}

    def validate_config(self, config):
        '''Validate and normalize supported values in harvest source configuration JSON from
           the UI template.
        '''
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
        '''Controls whether source config field presence is allowed/required.

        Return harvest object extra schema entries for this harvester.
        Here, the extra schema is just ontario_geohub_publisher.
        Called by CKAN Harvest core while processing harvest source forms and
        API actions. When a harvest source is saved or loaded, CKAN runs schema 
        validators. Those validators ask each harvester for its extra fields (via extra_schema), validate them, and merge them into the source config.

        ontario_geohub_publisher uses:
        - ignore_missing: accept records where the field is absent.
        - unicode_safe: coerce/validate the value as safe unicode text.
        '''
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
        given the key.
        '''
        for extra in harvest_object.extras:
            if extra.key == key:
                return extra.value
        return None

    def _get_package_name(self, harvest_object, title):
        '''Return an existing package name or generate a unique one from title.
        '''

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
        '''Return the harvest source URL for a harvest object id.
        '''
        obj = model.Session.query(HarvestObject). \
            filter(HarvestObject.id == harvest_object_id).\
            first()
        if obj:
            return obj.source.url
        return None

    def _read_datasets_from_db(self, guid):
        '''
        Return a list of active package id rows for the given guid.
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
        Check if a dataset with a certain guid extra already exists.
        Return a dict like that returned by package_show.
        '''

        datasets = self._read_datasets_from_db(guid)

        if not datasets:
            return None
        elif len(datasets) > 1:
            log.error('Found more than one dataset with the same guid: {0}'
                      .format(guid))

        return p.toolkit.get_action('package_show')({}, {'id': datasets[0][0]})

    def _get_existing_dataset_by_name(self, name):
        '''
        Check if an active dataset already exists with the same name.
        Return a dict like that returned by package_show.
        '''

        if not name:
            return None

        datasets = model.Session.query(model.Package.id) \
                                .filter(model.Package.name == name) \
                                .filter(model.Package.state == 'active') \
                                .all()

        if not datasets:
            return None
        elif len(datasets) > 1:
            log.error('Found more than one dataset with the same name: {0}'
                      .format(name))

        return p.toolkit.get_action('package_show')({}, {'id': datasets[0][0]})

    def _find_existing_catalog_dataset_for_harvest(self, geohub_dict):
        '''
        Find an existing active CKAN dataset (not yet linked by harvest guid)
        that matches the incoming GeoHub record by CKAN name + source URL.
        '''
        if not isinstance(geohub_dict, dict):
            return None

        title = geohub_dict.get('dct:title')
        identifier = geohub_dict.get('dct:identifier')
        if not title or not identifier:
            return None

        candidate_name = ontario_theme_helpers.name_cleaner(title)
        if not candidate_name:
            return None

        log.debug(
            '[HARVEST] FIND_CATALOG_DATASET title=%s candidate_name=%s identifier=%s',
            title, candidate_name, identifier)

        existing_dataset = self._get_existing_dataset_by_name(candidate_name)
        if not existing_dataset:
            log.debug(
                '[HARVEST] FIND_CATALOG_DATASET no_name_match candidate_name=%s',
                candidate_name)
            return None

        log.debug(
            '[HARVEST] FIND_CATALOG_DATASET name_match package_id=%s existing_url=%s incoming_url=%s',
            existing_dataset.get('id'),
            existing_dataset.get('url'),
            identifier)

        if not _geohub_dataset_urls_match(existing_dataset.get('url'),
                                          identifier):
            log.debug(
                '[HARVEST] FIND_CATALOG_DATASET url_mismatch_skip package_id=%s',
                existing_dataset.get('id'))
            return None

        log.debug(
            '[HARVEST] FIND_CATALOG_DATASET found package_id=%s',
            existing_dataset.get('id'))
        return existing_dataset

    def _is_existing_dataset_unchanged(self, existing_dataset, current_content):
        '''
        Compare incoming harvest content to an existing CKAN dataset that does
        not currently have a harvest guid.

        Return True when the incoming dct:modified is not newer than the
        dataset's existing timestamp (current_as_of/metadata_modified).
        '''
        if not existing_dataset:
            return False

        current_modified = self._extract_dct_modified(current_content)
        if not current_modified:
            return False

        existing_modified = (
            existing_dataset.get('current_as_of')
            or existing_dataset.get('metadata_modified')
            or existing_dataset.get('metadata_created')
        )
        if not existing_modified:
            return False

        current_dt = self._parse_dct_modified_timestamp(current_modified)
        existing_dt = self._parse_dct_modified_timestamp(existing_modified)

        if current_dt and existing_dt:
            return current_dt <= existing_dt

        return (six.text_type(current_modified).strip() ==
                six.text_type(existing_modified).strip())


    def _make_package_dict(self, geohub_dict, harvest_object):
        '''Build a CKAN package payload from a GeoHub dataset record.
        '''
        resolved_org = _resolve_dataset_catalog_organization(geohub_dict)
        resolved_org_id = resolved_org.get('id') if resolved_org else None

        required_fields = [
            'ontario_geohub_id',
            'dct:identifier',
            'dct:title',
            'dct:description',
        ]
        missing_required_fields = []
        for field_name in required_fields:
            field_value = geohub_dict.get(field_name)
            if field_value is None:
                missing_required_fields.append(field_name)
                continue
            if isinstance(field_value, six.string_types) and not field_value.strip():
                missing_required_fields.append(field_name)

        if missing_required_fields:
            dataset_id = geohub_dict.get('ontario_geohub_id', 'unknown')
            log.warning(
                '[HARVEST] SKIP_BECAUSE_MISSING_REQUIRED_FIELDS dataset_id=%s missing_fields=%s',
                dataset_id,
                ','.join(missing_required_fields)
            )
            self._save_object_error(
                'Skipping dataset {}: missing required fields [{}]'.format(
                    dataset_id,
                    ', '.join(missing_required_fields)),
                harvest_object,
                'Import'
            )
            return None

        english_xml = english_metadata_xml_response(geohub_dict)
        french_xml = french_metadata_xml_response(geohub_dict)
        english_json = english_metadata_json_response(geohub_dict)

        dataset_id = geohub_dict.get('ontario_geohub_id')
        dataset_identifier = geohub_dict.get('dct:identifier')
        dataset_title = geohub_dict.get('dct:title')
        dataset_description = geohub_dict.get('dct:description')
        dataset_keywords = geohub_dict.get('dcat:keyword')
        if not isinstance(dataset_keywords, list):
            dataset_keywords = []

        package_dict = {
            "id": dataset_id, # Use geohub ID.
            "url": dataset_identifier,
            "license_id": "other-open", 
            "title_translated": {
                "en": dataset_title,
                "fr": french_title(french_xml)
            },
            "notes_translated": {
                "en": html2text.html2text(dataset_description),
                "fr": html2text.html2text(french_notes(french_xml))
            },
            "keywords": {
                "en": ontario_theme_helpers.remove_odd_chars_from_keywords(dataset_keywords) + ['ontario-geohub'],
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
            "resources": build_resources(dataset_id, geohub_dict,
                                         english_xml, english_json),
            "update_frequency": "",
            "exemption": "none",
            "exemption_rationale": {
                "en": "",
                "fr": ""
            },
            "name": ontario_theme_helpers.name_cleaner(dataset_title),
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
            mapped_update_frequency = update_frequencies.get(geohub_update_frequency)
            if mapped_update_frequency:
                package_dict['update_frequency'] = mapped_update_frequency
            else:
                log.warning(
                    '[HARVEST] Unmapped GeoHub update frequency "%s" for dataset %s; leaving update_frequency blank',
                    geohub_update_frequency,
                    geohub_dict.get('ontario_geohub_id', 'unknown')
                )
                package_dict['update_frequency'] = ""

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

        else:

            contact = extract_ontario_email(package_dict['notes_translated']['en'])
            if not contact:
                # Try the DCAT contactPoint email (strip mailto: prefix)
                cp_email = geohub_dict.get('dcat:contactPoint', {}).get('vcard:hasEmail', '')
                if cp_email:
                    contact = cp_email.replace('mailto:', '').strip()
            if contact:
                package_dict['maintainer_email'] = contact.strip()
                contact_name = geohub_dict.get('dcat:contactPoint', {}).get('vcard:fn', '')
                if contact_name:
                    package_dict['maintainer_translated']['en'] = contact_name
                elif package_dict['maintainer_email'].replace("@ontario.ca","").find(".") == -1:
                    package_dict['maintainer_translated']['en'] = package_dict['maintainer_email'].replace("@ontario.ca","").strip()
                else:
                    package_dict['maintainer_translated']['en'] = get_ontario_employee_name(package_dict['maintainer_email'])
                package_dict['maintainer_translated']['fr'] = package_dict['maintainer_translated']['en']

        # owner_org is resolved only from ontario_geohub_publisher.
        if not package_dict.get("owner_org", False) and resolved_org_id:
            package_dict['owner_org'] = resolved_org_id

        return package_dict


    def has_french(self, dataset_obj):
        '''Return boolean.
        '''

        french_xml = french_metadata_xml_response(dataset_obj) 

        if french_notes(french_xml) == "Placeholder":
            return False
        else:
            return True

    def _has_odcsync_keyword(self, dataset_obj):
        '''Return True when the dataset carries the ODCSYNC inclusion keyword.
        '''
        keywords = dataset_obj.get('dcat:keyword', [])
        if not isinstance(keywords, list):
            return False
        if "ODCSYNC" in keywords:
            return True
        return False


    def _is_hubtype_table(self, dataset_obj):
        '''Return boolean.
        
        If _is_hubtype_table returns true, skip the record.
        hubtype: "table" is a "sub-set" of existing datasets.
        The hubtype value is only available through the GeoHub V3 api.
        '''
        identifier = dataset_obj.get('ontario_geohub_id')
        if not identifier:
            log.warning(
                '[HARVEST] HUBTYPE_CHECK_SKIPPED reason=missing_ontario_geohub_id')
            return False
        geohub_endpoint = "https://geohub.lio.gov.on.ca/api/v3/datasets/{}".format(identifier)

        try:
            geohub_response = _requests_get_with_retry(
                geohub_endpoint,
                timeout=30)
            if geohub_response.status_code != 200:
                log.warning(
                    'hubtype_table: HTTP %s for %s, skipping hubtype check',
                    geohub_response.status_code, identifier)
                return False
            payload = geohub_response.json()
            payload_data = payload.get('data', {}) if isinstance(payload, dict) else {}
            attributes = payload_data.get('attributes', {}) if isinstance(payload_data, dict) else {}
            hub_type = attributes.get('hubType')
            if not isinstance(hub_type, six.string_types):
                log.warning(
                    'hubtype_table: Missing hubType for %s, skipping hubtype check',
                    identifier)
                return False
            if hub_type.lower() == 'table':
                return True
        except (requests.exceptions.RequestException, KeyError,
                ValueError, TypeError) as e:
            log.warning(
                'hubtype_table: Error checking hubtype for %s: %s',
                identifier, e)

        return False

    def info(self):
        '''Return harvester metadata used by CKAN harvest-source UI pages.
        '''
        return {
            'name': 'ontario_geohub',
            'title': 'Ontario Geohub',
            'description': 'Harvester for Ontario Geohub'
        }

    def _get_guids_and_datasets(self, content, selected_publisher=None,
                                log_rejections=False,
                                rejection_log_limit=0):
        '''Yield accepted dataset guid/content pairs after filter evaluation.
        '''
        log.warning(f"[HARVEST] Selected publisher: {selected_publisher}")

        selected_org_name = None
        if selected_publisher:
            selected_org = _find_catalog_organization_from_publisher(
                selected_publisher)
            selected_org_name = (
                selected_org['name'] if selected_org else selected_publisher)

        blacklist = _fetch_blacklist_ids()

        doc = json.loads(content)

        if isinstance(doc, list):
            # Assume a list of datasets
            datasets = doc
        elif isinstance(doc, dict):
            datasets = doc.get('dcat:dataset', [])
        else:
            raise ValueError('Wrong JSON object')

        rejected_count = 0
        rejected_logged = 0
        rejection_counts = {}

        for dataset in datasets:
            accepted, guid, as_string, failed_filters, failure_messages = \
                self._evaluate_dataset_filters(
                    dataset,
                    selected_publisher=selected_publisher,
                    selected_org_name=selected_org_name,
                    blacklist=blacklist)

            if accepted:
                log.warning(f"[HARVEST] ACCEPTED GUID: {guid}")
                yield guid, as_string
            elif log_rejections:
                rejected_count += 1
                for code in failed_filters:
                    rejection_counts[code] = rejection_counts.get(code, 0) + 1

                if rejected_logged < rejection_log_limit:
                    log.warning(
                        '[HARVEST] FULL_FEED_FILTER_REJECTED guid=%s title=%s failed_filters=%s reasons=%s',
                        dataset.get('ontario_geohub_id', 'unknown'),
                        dataset.get('dct:title', 'Unknown'),
                        ','.join(failed_filters),
                        ' ; '.join(failure_messages))
                    rejected_logged += 1

        if log_rejections and rejected_count:
            ordered_counts = ','.join(
                ['{}:{}'.format(code, rejection_counts[code])
                 for code in sorted(rejection_counts.keys())]
            )
            log.warning(
                '[HARVEST] FULL_FEED_FILTER_SUMMARY rejected_total=%s logged_examples=%s log_limit=%s counts=%s',
                rejected_count,
                rejected_logged,
                rejection_log_limit,
                ordered_counts)

    def _evaluate_dataset_filters(self, dataset, selected_publisher=None,
                                  selected_org_name=None, blacklist=None):
        '''Evaluate gather filters and return acceptance, ids, and failure reasons.
        '''
        if blacklist is None:
            blacklist = _fetch_blacklist_ids()

        failed_filters = []
        failure_messages = []

        def add_failure(code, message):
            failed_filters.append(code)
            failure_messages.append(message)

        dataset_publisher = normalize_geohub_publisher_name(
            dataset.get('ontario_geohub_publisher', ''))
        dataset_org = _find_catalog_organization_from_publisher(
            dataset_publisher)
        dataset_org_name = dataset_org['name'] if dataset_org else None

        as_string = json.dumps(dataset)
        guid = dataset.get('ontario_geohub_id')
        if not guid:
            # This is bad, any ideas welcomed
            guid = sha1(as_string).hexdigest()

        # Organization gate
        if not dataset_org_name:
            add_failure(
                'no_ckan_org_match',
                'no CKAN org match for publisher={}'.format(dataset_publisher)
            )

        if selected_org_name:
            log.warning(
                '[HARVEST] Dataset publisher/org: %s / %s',
                dataset_publisher,
                dataset_org_name)
            if dataset_org_name != selected_org_name:
                add_failure(
                    'selected_publisher_mismatch',
                    'selected_org_name={} dataset_org_name={}'.format(
                        selected_org_name,
                        dataset_org_name)
                )
            else:
                log.warning(f"[HARVEST] MATCH")

        # Standard gather filters
        if guid in blacklist:
            add_failure('blacklisted', 'dataset id is in blacklist')

        if not self._has_odcsync_keyword(dataset):
            add_failure('missing_odcsync', 'dataset is missing ODCSYNC keyword')

        # If org gating already failed, skip expensive remote checks that can
        # produce noisy warnings for datasets that are guaranteed to be rejected.
        if ('no_ckan_org_match' in failed_filters or
                'selected_publisher_mismatch' in failed_filters):
            return (False,
                    guid,
                    as_string,
                    failed_filters,
                    failure_messages)

        if self._is_hubtype_table(dataset):
            add_failure('hubtype_table', 'dataset hubType resolved to table')

        if not self.has_french(dataset):
            add_failure('missing_french', 'dataset has no French metadata')

        return (len(failed_filters) == 0,
                guid,
                as_string,
                failed_filters,
                failure_messages)

    def fetch_stage(self, harvest_object):
        '''No-operation fetch stage for CKAN harvest pipeline compatibility.

        Return True needed to mark fetch as successful and allow import_stage to run.
        Gather already stores dataset JSON content on each HarvestObject,
        so there is nothing left to retrieve in this stage. 
        '''
        return True

    def _get_package_dict(self, harvest_object):
        '''Convert a harvest object's JSON content into package and source dicts.
        '''

        content = harvest_object.content

        geohub_dict = json.loads(content)

        package_dict = self._make_package_dict(geohub_dict,
                                                harvest_object)

        return package_dict, geohub_dict

    def _extract_dct_modified(self, dataset_content):
        '''Return dct:modified from a harvested dataset JSON payload string.
        '''
        if not dataset_content:
            return None
        try:
            dataset_dict = json.loads(dataset_content)
        except (TypeError, ValueError):
            return None
        return dataset_dict.get('dct:modified')

    def _parse_dct_modified_timestamp(self, value):
        '''Parse common dct:modified timestamp formats to a datetime.
        '''
        if not value:
            return None

        text_value = six.text_type(value).strip()
        if not text_value:
            return None

        known_formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d',
        ]

        for date_format in known_formats:
            try:
                return datetime.datetime.strptime(text_value, date_format)
            except ValueError:
                continue

        return None

    def _is_unchanged_dataset(self, previous_content, current_content):
        '''Return True when dataset should be skipped as unchanged.

        Only reharvest when current dct:modified is newer than previous
        dct:modified.
        '''
        previous_modified = self._extract_dct_modified(previous_content)
        current_modified = self._extract_dct_modified(current_content)

        # Missing timestamps force reharvest.
        if not current_modified or not previous_modified:
            return False

        current_dt = self._parse_dct_modified_timestamp(current_modified)
        previous_dt = self._parse_dct_modified_timestamp(previous_modified)

        if current_dt and previous_dt:
            # Unchanged when current is not newer than previous.
            return current_dt <= previous_dt

        # If we cannot parse either timestamp, compare raw normalized values.
        return (six.text_type(current_modified).strip() ==
                six.text_type(previous_modified).strip())


    # -------------------------------------------------------------------
    # Single-dataset harvesting support
    #
    # These methods allow a tester to enter a single GeoHub dataset URL
    # (by name/slug or by geo-ID) in the Harvest UI instead of the full
    # DCAT feed.  This avoids the 45+ min download of all ~490 datasets.
    # -------------------------------------------------------------------

    def _is_single_dataset_url(self, url):
        '''Determine if the harvest source URL points to a single GeoHub
        dataset rather than the full DCAT feed.

        Return True for URLs like:
          - https://geohub.lio.gov.on.ca/datasets/<slug>/...
          - https://geohub.lio.gov.on.ca/maps/<id>/...
          - https://geohub.lio.gov.on.ca/documents/<id>/...
          - Raw hex IDs (32 chars, optionally with _N suffix)

        Return False for the full DCAT feed URL:
          - https://geohub.lio.gov.on.ca/api/feed/dcat-ap/2.1.1.json
        '''
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
        '''Extract the dataset slug or ID from various GeoHub URL formats.

        Handle:
          https://geohub.lio.gov.on.ca/datasets/mnrf::contour/explore?...
          https://geohub.lio.gov.on.ca/datasets/provincially-tracked-species-1km-grid
          https://geohub.lio.gov.on.ca/maps/882a9059ec7c4881abbdb6afa0ae73e6/about
          https://geohub.lio.gov.on.ca/documents/some-doc-id
          882a9059ec7c4881abbdb6afa0ae73e6       (raw ID)
          882a9059ec7c4881abbdb6afa0ae73e6_29    (raw ID with layer index)

        Return the identifier string (slug or ID).
        '''
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
        '''Search the GeoHub v3 search API with the given parameter.

        Return a list of dataset dicts from the API response, or None.
        '''
        import urllib.parse
        search_url = (
            "https://geohub.lio.gov.on.ca/api/v3/search?{}={}".format(
                param, urllib.parse.quote(value, safe=''))
        )

        try:
            response = _requests_get_with_retry(search_url, timeout=60)
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

    def _search_geohub_v3_all(self, param, value, harvest_job):
        '''Search the GeoHub v3 API and follow pagination links.
        '''
        import urllib.parse

        next_url = (
            "https://geohub.lio.gov.on.ca/api/v3/search?{}={}".format(
                param, urllib.parse.quote(value, safe=''))
        )
        results = []
        # Track visited page URLs to guard against accidental pagination cycles.
        seen_urls = set()
        # Hard stop to prevent pathological loops if the API keeps returning next links.
        max_pages = 100
        page_count = 0
        # Reuse one HTTP session across pages for connection efficiency.
        session = requests.Session()

        while next_url:
            if next_url in seen_urls:
                log.warning(
                    'Detected repeated GeoHub v3 pagination URL for %s=%s; stopping at %s pages',
                    param, value, page_count)
                break
            seen_urls.add(next_url)

            page_count += 1
            if page_count > max_pages:
                log.warning(
                    'GeoHub v3 pagination exceeded max pages (%s) for %s=%s; stopping',
                    max_pages, param, value)
                break

            try:
                response = _requests_get_with_retry(
                    next_url,
                    timeout=60,
                    session=session)
                if response.status_code != 200:
                    log.warning(
                        'GeoHub v3 paged search returned HTTP %s for %s=%s',
                        response.status_code, param, value)
                    break

                payload = response.json()
                data = payload.get('data', [])
                if data:
                    results.extend(data)

                # Continue pagination using the API-provided next link.
                next_url = payload.get('meta', {}).get('next')
            except requests.exceptions.Timeout as e:
                log.warning(
                    'Timeout searching paged GeoHub v3 API (%s=%s): %s',
                    param, value, e)
                break
            except requests.exceptions.RequestException as e:
                # Covers transport-level request failures (DNS/connection/SSL, etc.).
                log.warning(
                    'Request error searching paged GeoHub v3 API (%s=%s): %s',
                    param, value, e)
                break
            except (ValueError, TypeError) as e:
                # Covers malformed/invalid payload structures from the API response.
                log.warning(
                    'Invalid paged GeoHub v3 API response (%s=%s): %s',
                    param, value, e)
                break
            except Exception as e:
                log.warning(
                    'Error searching paged GeoHub v3 API (%s=%s): %s',
                    param, value, e)
                break

        return results if results else None

    def _resolve_selected_publisher_content(self, selected_publisher,
                                            harvest_job):
        '''Fetch only datasets for the selected publisher from GeoHub v3.
        '''
        datasets_by_id = {}

        selected_org = _find_catalog_organization_from_publisher(
            selected_publisher)
        selected_org_name = (
            selected_org['name'] if selected_org else selected_publisher)

        source_names = []

        def _append_source_name(value):
            '''Append a normalized source name candidate if it is non-empty and new.
            '''
            normalized = normalize_geohub_publisher_name(value)
            if normalized and normalized not in source_names:
                source_names.append(normalized)

        # GeoHub v3 filter[source] expects the full source label
        # (e.g. "Ontario ministry of health"), while CKAN org matching
        # can still use stripped names via _find_catalog_organization_from_publisher.
        full_source_name = selected_publisher
        if selected_org:
            full_source_name = selected_org.get('title', '') or selected_publisher
        full_source_name = normalize_geohub_publisher_name(full_source_name)
        if re.match(r'^(?i)ministry\s+of\s+', full_source_name):
            full_source_name = 'Ontario ' + full_source_name
        if full_source_name:
            _append_source_name(full_source_name)

        _append_source_name(selected_publisher)
        if selected_org:
            _append_source_name(selected_org.get('title', ''))
            _append_source_name(selected_org.get('name', ''))

        # Build ministry-shaped candidate values from org slug/title so
        # publisher slugs like "health" can resolve to v3 source labels like
        # "Ministry of Health" / "Ontario ministry of health".
        source_base = (
            selected_org.get('title', '')
            or selected_org.get('name', '')
            if selected_org else selected_publisher
        )
        source_base = normalize_geohub_publisher_name(source_base)
        source_base = re.sub(r'[_\-]+', ' ', source_base)

        if source_base:
            if re.search(r'(?i)\bministry\s+of\b', source_base):
                ministry_name = source_base
            else:
                ministry_name = 'Ministry of {}'.format(source_base.title())

            ontario_ministry_name = 'Ontario {}'.format(ministry_name)
            _append_source_name(ontario_ministry_name)
            _append_source_name(re.sub(
                r'(?i)^Ontario\s+Ministry\s+of\s+',
                'Ontario ministry of ',
                ontario_ministry_name
            ))

        log.info(
            'GeoHub v3 source candidates for selected publisher %s: %s',
            selected_publisher, source_names)

        for source_name in source_names:
            if not source_name:
                continue
            v3_data = self._search_geohub_v3_all(
                'filter[source]', source_name, harvest_job)
            if not v3_data:
                continue

            for dataset in v3_data:
                normalized_source = normalize_geohub_publisher_name(
                    dataset.get('attributes', {}).get('source', ''))
                dataset_org = _find_catalog_organization_from_publisher(
                    normalized_source)
                dataset_org_name = dataset_org['name'] if dataset_org else None
                if dataset_org_name != selected_org_name:
                    continue
                dataset_id = dataset.get('id')
                if dataset_id:
                    datasets_by_id[dataset_id] = dataset

        dcat_datasets = [
            self._build_dcat_dict_from_v3(dataset)
            for dataset in datasets_by_id.values()
        ]
        log.info(
            'Resolved %s GeoHub datasets for selected publisher %s',
            len(dcat_datasets), selected_publisher)
        return json.dumps({'dcat:dataset': dcat_datasets})

    @staticmethod
    def _timestamp_to_iso(timestamp_ms):
        '''Convert a Unix timestamp in milliseconds to an ISO-format string.
        '''
        if timestamp_ms:
            try:
                return datetime.datetime.utcfromtimestamp(
                    timestamp_ms / 1000
                ).strftime('%Y-%m-%dT%H:%M:%S.000Z')
            except (TypeError, ValueError, OSError):
                pass
        return ''

    def _build_dcat_dict_from_v3(self, v3_dataset):
        '''Build a DCAT-compatible dict from a GeoHub v3 search API dataset.

        The returned dict has the field names expected by _make_package_dict
        and the rest of the harvester pipeline.
        '''
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
            if not isinstance(extra_res, dict):
                continue
            extra_url = extra_res.get('url')
            if extra_url:
                distributions.append({
                    "title": extra_res.get('name', extra_url),
                    "accessURL": extra_url,
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
        '''Resolve a single dataset URL to DCAT-compatible content.

        Uses the GeoHub v3 search API to look up the dataset by ID or slug,
        then constructs a DCAT-compatible dict for the harvester pipeline.

        Returns a JSON string in the same format as the DCAT feed, or None.
        '''
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
                    if d.get('id') == identifier
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

    def _gather_single_dataset(self, harvest_job, selected_publisher=''):
        '''Gather stage for a single GeoHub dataset URL.

        This allows testing individual datasets without downloading the full
        DCAT feed (~490 datasets, 45+ min). The same acceptance filters used
        by the full-feed gather path are still applied (ODCSYNC-tag check,
        blacklist, hubtype, French metadata, org matching).
        '''
        log.info('Single dataset mode: resolving %s', harvest_job.source.url)

        content = self._resolve_single_dataset(
            harvest_job.source.url, harvest_job)
        if not content:
            return None

        ids = []

        # Get the previous guids for this source
        query = (
            model.Session.query(
                HarvestObject.guid,
                HarvestObject.package_id,
                HarvestObject.content)
            .filter(HarvestObject.current == True)
            .filter(
                HarvestObject.harvest_source_id == harvest_job.source.id)
        )
        guid_to_package_id = {}
        guid_to_current_content = {}
        for guid, package_id, current_content in query:
            guid_to_package_id[guid] = package_id
            guid_to_current_content[guid] = current_content

        guids_in_db = list(guid_to_package_id.keys())
        guids_in_source = []

        accepted_datasets = []
        selected_org_name = None
        if selected_publisher:
            selected_org = _find_catalog_organization_from_publisher(
                selected_publisher)
            selected_org_name = (
                selected_org['name'] if selected_org else selected_publisher)

        blacklist = _fetch_blacklist_ids()
        doc = json.loads(content)
        datasets = doc.get('dcat:dataset', []) if isinstance(doc, dict) else []

        for dataset in datasets:
            accepted, guid, as_string, failed_filters, failure_messages = \
                self._evaluate_dataset_filters(
                    dataset,
                    selected_publisher=selected_publisher,
                    selected_org_name=selected_org_name,
                    blacklist=blacklist)
            if accepted:
                accepted_datasets.append((guid, as_string))
                continue

            log.warning(
                '[HARVEST] SINGLE_DATASET_FILTER_REJECTED guid=%s title=%s failed_filters=%s reasons=%s',
                dataset.get('ontario_geohub_id', 'unknown'),
                dataset.get('dct:title', 'Unknown'),
                ','.join(failed_filters),
                ' ; '.join(failure_messages))
        if not accepted_datasets:
            log.info(
                'Single dataset mode: no datasets passed standard gather '
                'filters for %s',
                harvest_job.source.url)
            return []

        for guid, as_string in accepted_datasets:
            dataset = json.loads(as_string)

            guids_in_source.append(guid)

            log.info(
                'Single dataset mode: processing %s (ID: %s)',
                dataset.get('dct:title', 'Unknown'), guid)

            if guid in guids_in_db:
                existing_content = guid_to_current_content.get(guid)
                if self._is_unchanged_dataset(existing_content, as_string):
                    log.debug(
                        '[HARVEST] SKIP_UNCHANGED guid=%s',
                        guid)
                    continue

                previous_modified = self._extract_dct_modified(existing_content)
                current_modified = self._extract_dct_modified(as_string)
                log.debug(
                    '[HARVEST] MARK_CHANGE guid=%s previous_dct_modified=%s new_dct_modified=%s',
                    guid,
                    previous_modified,
                    current_modified)

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

        # In single-dataset mode we intentionally do not enqueue deletes for
        # every other dataset in the source. This mode is for targeted testing.
        # Full source synchronization (including deletes) happens in normal
        # gather_stage runs against the full feed.
        if set(guids_in_db) - set(guids_in_source):
            log.info(
                'Single dataset mode: skipping delete sweep for %s datasets',
                len(set(guids_in_db) - set(guids_in_source)))

        return ids

    def gather_stage(self, harvest_job):
        '''Collect source records and enqueue HarvestObjects for import.

        Uses source config to apply optional publisher scoping. If the source
        URL targets a single dataset, routes to single-dataset gather logic;
        otherwise processes the full feed, applies acceptance filters, and
        compares with previous current objects.

        Create HarvestObjects with status values:
        - new: accepted GUID not currently tracked for this source.
        - change: accepted GUID with newer content, including adopted
            pre-existing CKAN datasets.
        - delete: GUID tracked in DB but missing from the current source run.

        Return a list of created HarvestObject ids, or None on gather errors.
        '''
        log.debug('In DCAT JSON Harvester gather_stage')
        log.warning('[HARVEST] Selected publisher config: %s',
                    harvest_job.source.config)

        self._set_config(harvest_job.source.config)
        selected_publisher = (self.config or {}).get('ontario_geohub_publisher', '')
        log.warning(f"[HARVEST] Selected publisher from config: {selected_publisher}")

        # Check if the source URL points to a single dataset rather than
        # the full DCAT feed.  This enables fast testing of individual
        # datasets without downloading all ~490 entries.
        url = harvest_job.source.url

        if self._is_single_dataset_url(url):
            return self._gather_single_dataset(
                harvest_job,
                selected_publisher=selected_publisher)

        ids = []

        # Get the previous guids for this source
        query = \
            model.Session.query(
                HarvestObject.guid,
                HarvestObject.package_id,
                HarvestObject.content) \
            .filter(HarvestObject.current == True) \
            .filter(HarvestObject.harvest_source_id == harvest_job.source.id)
        guid_to_package_id = {}
        guid_to_current_content = {}

        for guid, package_id, current_content in query:
            guid_to_package_id[guid] = package_id
            guid_to_current_content[guid] = current_content

        guids_in_db = list(guid_to_package_id.keys())

        guids_in_source = []

        # Resolve content once per gather run.
        # - Selected publisher: prefer GeoHub v3 narrowed results.
        # - No selected publisher (or empty v3 result): use full DCAT feed.
        url = harvest_job.source.url
        try:
            if selected_publisher:
                content = self._resolve_selected_publisher_content(
                    selected_publisher, harvest_job)
                content_type = 'application/json'
                try:
                    resolved_doc = json.loads(content)
                except (TypeError, ValueError):
                    resolved_doc = {}
                resolved_datasets = (
                    resolved_doc.get('dcat:dataset', [])
                    if isinstance(resolved_doc, dict)
                    else [])
                if not resolved_datasets:
                    # Keep existing behavior when v3 source-name matching
                    # misses records: fall back to the full DCAT pipeline.
                    log.info(
                        'No GeoHub v3 datasets resolved for selected '
                        'publisher %s; falling back to full DCAT feed '
                        'filtering', selected_publisher)
                    content, content_type = self._get_content_and_type(
                        url, harvest_job)
            else:
                content, content_type = self._get_content_and_type(
                    url, harvest_job)
        except requests.exceptions.HTTPError as error:
            if error.response.status_code == 404:
                msg = 'Could not get content. Server responded with 404 Not Found'
                self._save_gather_error(msg, harvest_job)
                return None
            raise

        if not content:
            return None

        try:
            # Single-pass processing: iterate the resolved payload once and
            # classify each GUID as create/update for this harvest job.
            for guid, as_string in self._get_guids_and_datasets(
                    content,
                    selected_publisher=selected_publisher,
                    log_rejections=True,
                    rejection_log_limit=GEOHUB_FULL_FEED_REJECTION_LOG_LIMIT):

                log.debug('Got identifier: {0}'
                          .format(guid.encode('utf8')))
                guids_in_source.append(guid)

                if guid in guids_in_db:
                    existing_content = guid_to_current_content.get(guid)
                    if self._is_unchanged_dataset(existing_content, as_string):
                        log.debug(
                            '[HARVEST] SKIP_UNCHANGED guid=%s',
                            guid)
                        continue

                    previous_modified = self._extract_dct_modified(existing_content)
                    current_modified = self._extract_dct_modified(as_string)
                    log.debug(
                        '[HARVEST] MARK_CHANGE guid=%s previous_dct_modified=%s new_dct_modified=%s',
                        guid,
                        previous_modified,
                        current_modified)

                    # Dataset needs to be updated
                    obj = HarvestObject(
                        guid=guid, job=harvest_job,
                        package_id=guid_to_package_id[guid],
                        content=as_string,
                        extras=[HarvestObjectExtra(key='status',
                                                   value='change')])
                else:
                    dataset_dict = json.loads(as_string)
                    existing_catalog_dataset = \
                        self._find_existing_catalog_dataset_for_harvest(
                            dataset_dict)

                    if existing_catalog_dataset:
                        if self._is_existing_dataset_unchanged(
                                existing_catalog_dataset,
                                as_string):
                            log.debug(
                                '[HARVEST] SKIP_UNCHANGED_EXISTING guid=%s package_id=%s',
                                guid,
                                existing_catalog_dataset.get('id'))
                            continue

                        log.debug(
                            '[HARVEST] ADOPT_EXISTING_DATASET guid=%s package_id=%s',
                            guid,
                            existing_catalog_dataset.get('id'))
                        obj = HarvestObject(
                            guid=guid, job=harvest_job,
                            package_id=existing_catalog_dataset.get('id'),
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

        except ValueError as e:
            msg = 'Error parsing file: {0}'.format(str(e))
            self._save_gather_error(msg, harvest_job)
            return None

        # Check datasets that need to be deleted
        guids_to_delete = set(guids_in_db) - set(guids_in_source)
        for guid in guids_to_delete:
            obj = HarvestObject(
                guid=guid, job=harvest_job,
                package_id=guid_to_package_id[guid],
                extras=[HarvestObjectExtra(key='status', value='delete')])
            model.Session.query(HarvestObject).\
                filter_by(guid=guid).\
                update({'current': False}, False)
            obj.save()
            ids.append(obj.id)

        return ids


    def import_stage(self, harvest_object):
        '''Create, update, or delete CKAN datasets for a harvested GeoHub record.
        '''
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


        package_dict, geohub_dict = self._get_package_dict(harvest_object)
        if not package_dict:
            return False

        # owner_org is mandatory: skip objects where no valid org id is found
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

        if status == 'new' and package_dict.get('name'):
            log.debug(
                '[HARVEST] PRE_CREATE_NAME_CHECK name=%s guid=%s incoming_url=%s',
                package_dict.get('name'),
                harvest_object.guid,
                package_dict.get('url'))
            existing_dataset = self._get_existing_dataset_by_name(
                package_dict['name'])
            if existing_dataset:
                url_matches = _geohub_dataset_urls_match(
                    existing_dataset.get('url'), package_dict.get('url'))
                if url_matches:
                    log.warning(
                        '[HARVEST] PRE_CREATE_REUSE package_id=%s guid=%s reason=name_and_url_match '
                        'existing_url=%s incoming_url=%s '
                        'existing_norm=%s incoming_norm=%s',
                        existing_dataset.get('id'),
                        harvest_object.guid,
                        existing_dataset.get('url'),
                        package_dict.get('url'),
                        _normalize_geohub_dataset_url_for_match(existing_dataset.get('url')),
                        _normalize_geohub_dataset_url_for_match(package_dict.get('url')))
                else:
                    log.warning(
                        '[HARVEST] PRE_CREATE_REUSE package_id=%s guid=%s reason=name_only_match '
                        'existing_url=%s incoming_url=%s '
                        'existing_norm=%s incoming_norm=%s',
                        existing_dataset.get('id'),
                        harvest_object.guid,
                        existing_dataset.get('url'),
                        package_dict.get('url'),
                        _normalize_geohub_dataset_url_for_match(existing_dataset.get('url')),
                        _normalize_geohub_dataset_url_for_match(package_dict.get('url')))
                harvest_object.package_id = existing_dataset['id']
                harvest_object.add()
                package_dict['id'] = existing_dataset['id']
                package_dict.setdefault('extras', [])
                if not any(extra.get('key') == 'guid' for extra in package_dict['extras']):
                    package_dict['extras'].append({
                        'key': 'guid',
                        'value': geohub_dict['ontario_geohub_id'],
                    })
                status = 'change'


        if not package_dict.get('name'):
            package_dict['name'] = \
                self._get_package_name(harvest_object, package_dict['title_translated']['en'])

        # copy across resource ids from the existing dataset, otherwise they'll
        # be recreated with new ids

        if status == 'change':
            package_dict.setdefault('extras', [])
            if not any(extra.get('key') == 'guid' for extra in package_dict['extras']):
                package_dict['extras'].append({
                    'key': 'guid',
                    'value': geohub_dict['ontario_geohub_id'],
                })

            existing_dataset = self._get_existing_dataset(harvest_object.guid)
            if not existing_dataset and harvest_object.package_id:
                try:
                    existing_dataset = p.toolkit.get_action('package_show')(
                        {}, {'id': harvest_object.package_id})
                except Exception as e:
                    log.warning(
                        '[HARVEST] Unable to load existing package for resource matching package_id=%s error=%s',
                        harvest_object.package_id,
                        e)
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
            if status == 'new' and package_dict.get('name'):
                existing_dataset = self._get_existing_dataset_by_name(
                    package_dict['name'])
                if existing_dataset:
                    url_matches = _geohub_dataset_urls_match(
                        existing_dataset.get('url'), package_dict.get('url'))
                    try:
                        log.warning(
                            '[HARVEST] EXCEPTION_RECOVERY package_id=%s guid=%s '
                            'url_matches=%s existing_url=%s incoming_url=%s '
                            'existing_norm=%s incoming_norm=%s error=%s',
                            existing_dataset.get('id'),
                            harvest_object.guid,
                            url_matches,
                            existing_dataset.get('url'),
                            package_dict.get('url'),
                            _normalize_geohub_dataset_url_for_match(existing_dataset.get('url')),
                            _normalize_geohub_dataset_url_for_match(package_dict.get('url')),
                            e)
                        package_dict['id'] = existing_dataset['id']
                        harvest_object.package_id = existing_dataset['id']
                        harvest_object.add()
                        package_dict.setdefault('extras', [])
                        if not any(extra.get('key') == 'guid'
                                   for extra in package_dict['extras']):
                            package_dict['extras'].append({
                                'key': 'guid',
                                'value': geohub_dict['ontario_geohub_id'],
                            })
                        copy_across_resource_ids(existing_dataset, package_dict)
                        package_id = p.toolkit.get_action('package_update')(
                            context, package_dict)
                        log.info('Updated dataset with id %s', package_id)
                        return True
                    except Exception as retry_error:
                        log.warning(
                            '[HARVEST] package_create recovery failed guid=%s error=%s',
                            harvest_object.guid,
                            retry_error)

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
geohub_update_frequency_pattern = re.compile("\*\*Maintenance and Update Frequency(?:[\s\n]*)\*\*(?:[\s\n]*)([^:\n]*):")

def get_org_id(organization_name):  
    '''Return the CKAN organization id matching the GeoHub publisher name.
    '''
    if not organization_name:
        return None

    source_name = organization_name.strip()
    organization = _find_catalog_organization_from_publisher(source_name)
    if organization:
        return organization.get('id')

    # Backward-compatible fallback for direct org slug inputs.
    name_candidates = [source_name]
    for candidate in name_candidates:
        if not candidate:
            continue
        org = model.Group.by_name(candidate)
        if org:
            return org.id

    log.warning(
        '[HARVEST] No CKAN organization match for source org="%s"',
        source_name
    )
    return None


def call_to_infogo(email):
    '''Fetch and cache InfoGo details for an Ontario email address.
    '''
    if email not in calls_to_infogo:
        try:
            infogo_request = _requests_get_with_retry(
                "http://www.infogo.gov.on.ca/infogo/v1/individuals/search?&keywords={}".format(email),
                timeout=15)
            calls_to_infogo[email] = infogo_request.json()
        except (requests.exceptions.RequestException, ValueError, TypeError) as e:
            log.warning('InfoGo API call failed for %s: %s', email, e)
            calls_to_infogo[email] = {}
    return calls_to_infogo[email]

def normalize_update_frequency_text(value):
    '''Normalize (clean) free-text values of update frequency for mapping lookups.
    '''
    if not value:
        return ''
    normalized = re.sub(r'\s+', ' ', six.text_type(value)).strip().lower()
    return normalized


def extract_update_frequency(description):
    '''Extract and normalize update frequency text from a GeoHub description.

    GeoHub descriptions may include a section like:
    Maintenance and Update Frequency
    As needed: data is updated as deemed necessary

    Return the normalized frequency label (for example, "as needed"),
    or None when no frequency is found.
    '''
    search_results = geohub_update_frequency_pattern.findall(description)
    if len(search_results) > 0:
        return normalize_update_frequency_text(search_results[0])
    else:
        return None


def extract_fr_contact_info(description):
    '''Extract French maintainer name, email, and branch from contact text.

    Parse the contact section to extract the name (after removing ministry and branch info),
    email address, and optional branch designation.

    Return a dict with keys maintainer_name, maintainer_email, and optionally maintainer_branch,
    or None if no contact info is found.
    '''
    search_results = geohub_contact_pattern.findall(description)
    if len(search_results) > 0:
        contact_info = search_results[0]
        # split into maintainer name, ministry, branch, email
        contact_info_dict = {
            "maintainer_email" : contact_info[1]
        }
        non_email_contact_info = contact_info[0].replace("\n"," ").replace("  "," ")
        non_email_contact_info = re.sub(
            r"minist[eè]re\s+de\s+[\u00A0-\u017Fa-zA-Z0-9 ,&\-\(\)']+",
            '',
            non_email_contact_info,
            flags=re.IGNORECASE)
        if non_email_contact_info.lower().find("direction") != -1:
            contact_info_chunks = non_email_contact_info.split(",")
            for chunk in contact_info_chunks:
                if chunk.lower().find("direction") != -1:
                   contact_info_dict['maintainer_branch'] = chunk
                   break
        contact_info_dict['maintainer_name'] = non_email_contact_info.strip()
        if contact_info_dict['maintainer_name'] and contact_info_dict['maintainer_name'][-1] in ["-",","]:
            contact_info_dict['maintainer_name'] = contact_info_dict['maintainer_name'][:-1].strip()
        return contact_info_dict
    else:
        return None


def extract_contact_info(description):
    '''Extract maintainer email/name/branch fields from English contact text.
    '''
    search_results = geohub_contact_pattern.findall(description)
    if len(search_results) > 0:
        contact_info = search_results[0]
        # split into maintainer name, ministry, branch, email
        contact_info_dict = {
            "maintainer_email" : contact_info[1].strip()
        }
        non_email_contact_info = contact_info[0].replace("\n"," ").replace("  "," ")
        non_email_contact_info = re.sub(
            r"(?:ontario\s+)?ministry\s+of\s+[a-zA-Z0-9 ,&\-\(\)']+",
            '',
            non_email_contact_info,
            flags=re.IGNORECASE)
        if non_email_contact_info.lower().find("branch") != -1:
            contact_info_chunks = non_email_contact_info.split(",")
            for chunk in contact_info_chunks:
                if chunk.lower().find("branch") != -1:
                   contact_info_dict['maintainer_branch'] = chunk
                   break
        contact_info_dict['maintainer_name'] = non_email_contact_info.strip()
        if contact_info_dict['maintainer_name'] and contact_info_dict['maintainer_name'][-1] in ["-",","]:
            contact_info_dict['maintainer_name'] = contact_info_dict['maintainer_name'][:-1].strip()
        return contact_info_dict
    else:
        return None


def extract_date(date_str):
    '''Return the first YYYY-MM-DD date found in a text string.
    '''
    search_results = iso_date_pattern.findall(date_str)
    if len(search_results) > 0:
        return search_results[0]
    else:
        return None


def extract_ontario_email(description):
    '''Return the first ontario.ca email address found in text.
    '''
    search_results = ontario_email_pattern.findall(description)
    if len(search_results) > 0:
        return search_results[0]
    else:
        return None


def get_ontario_employee_name(email):
    '''Return employee display name from InfoGo, with an email-based fallback.
    '''
    fallback_name = " ".join(list(map(
        lambda x: x.capitalize(),
        re.sub(r'[0-9]+', '', email).replace("@ontario.ca","").split(".", 1))))
    infogo_response = call_to_infogo(email)
    total = infogo_response.get('total', 0)
    individuals = infogo_response.get('individuals', [])
    if total > 0 and isinstance(individuals, list) and individuals:
        first_individual = individuals[0]
        if not isinstance(first_individual, dict):
            return fallback_name
        calls_to_infogo[email] = infogo_response
        return " ".join(list(map(lambda x: first_individual[x] if x in first_individual else "", ["firstname", "middleName","lastName"])))
    else:
        return fallback_name


def french_notes(french_xml):
    '''Extract French abstract/notes from ISO 19115 metadata XML.

    Search the metadata root for the dataIdInfo/idAbs element and return its text content.
    Return the French abstract text, or 'Placeholder' if the element is not found.
    '''
    french_notes_text = 'Placeholder'

    root = french_xml
    #root = lxml.etree.fromstring(french_xml.content)
    french_notes_element = root.xpath("//dataIdInfo/idAbs")
    if french_notes_element:
        french_notes_text = french_notes_element[0].text

    return french_notes_text


def french_title(french_xml):
    '''Return the french title from the xml response.
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
    '''Return the french keywords from the xml response.
    <dataIdInfo><idAbs>
    '''

    french_keywords = []

    root = french_xml
    #root = lxml.etree.fromstring(french_xml.content)
    french_keywords_element = root.xpath("//searchKeys")
    if french_keywords_element:
        for keyword in french_keywords_element[0]:
            keyword_text = keyword.text
            if keyword_text and len(keyword_text) < 100:
                french_keywords.append(keyword_text)
      
    return french_keywords


def get_license_from_xml(root):
    '''Return the license for that dataset.
    '''
    license_path = root.xpath("//dataIdInfo/resConst/LegConsts/useLimit")
    if license_path:
        license_text = license_path[0].text
        return license_text
    return False

def get_backup_description_from_xml(root):
    '''Return the description/purpose from the ISO 19115 idPurp element, 
    or False if not found.
    '''
    desc_path = root.xpath("//dataIdInfo/idPurp")
    if desc_path:
        desc_text = desc_path[0].text
        if desc_text:
            return desc_text
    return False



def _get_metadata_attributes(json_metadata):
    '''Safely retrieve the nested data.attributes mapping from metadata JSON.
    '''
    if not isinstance(json_metadata, dict):
        return {}
    data = json_metadata.get('data', {})
    if not isinstance(data, dict):
        return {}
    attributes = data.get('attributes', {})
    if not isinstance(attributes, dict):
        return {}
    return attributes


def get_data_last_updated_from_json(json_metadata):
    '''Return the ISO-format datetime string (e.g., '2024-06-11T14:30:45.123456') 
    of the data's last update timestamp, or an empty string if the timestamp is 
    missing or invalid.

        json[“data”][“attributes”][“modified”] – Date that the data was last updated.

    '''
    attributes = _get_metadata_attributes(json_metadata)
    modified = attributes.get('modified')
    if not isinstance(modified, six.integer_types + (float,)):
        return ''
    try:
        return datetime.datetime.utcfromtimestamp(modified / 1000).isoformat()
    except (TypeError, ValueError, OSError):
        return ''


def get_current_as_of_date_from_json(json_metadata):
    '''
            This can be obtained from a combination of two values.

            Using this API endpoint: https://opendata.arcgis.com/api/v3/datasets/{id}

            json[“data”][“attributes”][“itemModified”] – Date that the ArcGIS Online item was last modified, including metadata updates. Equivalent to ModDate + ModTime from the metadata XML

            json[“data”][“attributes”][“modified”] – Date that the data was last updated.

            The values returned are unix timestamps in milliseconds. Compare and use the larger one of the two.

    '''
    attributes = _get_metadata_attributes(json_metadata)
    item_modified = attributes.get('itemModified')
    modified = attributes.get('modified')
    numeric_values = [
        value for value in (item_modified, modified)
        if isinstance(value, six.integer_types + (float,))
    ]
    if not numeric_values:
        return ''
    current_as_of = max(numeric_values)
    try:
        return datetime.datetime.utcfromtimestamp(current_as_of / 1000).isoformat()
    except (TypeError, ValueError, OSError):
        return ''

def get_revise_date_from_xml(root):
    '''Return the revise date (comparable to data_range_end) for that dataset.
    '''
    revise_date_path = root.xpath("//metadata/Esri/ModDate") #//dataIdInfo/idCitation/date/reviseDate
    if revise_date_path:
        revise_date_text = revise_date_path[0].text
        revise_date = extract_date(revise_date_text)
        if revise_date:
            return revise_date
    return False

def get_create_date_from_json(json_metadata):
    '''Return created timestamp from metadata JSON as an ISO datetime string.
    '''
    attributes = _get_metadata_attributes(json_metadata)
    created = attributes.get('created')
    if not isinstance(created, six.integer_types + (float,)):
        return ''
    try:
        return datetime.datetime.utcfromtimestamp(created / 1000).isoformat()
    except (TypeError, ValueError, OSError):
        return ''

def get_create_date_from_xml(root):
    '''Return the create date (comparable to data_range_start) for that dataset.
    '''
    create_date_path = root.xpath("//metadata/Esri/CreaDate") #//dataIdInfo/idCitation/date/createDate
    if create_date_path:
        create_date_text = create_date_path[0].text
        create_date = extract_date(create_date_text)
        if create_date:
            return create_date
    return False


def get_file_type(resource):
    '''Return the file format of a resource.
    
    Handle both flat dicts (from v3 API / normalized) and DCAT-prefixed
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
    '''Convert a DCAT-AP 2.0.1 distribution entry to the flat format
    expected by build_resources / get_file_type.

    DCAT feed entries look like:
        {"dct:title": "CSV",
         "dcat:accessURL": {"@id": "https://..."},
         "dct:format": {"@id": "ftype/CSV"}}

    The v3-API path already produces flat dicts:
        {"title": "CSV", "accessURL": "https://...", "format": "CSV"}

    This helper normalises to the flat style so downstream code works
    regardless of which path produced the dict.
    '''
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
    '''Harvest all resources/files for the dataset.

    Build a complete list of resources/downloads for a dataset from 
    multiple metadata sources.

    Collect resources from DCAT distributions (handling both v3 API 
    flat format and DCAT-AP feed format), add standard ISO 19115 
    metadata document links (HTML and XML formats), and include 
    additional resources from XML metadata. Avoid duplicates by 
    tracking accessURLs.

    Return a list of resource dicts with keys: name_translated (en/fr), 
    type (data, metadata, technical_document), url, format, and 
    optional data_range_start/data_range_end timestamps.
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
    '''Return the base dataset identifier without any layer index suffix. 
    
    Strip trailing '_N' suffixes (e.g., '882a9059ec7c4881abbdb6afa0ae73e6_29' → '882a9059ec7c4881abbdb6afa0ae73e6'). 
    Return the identifier unchanged if no suffix is present.
    '''
    # ID is at the end but sometimes there's extra bits we dont want that are
    # the underlying layer index.
    #identifier = identifier_url.split('/')[-1].split('_')[0]
    identifier = identifier.split('_')[0]
    return identifier


def identifier_from_url_with_index(identifier_url):
    '''Return the dataset identifier with layer index suffix preserved.
    If no layer index exists, the identifier is returned as-is.

    Extract the last path component from an identifier URL (e.g., '882a9059ec7c4881abbdb6afa0ae73e6_29' from a URL path) and
    return it as-is, keeping any '_N' layer index suffix. Use this
    when the full identifier with layer index is needed; use
    identifier_from_url() to strip the layer index when the layer
    index is not needed.
    '''
    identifier = identifier_url.split('/')[-1] # keep layer index.
    return identifier

def metadata_url(id):
    '''Return a url for the metadata XML.
    '''
    return "https://www.arcgis.com/sharing/rest/content/items/{}/info/metadata/metadata.xml".format(id)


def _parse_metadata_xml_content(xml_bytes, dataset_id, language_label):
    '''Parse XML bytes into an lxml element root, retrying with recover=True
    on XMLSyntaxError to handle minor ArcGIS metadata defects.
    Log a warning on recovery; raise if recovery also fails.
    '''
    try:
        return lxml.etree.fromstring(xml_bytes)
    except lxml.etree.XMLSyntaxError as strict_error:
        # Some ArcGIS metadata payloads contain minor XML defects. Recovering
        # preserves usable nodes instead of hard-failing to an empty root.
        parser = lxml.etree.XMLParser(recover=True)
        recovered_root = lxml.etree.fromstring(xml_bytes, parser=parser)
        if recovered_root is not None:
            log.warning(
                '[HARVEST] RECOVERED_MALFORMED_%s_METADATA_XML dataset_id=%s error=%s',
                language_label.upper(),
                dataset_id,
                strict_error)
            return recovered_root
        raise


def additional_resources_from_xml(root):
    '''Return a list of resource dicts from onLineSrc elements in the XML metadata.

    Each dict has keys: url (linkage text), name_translated (en/fr using orName,
    defaulting to the linkage URL if no name is present), and type ('data').
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
    '''Fetch English ArcGIS v3 metadata JSON or return safe default values.
    '''
    english_id = dataset_obj['ontario_geohub_id']
    english_metadata_url = "https://opendata.arcgis.com/api/v3/datasets/{}".format(english_id)
    try:
        metadata_json_request = _requests_get_with_retry(
            english_metadata_url,
            timeout=60)
        metadata_json_request.raise_for_status()
        return metadata_json_request.json()
    except (requests.exceptions.RequestException, ValueError, TypeError) as e:
        log.warning(
            'Exception raised. Cannot load/parse english metadata JSON for '
            'english_id: %s. Using default timestamps. %r',
            english_id,
            e)
        return {
            'data': {
                'attributes': {
                    'created': 0,
                    'itemModified': 0,
                    'modified': 0,
                }
            }
        }
    

def english_metadata_xml_response(dataset_obj):
    '''Fetch and parse the ArcGIS metadata XML for an English dataset record.

    Return the parsed lxml element root, or an empty root element if the
    request fails or the XML cannot be parsed.
    '''

    english_id = identifier_from_url(dataset_obj['ontario_geohub_id'])
    english_metadata_url = metadata_url(english_id)
    try:
        metadata_xml_request = _requests_get_with_retry(
            english_metadata_url,
            timeout=60)
        metadata_xml_request.raise_for_status()
        # parse the response to get the additional resources.
        return _parse_metadata_xml_content(
            metadata_xml_request.content,
            english_id,
            'english')
    except (requests.exceptions.RequestException,
            lxml.etree.XMLSyntaxError) as e:
        log.warning(
            'Exception raised. Cannot load/parse english metadata for '
            'english_id: %s. Using empty root element instead. %r',
            english_id,
            e)
        return lxml.etree.Element("root")

def french_metadata_xml_response(dataset_obj):
    '''Return the french metadata xml.

    To build this we need to grab the french values for some fields. Easiest
    so far is to loop over english and make a call to the matching french
    record.
    '''

    english_id = dataset_obj['ontario_geohub_id']
    french_id = geohub_french_id_from_xml(dataset_obj)
    if not french_id:
        return lxml.etree.Element("root")

    #french_id = identifier_from_url(french_id)
    french_metadata_xml_url = metadata_url(identifier_from_url(french_id))

    try:
        # Now can make request for xml.
        french_xml_response = _requests_get_with_retry(
            french_metadata_xml_url,
            timeout=60)
        french_xml_response.raise_for_status()
        # TODO: fix bug.  if geohub_french_id_from_xml: continue on, else abort french and use defaults. in some cases there is an ID but the request fails (outdated data I think). In this case it tries to parse the html I think and uses the defaults (den-site is an example).
        # TODO: Error handle for non-existent French record.
        french_xml_root = _parse_metadata_xml_content(
            french_xml_response.content,
            english_id,
            'french')
    except (requests.exceptions.RequestException,
            lxml.etree.XMLSyntaxError) as e:
        logging.warning('Exception raised. Cannot load/parse response for english_id: {} and french_id: {}. Using empty root element instead. {}'
            .format(english_id, french_id, repr(e)))
        # Create an empty root element 
        french_xml_root = lxml.etree.Element("root")

    return french_xml_root