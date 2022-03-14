# encoding: utf-8

'''Unit tests for ontario_theme/tests/test_plugin.py.
Tried to follow test format from the unit tests for ckan/logic/validators.py in
CKAN core but trimmed down.

The ckan core tests were a bit too complex for the basic testing currently
being done here. Refactor if / when tests become more complex.
'''

import pytest 

from ckan.tests import factories
import ckan.tests.helpers as helpers

@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
class TestUpdateDataset(object):
    '''Ensure dataset updates still work and don't work as expected.
    '''

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
            access_level = u'restricted',
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
            access_level = u'restricted',
            notes_translated = {
                'en': 'shorter description',
                'fr': 'petit...'
            }
        )

        # Make sure update works and returns saved value.
        assert dataset_['name'] == 'new-name'

        # Safe measure - query the package again and validate values.
        dataset_ = helpers.call_action('package_show', id=dataset['id'])
        assert dataset_['name'] == 'new-name'
        assert dataset_['maintainer_translated']['en'] == 'Jane Smith'
        assert dataset_['maintainer_email'] == 'Jane.Smith@ontario.ca'
        assert dataset_['notes_translated']['en'] == 'shorter description'
        assert dataset_['notes_translated']['fr'] == 'petit...'


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
            access_level = u'restricted',
            owner_org = org['name'] # depends on config.
        )

        assert dataset['notes_translated']['en'] == 'short description'

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
        
        package_show = helpers.call_action('package_show', id=dataset['id'])
        assert dataset_['maintainer_translated']['en'] == 'Jane Smith'
        assert dataset_['maintainer_email'] == 'Jane.Smith@ontario.ca'
        assert package_show['notes_translated']['en'] == 'shorter description'
        assert 'current_as_of' not in package_show
        assert package_show['update_frequency'] == 'as_required'
        assert package_show['access_level'] == 'open'
        assert package_show['exemption'] == 'none' # Confirms modified in validation.

