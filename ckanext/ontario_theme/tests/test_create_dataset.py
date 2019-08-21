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

class TestCreateDataset(object):
    '''Ensure dataset creates still work and don't work as expected.
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

    def test_package_create_with_minimum_values(self):
        '''If dataset is given it's basic fields it is created.
        '''
        dataset = helpers.call_action(
            'package_create',
            name='package-name',
            maintainer='Joe Smith',
            maintainer_email='Joe.Smith@ontario.ca',
            title_translated={
                'en': u'A Novel By Tolstoy', 'fr':u'Un novel par Tolstoy'},
            notes_translated={'en': u'short description', 'fr': u'...'}
            )
        assert_equals(dataset['name'], 'package-name')

        dataset = helpers.call_action('package_show', id=dataset['id'])
        assert dataset['title_translated']['fr'] == u'Un novel par Tolstoy'

        dataset = helpers.call_action('package_show', id=dataset['id'])
        assert dataset['notes_translated']['en'] == u'short description'

    def test_wrong_node_id_type(self):
        '''If dataset is given a value for node_id it must be a positive integer.
        Empty and missing values are allowed.
        '''
        assert_raises(
            logic.ValidationError, helpers.call_action,
            'package_create',
            node_id='apple',
            name='package-name',
            maintainer='Joe Smith',
            maintainer_email='Joe.Smith@ontario.ca',
            title_translated={
                'en': u'A Novel By Tolstoy', 'fr':u'Un novel par Tolstoy'},
            notes_translated={'en': u'short description', 'fr': u'...'}
        )

    def test_package_create_with_validated_values(self):
        '''If dataset is given custom validated keys with valid values
        a dataset is created.
        '''
        dataset = helpers.call_action(
            'package_create',
            name='package-name',
            maintainer='Joe Smith',
            maintainer_email='Joe.Smith@ontario.ca',
            title_translated={
                'en': u'A Novel By Tolstoy', 'fr':u'Un novel par Tolstoy'},
            node_id='123',
            notes_translated={'en': u'short description', 'fr': u'...'},
            current_as_of='',
            update_frequency='as_required',
            access_level='open',
            exemption='' # Defaults to none when key provided and value is empty.
        )
        assert_equals(dataset['node_id'], '123')
        package_show = helpers.call_action('package_show', id=dataset['id'])
        assert_equals(package_show['node_id'], '123')
        assert_equals(package_show['notes_translated']['en'], 'short description')
        assert 'current_as_of' not in package_show
        assert_equals(package_show['update_frequency'], 'as_required')
        assert_equals(package_show['access_level'], 'open')
        assert_equals(package_show['exemption'], 'none') # Confirms modified in validation.

    def test_package_create_with_invalid_update_frequency(self):
        '''If dataset is given invalid values should raise Invalid.
        Only testing one. All select options follow same pattern in schema.
        As long as schema is correct scheming's validations should handle the testing.

        This is more of a reminder to setup the schema properly.

        NOTE: Presets are great unless you start modifying things. (i.e. presets
        add predefined values such as validators, until you add your own. Those override
        the preset. So you 'll have to add in the defaults as needed.')
        '''

        try:
            helpers.call_action(
                'package_create',
                name='package-name',
                maintainer='Joe Smith',
                maintainer_email='Joe.Smith@ontario.ca',
                title_translated={
                    'en': u'A Novel By Tolstoy', 'fr':u'Un novel par Tolstoy'},
                node_id='123',
                notes_translated={'en': u'short description', 'fr': u'...'},
                current_as_of='',
                update_frequency='required',
                access_level='open',
                exemption='' # Defaults to none when key provided and value is empty.
            )
        except logic.ValidationError as e:
            assert_equals(
                e.error_dict['update_frequency'],
                ['Value must be one of: as_required; biannually; current; daily; historical; monthly; never; on_demand; other; periodically; quarterly; weekly; yearly (not \'required\')']
            )
        else:
            raise AssertionError('ValidationError not raised')

    def test_package_create_with_invalid_current_as_of(self):
        '''If dataset is given invalid values should raise Invalid.
        Only testing one per input type that was modified. All date inputs follow same pattern in schema.
        As long as schema is correct scheming's validations should handle the testing.

        This is more of a reminder to setup the schema properly.

        NOTE: Presets are great unless you start modifying things. (i.e. presets
        add predefined values such as validators, until you add your own. Those override
        the preset. So you 'll have to add in the defaults as needed.')
        '''

        try:
            helpers.call_action(
                'package_create',
                name='package-name',
                maintainer='Joe Smith',
                maintainer_email='Joe.Smith@ontario.ca',
                title_translated={
                    'en': u'A Novel By Tolstoy', 'fr':u'Un novel par Tolstoy'},
                node_id='123',
                notes_translated={'en': u'short description', 'fr': u'...'},
                current_as_of='31/11/2018',
                update_frequency='as_required',
                access_level='open',
                exemption='' # Defaults to none when key provided and value is empty.
            )
        except logic.ValidationError as e:
            assert_equals(
                e.error_dict['current_as_of'],
                ['Date format incorrect']
            )
        else:
            raise AssertionError('ValidationError not raised')