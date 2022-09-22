# encoding: utf-8

'''Unit tests for ckan/logic/auth/create.py.

Note: This is copied from https://github.com/ckan/ckan/blob/8ed0534f00b2b25f9e8df1962f821b9a9a979479/ckan/tests/logic/action/test_create.py#L413
and modified. Really it's just the final tests that were added using this as a
template
'''

import pytest
import ckan.plugins as plugins

import builtins as builtins

import ckan
import ckan.logic as logic
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import mock

from ckan.common import config
from pyfakefs import fake_filesystem

real_open = open
fs = fake_filesystem.FakeFilesystem()
fake_os = fake_filesystem.FakeOsModule(fs)
fake_open = fake_filesystem.FakeFileOpen(fs)


def mock_open_if_open_fails(*args, **kwargs):
    try:
        return real_open(*args, **kwargs)
    except (OSError, IOError):
        return fake_open(*args, **kwargs)

@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
class TestResourceCreate(object):
    import cgi

    class FakeFileStorage(cgi.FieldStorage):
        def __init__(self, fp, filename):
            self.file = fp
            self.filename = filename
            self.name = 'upload'

    # Changed storage_path from /doesnt_exist to doesnt exist as this was
    # trying to make a directory without having permissions.
    @helpers.change_config('ckan.storage_path', 'doesnt_exist')
    @mock.patch.object(ckan.lib.uploader, 'os', fake_os)
    @mock.patch.object(builtins, 'open', side_effect=mock_open_if_open_fails)
    @mock.patch.object(ckan.lib.uploader, '_storage_path', new='doesnt_exist')
    @pytest.mark.ckan_config('ckan.plugins', 'ontario_theme_external ontario_theme scheming_datasets scheming_organizations scheming_groups fluent')
    @pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context','create_with_upload') 
    def test_mimetype_by_upload_by_filename(self, mock_open, create_with_upload):
        '''
        The type is determined using python magic which checks file
        headers.
        Real world usage would be using the FileStore API or web UI form to
        upload a file, with a filename plus extension
        '''
        file_data = '''
        "info": {
            "title": "BC Data Catalogue API",
            "description": "This API provides information about datasets in the BC Data Catalogue.",
            "termsOfService": "http://www.data.gov.bc.ca/local/dbc/docs/license/API_Terms_of_Use.pdf",
            "contact": {
                "name": "Data BC",
                "url": "http://data.gov.bc.ca/",
                "email": ""
            },
            "license": {
                "name": "Open Government License - British Columbia",
                "url": "http://www.data.gov.bc.ca/local/dbc/docs/license/OGL-vbc2.0.pdf"
            },
            "version": "3.0.0"
        }
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
            access_level = u'open',
            owner_org = org['name'] # depends on config.
        )
        assert dataset['name'] == 'package-name'

        result = create_with_upload(file_data, "test.json", 
            url="http://data",
            package_id=dataset["id"],
            name="A nice resource",
            mimetype="application/json")
        

    # Changed storage_path from /doesnt_exist to doesnt exist as this was
    # trying to make a directory without having permissions.
    @helpers.change_config('ckan.storage_path', 'doesnt_exist')
    @mock.patch.object(ckan.lib.uploader, 'os', fake_os)
    @mock.patch.object(builtins, 'open', side_effect=mock_open_if_open_fails)
    @mock.patch.object(ckan.lib.uploader, '_storage_path', new='doesnt_exist')
    @pytest.mark.ckan_config('ckan.plugins', 'ontario_theme_external ontario_theme scheming_datasets scheming_organizations scheming_groups fluent')
    @pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context','create_with_upload') 
    def test_validation_error_with_unsupported_html_type(self, mock_open, create_with_upload):
        '''
        The type is determined using python magic which checks file
        headers.
        Real world usage would be using the FileStore API or web UI form to
        upload a file, with a filename plus extension
        '''
        file_data = '''
        <!DOCTYPE html>
        <html>
            <head>
              <title></title>
            </head>
            <body>

            </body>
        </html>
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
            access_level = u'open',
            owner_org = org['name'] # depends on config.
        )
        assert dataset['name'] == 'package-name'


        # Mock url_for as using a test request context interferes with the FS
        # mocking
        
        with pytest.raises(logic.ValidationError) as excinfo:
            result = create_with_upload(file_data, "test.html", 
                url="http://data",
                package_id=dataset["id"],
                name="A nice resource")

        
                
    # Changed storage_path from /doesnt_exist to doesnt exist as this was
    # trying to make a directory without having permissions.
    @helpers.change_config('ckan.storage_path', 'doesnt_exist')
    @mock.patch.object(ckan.lib.uploader, 'os', fake_os)
    @mock.patch.object(builtins, 'open', side_effect=mock_open_if_open_fails)
    @mock.patch.object(ckan.lib.uploader, '_storage_path', new='doesnt_exist')
    @pytest.mark.ckan_config('ckan.plugins', 'ontario_theme_external ontario_theme scheming_datasets scheming_organizations scheming_groups fluent')
    @pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context','create_with_upload') 
    def test_validation_error_with_unsupported_exe_type(self, mock_open, create_with_upload):
        '''
        The type is determined using python magic which checks file
        headers.
        Real world usage would be using the FileStore API or web UI form to
        upload a file, with a filename plus extension
        '''
        file_data = '''
        <!DOCTYPE html>
        <html>
            <head>
              <title></title>
            </head>
            <body>

            </body>
        </html>
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
            access_level = u'open',
            owner_org = org['name'] # depends on config.
        )
        assert dataset['name'] == 'package-name'

        with pytest.raises(logic.ValidationError) as excinfo:

            result = create_with_upload(file_data, "test.exe", 
                url="http://data",
                package_id=dataset["id"],
                name="A nice resource")
