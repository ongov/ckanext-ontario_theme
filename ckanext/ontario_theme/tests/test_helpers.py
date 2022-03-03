# encoding: utf-8

'''Test for helpers in plugin.py
'''

import pytest

import json
import os
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
from ckan.common import config
from ckanext.ontario_theme.plugin import (
    get_license,
    default_locale,
    get_package_keywords
)

@pytest.mark.usefixtures('clean_db', 'clean_index', 'with_plugins', 'with_request_context') 
class TestGetLicense(object):
    def test_get_license_returns_proper_value(self):
        '''Ensure get_license returns proper license object from licences.json.
        '''
        with open(os.path.join(
            os.path.dirname(__file__), '../schemas', 'licences.json')
        ) as licenses:
            license = json.load(licenses)[0]
        assert get_license("OGL-ON-1.0")._data == license


@pytest.mark.usefixtures('clean_db', 'clean_index', 'with_plugins', 'with_request_context') 
class TestDefaultLocale(object):
    def test_default_locale_returns_proper_value(self):
        default = config.get('ckan.locale_default', 'en')
        assert default_locale() == default


@pytest.mark.usefixtures('clean_db', 'clean_index', 'with_plugins', 'with_request_context') 
class TestGetPackageKeywords(object):
    def test_get_package_keywords_returns_english_as_default(self):
        org = factories.Organization()
        dataset = helpers.call_action(
            'package_create',
            name = 'package-name',
            access_level = 'restricted',
            maintainer_translated = {
                'en': u'Joe Smith',
                'fr': u'...'
            },
            maintainer_email = 'Joe.Smith@ontario.ca',
            title_translated = {
                'en': u'A Novel By Tolstoy',
                'fr':u'Un novel par Tolstoy'
            },
            notes_translated = {
                'en': u'short description',
                'fr': u'...'
            },
            owner_org = org['name'], # depends on config.
            keywords={'en': [u'English Tag'], 'fr': [u'French Tag']}
        )
        # Make sure package was returned as expected.
        assert dataset['name'] == 'package-name'
        # Expected keyword list based on dataset above.
        keywords = [{
                'count': 1,
                'display_name': u'English Tag',
                'name': u'English Tag'
            }]

        assert get_package_keywords() == keywords

    def test_get_package_keywords_returns_english(self):
        org = factories.Organization()
        dataset = helpers.call_action(
            'package_create',
            name = 'package-name',
            access_level = 'restricted',
            maintainer_translated = {
                'en': u'Joe Smith',
                'fr': u'...'
            },
            maintainer_email = 'Joe.Smith@ontario.ca',
            title_translated = {
                'en': u'A Novel By Tolstoy',
                'fr':u'Un novel par Tolstoy'
            },
            notes_translated = {
                'en': u'short description',
                'fr': u'...'
            },
            owner_org = org['name'], # depends on config.
            keywords = {
                'en': [u'English Tag'],
                'fr': [u'French Tag']
            }
        )
        # Make sure package was returned as expected.
        assert dataset['name'] == 'package-name'
        # Expected keyword list based on dataset above.
        keywords = [{
                'count': 1,
                'display_name': u'English Tag',
                'name': u'English Tag'
            }]
        assert get_package_keywords(language='en') == keywords


    def test_get_package_keywords_returns_french(self):
        org = factories.Organization()
        dataset = helpers.call_action(
            'package_create',
            name = 'package-name',
            access_level = 'restricted',
            maintainer_translated = {
                'en': u'Joe Smith',
                'fr': u'...'
            },
            maintainer_email = 'Joe.Smith@ontario.ca',
            title_translated = {
                'en': u'A Novel By Tolstoy',
                'fr':u'Un novel par Tolstoy'
            },
            notes_translated = {
                'en': u'short description',
                'fr': u'...'
            },
            owner_org = org['name'], # depends on config.
            keywords = {
                'en': [u'English Tag'],
                'fr': [u'French Tag']
            }
        )
        # Make sure package was returned as expected.
        assert dataset['name'] == 'package-name'
        # Expected keyword list based on dataset above.
        keywords = [{
                'count': 1,
                'display_name': u'French Tag',
                'name': u'French Tag'
            }]
        assert get_package_keywords(language='fr') == keywords


    def test_get_package_keywords_returns_multiple_values(self):
        org = factories.Organization()
        dataset = helpers.call_action(
            'package_create',
            name = 'package-name',
            access_level = 'restricted',
            maintainer_translated = {
                'en': u'Joe Smith',
                'fr': u'...'
            },
            maintainer_email = 'Joe.Smith@ontario.ca',
            title_translated = {
                'en': u'A Novel By Tolstoy',
                'fr':u'Un novel par Tolstoy'
            },
            notes_translated = {
                'en': u'short description',
                'fr': u'...'
            },
            owner_org = org['name'], # depends on config.
            keywords = {
                'en': [u'English Tag', u'English Tag 2'],
                'fr': [u'French Tag', u'French Tag 2', u'French Tag 3']
            }
        )
        # Make sure package was returned as expected.
        assert dataset['name'] == 'package-name'
        # Expected keyword list based on dataset above.
        keywords = [{
                'count': 1,
                'display_name': u'English Tag 2',
                'name': u'English Tag 2'
            },
            {
                'count': 1,
                'display_name': u'English Tag',
                'name': u'English Tag'
            }]
        assert get_package_keywords() == keywords