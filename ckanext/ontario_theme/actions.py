# encoding: utf-8

import json
import re

import ckan.plugins.toolkit as toolkit

from ckanext.ontario_theme.harvesters.ontario_geohub import (
    OntarioGeohubHarvester,
    _fetch_blacklist_ids,
    _find_catalog_organization_from_publisher,
    normalize_geohub_publisher_name,
)


def ontario_geohub_precheck_single_dataset(context, data_dict):
    """Preflight-check a single GeoHub dataset URL against all 
    gather filters.

    Returns eligibility against all filters and details so the 
    harvest source form can warn users before saving a source 
    that cannot yield harvest objects.
    """
    toolkit.check_access('ontario_geohub_precheck_single_dataset',
                         context, data_dict)

    data_dict = data_dict or {}
    source_type = (data_dict.get('source_type') or '').strip()
    url = (data_dict.get('url') or '').strip()
    selected_publisher = normalize_geohub_publisher_name(
        data_dict.get('ontario_geohub_publisher') or '')

    result = {
        'eligible': True,
        'checked': False,
        'reason_code': '',
        'message': '',
        'failed_filters': [],
        'failure_messages': [],
        'dataset_id': '',
        'dataset_title': '',
    }

    # Only validate single-dataset GeoHub sources.
    if source_type != 'ontario_geohub' or not url:
        return result

    harvester = OntarioGeohubHarvester()
    if not harvester._is_single_dataset_url(url):
        return result

    result['checked'] = True

    identifier = harvester._extract_dataset_identifier(url)
    if not identifier:
        result.update({
            'eligible': False,
            'reason_code': 'invalid_identifier',
            'message': 'Could not extract a GeoHub dataset identifier from the URL.'
        })
        return result

    v3_data = None
    if re.match(r'^[a-f0-9]{32}(_\d+)?$', identifier):
        v3_data = harvester._search_geohub_v3('filter[id]', identifier, None)
    if not v3_data:
        v3_data = harvester._search_geohub_v3('filter[slug]', identifier, None)
    if not v3_data:
        search_term = identifier.replace('-', ' ').replace('::', ' ')
        v3_data = harvester._search_geohub_v3('q', search_term, None)
        if v3_data and len(v3_data) > 1:
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
        result.update({
            'eligible': False,
            'reason_code': 'not_found',
            'message': 'Dataset was not found in the GeoHub v3 API.'
        })
        return result

    dataset = v3_data[0]
    dcat_dict = harvester._build_dcat_dict_from_v3(dataset)
    dataset_id = dcat_dict.get('ontario_geohub_id', '')
    dataset_title = dcat_dict.get('dct:title', '')
    result['dataset_id'] = dataset_id
    result['dataset_title'] = dataset_title

    selected_org_name = None
    if selected_publisher:
        selected_org = _find_catalog_organization_from_publisher(
            selected_publisher)
        selected_org_name = (
            selected_org['name'] if selected_org else selected_publisher)

    dataset_publisher = normalize_geohub_publisher_name(
        dcat_dict.get('ontario_geohub_publisher', ''))
    dataset_org = _find_catalog_organization_from_publisher(dataset_publisher)
    dataset_org_name = dataset_org['name'] if dataset_org else None
    failed_filters = []
    failure_messages = []

    def add_failure(code, message):
        failed_filters.append(code)
        failure_messages.append(message)

    if not dataset_org_name:
        add_failure(
            'no_ckan_org_match',
            'Dataset publisher has no matching CKAN organization: {}'
            .format(dataset_publisher or 'unknown')
        )

    if selected_org_name and dataset_org_name != selected_org_name:
        add_failure(
            'selected_publisher_mismatch',
            'Dataset maps to CKAN organization "{}", but selected '
            'publisher resolves to "{}".'
            .format(dataset_org_name, selected_org_name)
        )

    if dataset_id and dataset_id in _fetch_blacklist_ids():
        add_failure('blacklisted', 'Dataset is blacklisted and will be skipped.')

    if not harvester._has_odcsync_keyword(dcat_dict):
        add_failure('missing_odcsync', 'Dataset is missing required ODCSYNC keyword.')

    if harvester._is_hubtype_table(dcat_dict):
        add_failure('hubtype_table', 'Dataset hubType is table and is skipped by harvester.')

    if not harvester.has_french(dcat_dict):
        add_failure('missing_french', 'Dataset has no French metadata and will be skipped.')

    if failed_filters:
        result.update({
            'eligible': False,
            'reason_code': failed_filters[0],
            'message': ' ; '.join(failure_messages),
            'failed_filters': failed_filters,
            'failure_messages': failure_messages,
        })
    else:
        result.update({
            'eligible': True,
            'reason_code': 'eligible',
            'message': 'Dataset passed all gather filters.',
            'failed_filters': [],
            'failure_messages': [],
        })
    return result