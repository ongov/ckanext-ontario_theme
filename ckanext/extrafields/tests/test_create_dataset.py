# encoding: utf-8

'''Unit tests for extrafields/tests/test_plugin.py.
Tried to follow test format from the unit tests for ckan/logic/validators.py in
CKAN core but trimmed down.

The ckan core tests were a bit too complex for the basic testing currently
being done here. Refactor if / when tests become more complex.
'''
import ckan.lib.navl.dictization_functions as df
import nose.tools
import datetime

import ckanext.extrafields.plugin as extrafields

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises

import ckan.model as model
import ckan.plugins
from ckan.plugins.toolkit import NotAuthorized, ObjectNotFound
import ckan.tests.factories as factories
import ckan.logic as logic

import ckan.tests.helpers as helpers

class TestCreateDataset(object):
    '''Ensure dataset creates still work and don't work as expected.
    '''

    @classmethod
    def setup_class(cls):
        '''Nose runs this method once to setup our test class.'''
        # Test code should use CKAN's plugins.load() function to load plugins
        # to be tested.
        ckan.plugins.load('extrafields')

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
        ckan.plugins.unload('extrafields')

    def test_package_create_with_minimum_values(self):
        '''If dataset is given name it is created.
        '''
        dataset = helpers.call_action(
            'package_create',
            name='package-name'
            )

    def test_wrong_node_id_type(self):
        '''If dataset is given a value for node_id it must be a positive integer.
        Empty and missing values are allowed.
        '''
        assert_raises(
            logic.ValidationError, helpers.call_action,
            'package_create',
            node_id='apple'
        )

    def test_package_create_with_validated_values(self):
        '''If dataset is given custom validated keys with valid values
        a dataset is created.
        '''
        dataset = helpers.call_action(
            'package_create',
            name='package-name',
            node_id='123',
            date_range_start='',
            date_range_end='',
            data_birth_date='',
            update_frequency='as_required',
            access_level='open',
            exemption='' # Defaults to none when key provided and value is empty.
        )
        assert_equals(dataset['node_id'], 123)
        package_show = helpers.call_action('package_show', id=dataset['id'])
        assert_equals(package_show['node_id'], 123)
        assert 'date_range_start' not in package_show
        assert 'date_range_end' not in package_show
        assert 'data_birth_date' not in package_show
        assert_equals(package_show['update_frequency'], 'as_required')
        assert_equals(package_show['access_level'], 'open')
        assert_equals(package_show['exemption'], 'none') # Confirms modified in validation.