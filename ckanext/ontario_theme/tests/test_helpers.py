# encoding: utf-8

'''Test for helpers in plugin.py
'''
import nose.tools
import json
import os
import ckan.tests.helpers as helpers
import ckan.model as model
import ckan.plugins as plugins
import ckan.lib.search as search
from ckan.common import config
from ckanext.ontario_theme.plugin import (
    get_license,
    default_locale,
    get_package_keywords
)
assert_equals = nose.tools.assert_equals


class TestGetLicense(object):
    def test_get_license_returns_proper_value(self):
        '''Ensure get_license returns proper license object from licences.json.
        '''
        with open(os.path.join(
            os.path.dirname(__file__), '..', 'licences.json')
        ) as licenses:
            license = json.load(licenses)[0]
        assert_equals(get_license("OGL-ON-1.0")._data, license)


class TestDefaultLocale(object):
    def test_default_locale_returns_proper_value(self):
        default = config.get('ckan.locale_default', 'en')
        assert_equals(default_locale(), default)


class TestGetPackageKeywords(object):
    @classmethod
    def setup_class(cls):
        '''Nose runs this method once to setup our test class.'''
        # Test code should use CKAN's plugins.load() function to load plugins
        # to be tested.
        plugins.load('ontario_theme')

        cls.package_index = search.PackageSearchIndex()

    def teardown(self):
        '''Nose runs this method after each test method in our test class.'''
        # Rebuild CKAN's database after each test method, so that each test
        # method runs with a clean slate.
        model.repo.rebuild_db()
        # clear the search index after every test.
        # This is needed because the count that is received from the keywords
        # helper is from solr. Solr wasn't clearing the index so the count
        # kept incrementing and throwing failing tests. Check CKAN's search
        # tests for larger examples.
        self.package_index.clear()

    @classmethod
    def teardown_class(cls):
        '''Nose runs this method once after all the test methods in our class
        have been run.

        '''
        # We have to unload the plugin we loaded, so it doesn't affect any
        # tests that run after ours.
        plugins.unload('ontario_theme')

    def test_get_package_keywords_returns_english_as_default(self):
        dataset = helpers.call_action(
                'package_create',
                name='package-name',
                maintainer='Joe Smith',
                maintainer_email='Joe.Smith@ontario.ca',
                title_translated={
                    'en': u'A Novel By Tolstoy', 'fr':u'Un novel par Tolstoy'},
                notes_translated={'en': u'short description', 'fr': u'...'},
                keywords={'en': [u'English Tag'], 'fr': [u'French Tag']}
                )
        # Make sure package was returned as expected.
        assert_equals(dataset['name'], 'package-name')
        # Expected keyword list based on dataset above.
        keywords = [{
                'count': 1,
                'display_name': u'English Tag',
                'name': u'English Tag'
            }]
        assert_equals(get_package_keywords(), keywords)

    def test_get_package_keywords_returns_english(self):
        dataset = helpers.call_action(
                'package_create',
                name='package-name',
                maintainer='Joe Smith',
                maintainer_email='Joe.Smith@ontario.ca',
                title_translated={
                    'en': u'A Novel By Tolstoy', 'fr':u'Un novel par Tolstoy'},
                notes_translated={'en': u'short description', 'fr': u'...'},
                keywords={'en': [u'English Tag'], 'fr': [u'French Tag']}
                )
        # Make sure package was returned as expected.
        assert_equals(dataset['name'], 'package-name')
        # Expected keyword list based on dataset above.
        keywords = [{
                'count': 1,
                'display_name': u'English Tag',
                'name': u'English Tag'
            }]
        assert_equals(get_package_keywords(language='en'), keywords)

    def test_get_package_keywords_returns_french(self):
        dataset = helpers.call_action(
                'package_create',
                name='package-name',
                maintainer='Joe Smith',
                maintainer_email='Joe.Smith@ontario.ca',
                title_translated={
                    'en': u'A Novel By Tolstoy', 'fr':u'Un novel par Tolstoy'},
                notes_translated={'en': u'short description', 'fr': u'...'},
                keywords={'en': [u'English Tag'], 'fr': [u'French Tag']}
                )
        # Make sure package was returned as expected.
        assert_equals(dataset['name'], 'package-name')
        # Expected keyword list based on dataset above.
        keywords = [{
                'count': 1,
                'display_name': u'French Tag',
                'name': u'French Tag'
            }]
        assert_equals(get_package_keywords(language='fr'), keywords)

    def test_get_package_keywords_returns_multiple_values(self):
        dataset = helpers.call_action(
                'package_create',
                name='package-name',
                maintainer='Joe Smith',
                maintainer_email='Joe.Smith@ontario.ca',
                title_translated={
                    'en': u'A Novel By Tolstoy', 'fr':u'Un novel par Tolstoy'},
                notes_translated={'en': u'short description', 'fr': u'...'},
                keywords={'en': [u'English Tag', u'English Tag 2'], 'fr': 
                [u'French Tag', u'French Tag 2', u'French Tag 3']}
                )
        # Make sure package was returned as expected.
        assert_equals(dataset['name'], 'package-name')
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
        assert_equals(get_package_keywords(), keywords)