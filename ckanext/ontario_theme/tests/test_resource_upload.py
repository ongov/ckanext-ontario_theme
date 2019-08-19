# encoding: utf-8

'''Unit tests for ckan/logic/auth/create.py.

Note: This is copied from https://github.com/ckan/ckan/blob/8ed0534f00b2b25f9e8df1962f821b9a9a979479/ckan/tests/logic/action/test_create.py#L413
and modified. Really it's just the final tests that were added using this as a
template
'''

import ckan.plugins as plugins

import __builtin__ as builtins

import ckan
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as p
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import mock
import nose.tools
from ckan.common import config
from pyfakefs import fake_filesystem

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises
assert_not_equals = nose.tools.assert_not_equals

real_open = open
fs = fake_filesystem.FakeFilesystem()
fake_os = fake_filesystem.FakeOsModule(fs)
fake_open = fake_filesystem.FakeFileOpen(fs)


def mock_open_if_open_fails(*args, **kwargs):
    try:
        return real_open(*args, **kwargs)
    except (OSError, IOError):
        return fake_open(*args, **kwargs)


class TestResourceCreate(object):
    import cgi

    class FakeFileStorage(cgi.FieldStorage):
        def __init__(self, fp, filename):
            self.file = fp
            self.filename = filename
            self.name = 'upload'

    @classmethod
    def setup_class(cls):
        helpers.reset_db()

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
        plugins.unload(u'ontario_theme')

    def setup(self):
        self.app = helpers._get_test_app()

        if not plugins.plugin_loaded(u'ontario_theme'):
            plugins.load(u'ontario_theme')
            plugin = plugins.get_plugin(u'ontario_theme')
            self.app.flask_app.register_extension_blueprint(
                plugin.get_blueprint())

        model.repo.rebuild_db()

    # Changed storage_path from /doesnt_exist to doesnt exist as this was
    # trying to make a directory without having permissions.
    @helpers.change_config('ckan.storage_path', 'doesnt_exist')
    @mock.patch.object(ckan.lib.uploader, 'os', fake_os)
    @mock.patch.object(builtins, 'open', side_effect=mock_open_if_open_fails)
    @mock.patch.object(ckan.lib.uploader, '_storage_path', new='doesnt_exist')
    def test_mimetype_by_upload_by_filename(self, mock_open):
        '''
        The type is determined using python magic which checks file
        headers.
        Real world usage would be using the FileStore API or web UI form to
        upload a file, with a filename plus extension
        '''
        import StringIO
        test_file = StringIO.StringIO()
        test_file.write('''
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
        ''')
        test_resource = TestResourceCreate.FakeFileStorage(test_file, 'test.json')

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

        context = {}
        params = {
            'package_id': dataset['id'],
            'url': 'http://data',
            'name': 'A nice resource',
            'upload': test_resource
        }

        # Mock url_for as using a test request context interferes with the FS mocking
        with mock.patch('ckan.lib.helpers.url_for'):
            result = helpers.call_action('resource_create', context, **params)

        mimetype = result.pop('mimetype')

        assert mimetype
        assert_equals(mimetype, 'application/json')

    # Changed storage_path from /doesnt_exist to doesnt exist as this was
    # trying to make a directory without having permissions.
    @helpers.change_config('ckan.storage_path', 'doesnt_exist')
    @mock.patch.object(ckan.lib.uploader, 'os', fake_os)
    @mock.patch.object(builtins, 'open', side_effect=mock_open_if_open_fails)
    @mock.patch.object(ckan.lib.uploader, '_storage_path', new='doesnt_exist')
    def test_validation_error_with_unsupported_html_type(self, mock_open):
        '''
        The type is determined using python magic which checks file
        headers.
        Real world usage would be using the FileStore API or web UI form to
        upload a file, with a filename plus extension
        '''
        import StringIO
        test_file = StringIO.StringIO()
        test_file.write('''
        <!DOCTYPE html>
        <html>
            <head>
              <title></title>
            </head>
            <body>

            </body>
        </html>
        ''')
        test_resource = TestResourceCreate.FakeFileStorage(test_file,
            'test.html')

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

        context = {}
        params = {
            'package_id': dataset['id'],
            'url': 'http://data',
            'name': 'A nice resource',
            'upload': test_resource
        }

        # Mock url_for as using a test request context interferes with the FS
        # mocking
        with mock.patch('ckan.lib.helpers.url_for'):
            assert_raises(logic.ValidationError,
                helpers.call_action,
                'resource_create',
                context=context,
                **params)

    # Changed storage_path from /doesnt_exist to doesnt exist as this was
    # trying to make a directory without having permissions.
    @helpers.change_config('ckan.storage_path', 'doesnt_exist')
    @mock.patch.object(ckan.lib.uploader, 'os', fake_os)
    @mock.patch.object(builtins, 'open', side_effect=mock_open_if_open_fails)
    @mock.patch.object(ckan.lib.uploader, '_storage_path', new='doesnt_exist')
    def test_validation_error_with_unsupported_exe_type(self, mock_open):
        '''
        The type is determined using python magic which checks file
        headers.
        Real world usage would be using the FileStore API or web UI form to
        upload a file, with a filename plus extension
        '''
        import StringIO
        test_file = StringIO.StringIO()
        test_file.write('''
        <!DOCTYPE html>
        <html>
            <head>
              <title></title>
            </head>
            <body>

            </body>
        </html>
        ''')
        test_resource = TestResourceCreate.FakeFileStorage(test_file,
            'test.exe')

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

        context = {}
        params = {
            'package_id': dataset['id'],
            'url': 'http://data',
            'name': 'A nice resource',
            'upload': test_resource
        }

        # Mock url_for as using a test request context interferes with the FS
        # mocking
        with mock.patch('ckan.lib.helpers.url_for'):
            assert_raises(logic.ValidationError,
                helpers.call_action,
                'resource_create',
                context=context,
                **params)
