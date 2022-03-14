"""Tests for plugin.py."""

import pytest

import datetime
import ckan.tests.helpers as helpers

@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context','app')
class TestOntarioThemePlugin(helpers.FunctionalTestBase):

    def setup(self):
        """Reset the database and clear the search indexes."""
        '''
        We need to overwrite the CKAN Core setup function
        because it calls functions that don't exist.
        We already clean/reset the db using the clean_db fixture
        '''
        return True

    # For the test, change the ckan.site_url to localhost.
    @helpers.change_config('ckan.site_url', 'http://127.0.0.1')
    def test_csv_dump_route(self, app):
        '''If `/datasets/inventory` route is called it returns csv export.
        '''

        res = app.get(u'/dataset/inventory')

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d')
        csv_filename = 'ontario_data_catalogue_inventory_' + timestamp

        assert u'200 OK' == res._status
        assert (
            res.headers.get("Content-Type")
            == 'text/csv; charset=utf-8'
        )
        assert (
            res.headers.get("Content-disposition")
            == 'attachment; filename="'+csv_filename+'.csv"'
        )
        pass