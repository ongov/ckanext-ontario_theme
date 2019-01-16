# encoding: utf-8

'''Unit tests for extrafields/tests/test_before_search.py.
'''

import nose.tools
assert_equals = nose.tools.assert_equals
from ckanext.extrafields.plugin import (
  num_resources_filter_scrub
)

class TestBeforeSearch(object):
  def test_before_search_with_good_value(self):
    u'''If search_params given num_resources remove double quotes around
    range.
    '''
    search_params = {'fq': u'num_resources:"[1 TO *]"', 'rows': 20, 'facet.field': [u'organization', u'groups', u'tags', u'res_format', u'license_id', 'access_level', 'update_frequency'], 'q': u'', 'start': 0, 'extras': {}, 'include_private': True}
    assert_equals(num_resources_filter_scrub(search_params),
                  {'fq': u'num_resources:[1 TO *]',
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
                   'include_private': True})

  def test_before_search_with_bad_value(self):
    u'''If search_params given num_resources with value other than "[1
    TO *]" do not modify.
    '''
    search_params = {'fq': u'num_resources:"[2 TO *]"', 'rows': 20, 'facet.field': [u'organization', u'groups', u'tags', u'res_format', u'license_id', 'access_level', 'update_frequency'], 'q': u'', 'start': 0, 'extras': {}, 'include_private': True}
    assert_equals(num_resources_filter_scrub(search_params),
                  search_params)