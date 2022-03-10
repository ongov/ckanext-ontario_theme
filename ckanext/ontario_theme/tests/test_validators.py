# encoding: utf-8

'''Unit tests for ontario_theme/tests/test_validators.py
'''

import pytest

import ckan.tests.factories as factories
import ckan.logic as logic

import ckan.tests.helpers as helpers

@pytest.mark.usefixtures('clean_db', 'clean_index', 'with_plugins', 'with_request_context')  
class TestOntarioThemeCopyFluentKeywordsToTags(object):
    '''Ensure Fluent multi-lingual keywords are copied to CKAN core Tags.
    '''
    def test_ontario_theme_copy_fluent_keywords_to_tags(self):
        '''If a dataset's keywords are updated make sure the Tags are too.
        These copied keywords should be available from the tag_autocomplete
        action.
        '''

        assert helpers.call_action('tag_autocomplete',query='Engl') == []

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
                'en': [u'English', u'Language'],
                'fr': [u'Français'],
                'de': [u'...']
            },
        )
        comparative_keywords = {
                'en': [u'English', u'Language'],
                'fr': [u'Français'],
                'de': [u'...']
            }
        assert dataset['keywords'] == comparative_keywords
        assert sorted([tag['name'] for tag in dataset['tags']]) == [u'...', u'English', u'Français', u'Language']
        
        assert helpers.call_action('tag_autocomplete', query='Engl') == [u'English']

@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
class TestOntarioThemeTagNameValidator(object):
    '''Ensure new Tag Name Validator with apostrophes accepts and
    rejects characters appropriately.
    '''

    def test_ontario_theme_creates_resource_without_apostrophe_tag(self):
        '''A dataset and resource should save with normal tag strings 
        (ensure default behaviour still works.).
        '''

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
                'en': [u'English', u"Languages"],
                'fr': [u'Français'],
                'de': [u'...']
            },
        )
        comparative_keywords = {
                'en': [u'English', u"Languages"],
                'fr': [u'Français'],
                'de': [u'...']
            }
        assert dataset['keywords'] == comparative_keywords

        resource = helpers.call_action(
            'resource_create',
            package_id = dataset["id"],
            url = 'http://data')

        assert resource["url"] == 'http://data'


    def test_ontario_theme_creates_resource_with_apostrophe_tag(self):
        '''A dataset and resource should save with apostrophes in tag
        strings (one of the modified features in new validator).
        '''

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
                'en': [u'English', u"Language's"],
                'fr': [u'Français'],
                'de': [u'...']
            },
        )

        comparative_keywords = {
                'en': [u'English', u"Language's"],
                'fr': [u'Français'],
                'de': [u'...']
            }
        assert dataset['keywords'] == comparative_keywords

        resource = helpers.call_action(
            'resource_create',
            package_id = dataset["id"],
            url = 'http://data')

        assert resource["url"] == 'http://data' 


    def test_ontario_theme_creates_resource_with_two_spaces(self):
        '''A dataset and resource should save with apostrophes in tag
        strings (one of the modified features in new validator).
        '''

        try:
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
                    'en': [u'English', u"French and  Italian"],
                    'fr': [u'Français'],
                    'de': [u'...']
                },
            )

            comparative_keywords = {
                    'en': [u'English'],
                    'fr': [u'Français'],
                    'de': [u'...']
                }
            assert dataset['keywords'] == comparative_keywords

            resource = helpers.call_action(
                'resource_create',
                package_id = dataset["id"],
                url = 'http://data')

        except logic.ValidationError as e:
            assert e.error_dict['keywords'] == [u'Tag "French and  Italian" may not contain consecutive spaces']


    def test_ontario_theme_creates_resource_with_comma(self):
        '''A dataset and resource should save with apostrophes in tag
        strings (one of the modified features in new validator).
        '''
        try:
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
                    'en': [u'English', u"Languages, dialects and locales"],
                    'fr': [u'Français'],
                    'de': [u'...']
                },
            )

            comparative_keywords = {
                    'en': [u'English'],
                    'fr': [u'Français'],
                    'de': [u'...']
                }
            assert dataset['keywords'] == comparative_keywords

            resource = helpers.call_action(
                'resource_create',
                package_id = dataset["id"],
                url = 'http://data')

        except logic.ValidationError as e:
            assert e.error_dict['keywords'] == [u'Tag "Languages, dialects and locales" may not contain commas']
            