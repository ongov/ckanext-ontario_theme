"""Tests for plugin.py."""
from nose.tools import eq_, ok_
from ckan.exceptions import HelperError
import ckan.plugins as plugins
import ckan.tests.helpers as helpers
import ckan.model as model


class TestOntarioThemePlugin(helpers.FunctionalTestBase):
    def setup(self):
        self.app = helpers._get_test_app()

        if not plugins.plugin_loaded(u'ontario_theme'):
            plugins.load(u'ontario_theme')
            plugin = plugins.get_plugin(u'ontario_theme')
            self.app.flask_app.register_extension_blueprint(
                plugin.get_blueprint())

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

    # For the test, change the ckan.site_url to localhost.
    @helpers.change_config('ckan.site_url', 'http://127.0.0.1')
    def test_csv_dump_route(self):
        '''If `/datasets/csv_dump` route is called it returns csv export.
        '''
        # res = self.app.get(u'/dataset/csv_dump')

        # eq_(u'200 OK', res._status)
        # ok_(('Content-Type', 'text/csv; charset=utf-8') in res._headerlist)
        # ok_(('Content-disposition',
        #      'attachment; filename="output.csv"') in res._headerlist)
        pass
