# encoding: utf-8

'''Test for helpers in plugin.py.
'''
import nose.tools
assert_equals = nose.tools.assert_equals
from ckan.common import config

from ckanext.extrafields.plugin import (
  default_locale
)

class TestDefaultLocale(object):
  def test_default_locale_returns_proper_value(self):
    default = config.get('ckan.locale_default', 'en')
    assert_equals(default_locale(), default)