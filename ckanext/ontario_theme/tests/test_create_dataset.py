# encoding: utf-8

'''Unit tests for ontario_theme/tests/test_plugin.py.
Tried to follow test format from the unit tests for ckan/logic/validators.py in
CKAN core but trimmed down.

The ckan core tests were a bit too complex for the basic testing currently
being done here. Refactor if / when tests become more complex.
'''

import pytest

import ckan.lib.navl.dictization_functions as df
import datetime

import ckanext.ontario_theme.plugin as ontario_theme

import ckan.model as model
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import ckan.logic as logic


@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')  
class TestCreateDataset(object):
    '''Ensure dataset creates still work and don't work as expected.
    '''

    def test_package_create_with_minimum_values_colby(self):
        '''If dataset is given it's basic fields it is created.
        '''
        org = factories.Organization()
        dataset = helpers.call_action(
            'package_create',
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
        assert dataset['name'] == 'package-name'

        dataset = helpers.call_action('package_show', id=dataset['id'])
        assert dataset['title_translated']['fr'] == u'Un novel par Tolstoy'

        dataset = helpers.call_action('package_show', id=dataset['id'])
        assert dataset['notes_translated']['en'] == u'short description'

 
    def test_package_create_with_minimum_values(self):
        '''If dataset is given it's basic fields it is created.
        '''
        org = factories.Organization()
        dataset = helpers.call_action(
            'package_create',
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
            access_level= u'open',
            owner_org = org['name'] # depends on config.
        )
        assert dataset['name'] == 'package-name'

        dataset = helpers.call_action('package_show', id=dataset['id'])
        assert dataset['title_translated']['fr'] == u'Un novel par Tolstoy'

        dataset = helpers.call_action('package_show', id=dataset['id'])
        assert dataset['notes_translated']['en'] == u'short description'


    def test_package_create_with_validated_values(self):
        '''If dataset is given custom validated keys with valid values
        a dataset is created.
        '''
        org = factories.Organization()
        dataset = helpers.call_action(
            'package_create',
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
            owner_org = org['name'], # depends on config.
            current_as_of='',
            update_frequency='as_required',
            access_level='open',
            exemption='' # Defaults to none when key provided and value is empty.
        )
        package_show = helpers.call_action('package_show', id=dataset['id'])
        assert package_show['notes_translated']['en'] == 'short description'
        assert 'current_as_of' not in package_show
        assert package_show['update_frequency'] == 'as_required'
        assert package_show['access_level'] == 'open'
        assert package_show['exemption'] == 'none' # Confirms modified in validation.

 
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
            org = factories.Organization()
            dataset = helpers.call_action(
                'package_create',
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
                owner_org = org['name'], # depends on config.
                current_as_of='',
                update_frequency='required',
                access_level='open',
                exemption='' # Defaults to none when key provided and value is empty.
            )
        except logic.ValidationError as e:
            update_frequency_values = ["Value must be one of ['as_required', 'biannually', 'current', 'daily', 'historical', 'monthly', 'never', 'on_demand', 'other', 'periodically', 'quarterly', 'weekly', 'yearly', 'quinquennial']"]
                                        
            assert e.error_dict['update_frequency'] == update_frequency_values

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
            org = factories.Organization()
            dataset = helpers.call_action(
                'package_create',
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
                owner_org = org['name'], # depends on config.
                current_as_of='31/11/2018',
                update_frequency='as_required',
                access_level='open',
                exemption='' # Defaults to none when key provided and value is empty.
            )
        except logic.ValidationError as e:
            assert e.error_dict['current_as_of'] == ['Date format incorrect']
        else:
            raise AssertionError('ValidationError not raised')