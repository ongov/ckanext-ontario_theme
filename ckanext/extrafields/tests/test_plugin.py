# encoding: utf-8

'''Unit tests for extrafields/tests/test_plugin.py.
Tried to follow test format from the unit tests for ckan/logic/validators.py in
CKAN core but trimmed down.

The ckan core tests were a bit too complex for the basic testing currently
being done here. Refactor if / when tests become more complex.
'''
import ckan.lib.navl.dictization_functions as df
import nose.tools
import datetime

import ckanext.extrafields.plugin as extrafields

assert_equals = nose.tools.assert_equals

class TestUpdateFrequencyValidator(object):

    def test_update_frequency_validator_with_invalid_value(self):
        '''If given an invalid value update_frequency_validator() should raise Invalid.
        '''
        invalid_update_frequencies = [
            # Non-string frequencies aren't allowed.
            13,
            23.7,
            100,
            1.0j,
            None,
            True,
            False,
            ('a', 2, False),
            [13, None, True],
            {'foo': 'bar'},
            lambda x: x ** 2,

            # Strings not in list aren't allowed.
            'month-by-month',
            'July',
            'Month',
            'month',
            'as required',
            ''
        ]

        for invalid_update_frequency in invalid_update_frequencies:
            def call_validator(*args, **kwargs):
                return extrafields.update_frequency_validator(*args, **kwargs)
            nose.tools.assert_raises(df.Invalid, call_validator, invalid_update_frequency)

    def test_update_frequency_validator_with_valid_value(self):
        '''If given a valid string update_frequency_validator() should return a 
        lower cased version.
        '''
        valid_update_frequencies = [
            # Allowed strings from plugin.
            'as_required',
            'biannually',
            'current',
            'daily',
            'historical',
            'monthly',
            'never',
            'on_demand',
            'other',
            'periodically',
            'quarterly',
            'weekly',
            'yearly'
        ]

        for valid_update_frequency in valid_update_frequencies:
            def call_validator(*args, **kwargs):
                return extrafields.update_frequency_validator(*args, **kwargs)
            assert call_validator(valid_update_frequency) == valid_update_frequency.lower(), (
                'Should return lower case value if in list of accepted values')

class TestAccessLevelValidator(object):

    def test_access_level_validator_with_invalid_value(self):
        '''If given an invalid value access_level_validator() should raise Invalid.
        '''
        invalid_access_levels = [
            # Non-strings aren't allowed.
            13,
            23.7,
            100,
            1.0j,
            None,
            True,
            False,
            ('a', 2, False),
            [13, None, True],
            {'foo': 'bar'},
            lambda x: x ** 2,

            # Strings not in list aren't allowed.
            'restrict',
            'opens',
            'under review',
            ''
        ]

        for invalid_access_level in invalid_access_levels:
            def call_validator(*args, **kwargs):
                return extrafields.access_level_validator(*args, **kwargs)
            nose.tools.assert_raises(df.Invalid, call_validator, invalid_access_level)

    def test_access_level_validator_with_valid_value(self):
        '''If given a valid string access_level_validator() should return a 
        lower cased version.
        '''
        valid_access_levels = [
            # Allowed strings from plugin.
            'open',
            'to_be_opened',
            'under_Review',
            'restricted'
        ]

        for valid_access_level in valid_access_levels:
            def call_validator(*args, **kwargs):
                return extrafields.access_level_validator(*args, **kwargs)
            assert call_validator(valid_access_level) == valid_access_level.lower(), (
                'Should return lower case value if in list of accepted values')

class TestExemptionValidator(object):

    def test_exemption_validator_with_invalid_value(self):
        '''If given an invalid value exemption_validator() should raise Invalid.
        '''
        invalid_exemptions = [
            # Non-strings aren't allowed.
            13,
            23.7,
            100,
            1.0j,
            None,
            True,
            False,
            ('a', 2, False),
            [13, None, True],
            {'foo': 'bar'},
            lambda x: x ** 2,

            # Strings not in list aren't allowed.
            'Legal',
            'No',
            'commercially sensitive',
            ''
        ]

        for invalid_exemption in invalid_exemptions:
            def call_validator(*args, **kwargs):
                return extrafields.exemption_validator(*args, **kwargs)
            nose.tools.assert_raises(df.Invalid, call_validator, invalid_exemption)

    def test_exemption_validator_with_valid_value(self):
        '''If given a valid string exemption_validator() should return a 
        lower cased version.
        '''
        valid_exemptions = [
            # Allowed strings from plugin.
            'commercial_sensitivity',
            'confidentiality',
            'legal_and_contractual_obligations',
            'none',
            'privacy',
            'security'
        ]

        for valid_exemption in valid_exemptions:
            def call_validator(*args, **kwargs):
                return extrafields.exemption_validator(*args, **kwargs)
            assert call_validator(valid_exemption) == valid_exemption.lower(), (
                'Should return lower case value if in list of accepted values')

class TestDateValidator(object):

    def test_date_validator_with_invalid_value(self):
        '''If given an invalid value date_validator() should raise Invalid.
        '''
        invalid_dates = [
            # Non-date values aren't allowed.
            13,
            23.7,
            100,
            1.0j,
            None,
            True,
            False,
            ('a', 2, False),
            [13, None, True],
            {'foo': 'bar'},
            lambda x: x ** 2,

            # Strings not in list aren't allowed.
            'Legal',

            # Improperly formatted date strings
            '2019-14-45',
            '2019-0619',
            '2019-06-',
            '20190619',
            '20194-05-01',
            '1998-444-30',
            '1999-12-123',
            '100-06-01',
            '2012-01-01 05:07:06',
            '2001-02-03T00:00:00+00:00'
        ]

        for invalid_date in invalid_dates:
            def call_validator(*args, **kwargs):
                return extrafields.date_validator(*args, **kwargs)
            nose.tools.assert_raises(df.Invalid, call_validator, invalid_date)

    def test_date_validator_with_valid_string_date_value(self):
        '''If given a valid date date_validator() should return a 
        the unchanged value.
        Valid dates include dates in format of YYYY-MM-DD.
        '''
        valid_dates = [
            # Allowed dates from plugin.
            '2019-06-12',
            '1998-01-28',
            '1000-10-24',
            '9099-6-1'
        ]

        for valid_date in valid_dates:
            def call_validator(*args, **kwargs):
                return extrafields.date_validator(*args, **kwargs)
            assert call_validator(valid_date) == valid_date, (
                'Should return unchanged date value if in list of accepted values')

    def test_date_validator_with_valid_empty_date_value(self):
        '''If given a valid date date_validator() should return a 
        the unchanged value.
        Valid dates include dates in format of YYYY-MM-DD.
        '''
        valid_dates = [
            # Allowed dates from plugin.
            ''
        ]

        for valid_date in valid_dates:
            def call_validator(*args, **kwargs):
                return extrafields.date_validator(*args, **kwargs)
            assert call_validator(valid_date) == None, (
                'Should return None if empty string passed')