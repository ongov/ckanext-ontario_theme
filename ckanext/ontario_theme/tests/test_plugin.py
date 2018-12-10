"""Tests for plugin.py."""
from nose.tools import eq_, ok_

from ckan.exceptions import HelperError
import ckan.plugins as plugins
import ckan.tests.helpers as helpers

class TestOntarioThemePlugin(helpers.FunctionalTestBase):
    def setup(self):
        self.app = helpers._get_test_app()

        if not plugins.plugin_loaded(u'ontario_theme'):
            plugins.load(u'ontario_theme')
            plugin = plugins.get_plugin(u'ontario_theme')
            self.app.flask_app.register_extension_blueprint(plugin.get_blueprint())

    # For the test, change the ckan.site_url to localhost.
    @helpers.change_config('ckan.site_url', 'http://127.0.0.1')
    def test_csv_dump_route(self):
        '''If `/datasets/csv_dump` route is called it returns csv export.
        '''
        res = self.app.get(u'/dataset/csv_dump')

        eq_(u'200 OK', res._status)
        ok_(('Content-Type', 'text/csv; charset=utf-8') in res._headerlist)
        ok_(('Content-disposition', 'attachment; filename="output.csv"') in res._headerlist)