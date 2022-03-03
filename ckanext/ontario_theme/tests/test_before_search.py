# encoding: utf-8

'''Unit tests for ontario_theme/tests/test_before_search.py.
'''

import pytest

from ckanext.ontario_theme.plugin import (
  num_resources_filter_scrub
)

@pytest.mark.usefixtures('clean_db', 'with_plugins', 'with_request_context')
class TestBeforeSearch(object):
  def test_before_search_with_good_value(self):
    u'''If search_params given num_resources remove double quotes around
    range.
    '''
    search_params = {'fq': u'num_resources:"[1 TO *]"', 'rows': 20, 'facet.field': [u'organization', u'groups', u'tags', u'res_format', u'license_id', 'access_level', 'update_frequency'], 'q': u'', 'start': 0, 'extras': {}, 'include_private': True}
    comparative_search_params = {'fq': u'num_resources:[1 TO *]',
                   'rows': 20,
                   'facet.field': [u'organization',
                                   u'groups',
                                   u'tags',
                                   u'res_format',
                                   u'license_id',
                                   'access_level',
                                   'update_frequency'],
                   'q': u'',
                   'start': 0,
                   'extras': {},
                   'include_private': True}
    assert num_resources_filter_scrub(search_params) == comparative_search_params

  def test_before_search_with_bad_value(self):
    u'''If search_params given num_resources with value other than "[1
    TO *]" do not modify.
    '''
    search_params = {'fq': u'num_resources:"[2 TO *]"', 'rows': 20, 'facet.field': [u'organization', u'groups', u'tags', u'res_format', u'license_id', 'access_level', 'update_frequency'], 'q': u'', 'start': 0, 'extras': {}, 'include_private': True}
    assert num_resources_filter_scrub(search_params) == search_params