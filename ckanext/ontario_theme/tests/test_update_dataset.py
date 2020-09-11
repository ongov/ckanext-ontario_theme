# encoding: utf-8

'''Unit tests for ontario_theme/tests/test_plugin.py.
Tried to follow test format from the unit tests for ckan/logic/validators.py in
CKAN core but trimmed down.

The ckan core tests were a bit too complex for the basic testing currently
being done here. Refactor if / when tests become more complex.
'''
import ckan.lib.navl.dictization_functions as df
import nose.tools
import datetime

import ckanext.ontario_theme.plugin as ontario_theme

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises

import ckan.model as model
import ckan.plugins
from ckan.plugins.toolkit import NotAuthorized, ObjectNotFound
import ckan.tests.factories as factories
import ckan.logic as logic

import ckan.tests.helpers as helpers

class TestUpdateDataset(object):
    '''Ensure dataset updates still work and don't work as expected.
    '''

    @classmethod
    def setup_class(cls):
        '''Nose runs this method once to setup our test class.'''
        # Test code should use CKAN's plugins.load() function to load plugins
        # to be tested.
        ckan.plugins.load('ontario_theme')

    def teardown(self):
        '''Nose runs this method after each test method in our test class.'''
        # Rebuild CKAN's database after each test method, so that each test
        # method runs with a clean slate.
        model.repo.rebuild_db()

    @classmethod
    def teardown_class(cls):
        '''Nose runs this method once after all the test methods in our class
        have been run.

        '''
        # We have to unload the plugin we loaded, so it doesn't affect any
        # tests that run after ours.
        ckan.plugins.unload('ontario_theme')

    def test_package_update_with_minimum_values(self):
        '''If dataset is given it's basic fields it is updated.
        '''
        org = factories.Organization()
        user = factories.User()
        dataset = factories.Dataset(
            user = user,
            name = 'package-name',
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
            owner_org = org['name'] # depends on config.
        )

        # All required fields needed here as this is update not patch.
        dataset_ = helpers.call_action(
            'package_update',
            id = dataset['id'],
            name = 'new-name',
            maintainer_translated = {
                'en': u'Jane Smith',
                'fr': u'...'
            },
            maintainer_email = 'Jane.Smith@ontario.ca',
            title_translated = {
                'en': u'A Novel By Tolstoy',
                'fr':u'Un novel par Tolstoy'
            },
            notes_translated = {
                'en': 'shorter description',
                'fr': 'petit...'
            }
        )

        # Make sure update works and returns saved value.
        assert_equals(dataset_['name'], 'new-name')

        # Safe measure - query the package again and validate values.
        dataset_ = helpers.call_action('package_show', id=dataset['id'])
        assert_equals(dataset_['name'], 'new-name')
        assert_equals(dataset_['maintainer_translated']['en'], 'Jane Smith')
        assert_equals(dataset_['maintainer_email'], 'Jane.Smith@ontario.ca')
        assert_equals(dataset_['notes_translated']['en'], 'shorter description')
        assert_equals(dataset_['notes_translated']['fr'], 'petit...')

    def test_package_update_with_validated_values(self):
        '''If dataset is given wider range input with valid values
        a dataset is updated.
        '''
        org = factories.Organization()
        user = factories.User()
        dataset = factories.Dataset(
            user = user,
            name = 'package-name',
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
            owner_org = org['name'] # depends on config.
        )

        assert_equals(dataset['notes_translated']['en'], 'short description')

        dataset_ = helpers.call_action(
            'package_update',
            id = dataset['id'],
            name = 'package-name',
            maintainer_translated = {
                'en': u'Jane Smith',
                'fr': u'...'
            },
            maintainer_email = 'Jane.Smith@ontario.ca',
            node_id = '123',
            title_translated = {
                'en': u'A Novel By Tolstoy',
                'fr':u'Un novel par Tolstoy'
            },
            notes_translated = {
                'en': 'shorter description',
                'fr': 'petit...'
            },
            current_as_of = '',
            update_frequency = 'as_required',
            access_level ='open',
            exemption = '' # Defaults to none when key provided and value is empty.
        )

        assert_equals(dataset_['node_id'], '123')

        package_show = helpers.call_action('package_show', id=dataset['id'])
        assert_equals(package_show['node_id'], '123')
        assert_equals(dataset_['maintainer_translated']['en'], 'Jane Smith')
        assert_equals(dataset_['maintainer_email'], 'Jane.Smith@ontario.ca')
        assert_equals(package_show['notes_translated']['en'], 'shorter description')
        assert 'current_as_of' not in package_show
        assert_equals(package_show['update_frequency'], 'as_required')
        assert_equals(package_show['access_level'], 'open')
        assert_equals(package_show['exemption'], 'none') # Confirms modified in validation.
