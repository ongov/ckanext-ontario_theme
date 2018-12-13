# encoding: utf-8

'''Test for helpers in plugin.py
'''
import nose.tools
assert_equals = nose.tools.assert_equals
from ckan.common import config

from ckanext.ontario_theme.plugin import (get_license)
import json
import os

class TestGetLicense(object):
  def test_get_license_returns_proper_value(self):
    '''Ensure get_license returns proper license object from licences.json.
    '''
    with open(os.path.join(
      os.path.dirname(__file__), '..', 'licences.json')
    ) as licenses:
      license = json.load(licenses)[0]
    assert_equals(get_license("OGL-ON-1.0")._data, license)