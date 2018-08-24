
# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.plugins.toolkit import Invalid
import datetime

# Custome Validators

def update_frequency_validator(value):
    try:
        value = value.lower()
    except:
        raise Invalid('Invalid update frequency input value, must be string')
    if value not in ['as_required',
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
                     'yearly']:
        raise Invalid('Invalid update frequency input value')
    return value

def access_level_validator(value):
    try:
        value = value.lower()
    except:
        raise Invalid('Invalid access level input value, must be string')
    if value not in ['open',
                     'restricted',
                     'to_be_opened',
                     'under_review']:
        raise Invalid('Invalid access level input value')
    return value

def exemption_validator(value):
    if value == '': # Some systems set this as empty instead of 'none'.
      return 'none' # 'none' is the string value below.
    try:
        value = value.lower()
    except:
      raise Invalid('Invalid access level input value, must be string')
    if value not in ['commercial_sensitivity',
                     'confidentiality',
                     'legal_and_contractual_obligations',
                     'none',
                     'privacy',
                     'security']:
        raise Invalid('Invalid exemption input value')
    return value

def submission_type_validator(value):
    if value == '':
        return None # Let user update value to empty.
    try:
        value = value.lower()
    except:
        raise Invalid('Invalid submission_type input value, must be string')
    if value not in ['colby_candidate',
                     'public_to_open_dataset',
                     'new_open_dataset',
                     'new_dataset_not_open',
                     'open_existing_dataset)',
                     'major_update_of_open_data',
                     'major_update_of_non-open_dataset']:
        raise Invalid('Invalid submission_type input value')
    return value

def submission_status_validator(value):
    if value == '':
        return None # Let user update value to empty.  
    try:
        value = value.lower()
    except:
        raise Invalid('Invalid submission_status input value, must be a string')
    if value not in ['data_identified_for_internal_sharing',
                     'posted_to_colby',
                     'data_identified_for_opening',
                     'submission_in_development',
                     'metadata_under_reivew_by_ministry',
                     'metadata_in_translation',
                     'ogo_review',
                     'mo_review/fyi',
                     'uploading/updating',
                     'published']:
        raise Invalid('Invalid submission_status input value')
    return value

def machine_readable_validator(value):
    if value == '':
        return None # Let user update value to empty.  
    try:
        value = value.lower()
    except:
        raise Invalid('Invalid machine_readable input value, must be a string')
    if value not in ['open',
                     'not_preferred',
                     'not_open']:
        raise Invalid('Invalid machine_readable input value')
    return value

def time_series_validator(value):
    if value == '':
        return None # Let user update value to empty.
    try:
        value = value.lower()
    except:
        raise Invalid('Invalid time_series input value, must be a string')
    if value not in ['all_data_is_in_one_file',
                     'data_is_split_into_multiple_files',
                     'n/a']:
        raise Invalid('Invalid time_series input value')
    return value

def good_file_name_validator(value):
    if value == '':
        return None # Let user update value to empty.  
    try:
        value = value.lower()
    except:
        raise Invalid('Invalid good_file_name input value, must be a string')
    if value not in ['yes',
                     'needs_improvement',
                     'mo']:
        raise Invalid('Invalid good_file_name input value')
    return value

def date_validator(value):
    '''Create custom date_validator that modifies the existing 
    validation for isodate. The original throws errors when 
    trying to use with extra_fields and date inputs and the api.
    This seemed to be appropriate solution.
    There was a little mention of this on github but nothing solid.
    '''
    if value == '':
        return None
    try:
        datetime.datetime.strptime(value, '%Y-%m-%d')
    except:
        raise Invalid('Date format incorrect, should be YYYY-MM-DD')
    return value

class ExtrafieldsPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IConfigurer)

    # IConfigurer

    def update_config(self, config_):
        # Add plugin's template directory to CKAN's extra_template_paths
        # to use the new templates.
        toolkit.add_template_directory(config_, 'templates')
        # toolkit.add_public_directory(config_, 'public')
        # toolkit.add_resource('fanstatic', 'extrafields')

    # IDatasetForm

    def _modify_package_schema(self, schema):
        # Custom fields for update and create of packages.
        schema.update({
            # TODO: Look into issues with using is_positive_integer validator. 
            #       When it's missing its still triggered.
            'node_id': [toolkit.get_validator('ignore_missing'),
                        toolkit.get_validator('int_validator'),
                        toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'technical_title': [toolkit.get_validator('ignore_missing'),
                                toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'short_description': [toolkit.get_validator('not_empty'),
                                  toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'maintainer_branch': [toolkit.get_validator('ignore_missing'),
                                  toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'data_range_start': [toolkit.get_validator('ignore_missing'),
                                 date_validator,
                                 toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'data_range_end': [toolkit.get_validator('ignore_missing'),
                               date_validator,
                               toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'data_birth_date': [toolkit.get_validator('ignore_missing'),
                                date_validator,
                                toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'opened_date': [toolkit.get_validator('ignore_missing'),
                            date_validator,
                            toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'dataset_published_date': [toolkit.get_validator('ignore_missing'),
                                       date_validator,
                                       toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'contains_geographic_markers': [toolkit.get_validator('boolean_validator'),
                                            toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'geographic_coverage': [toolkit.get_validator('ignore_missing'),
                                    toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'update_frequency': [toolkit.get_validator('ignore_missing'),
                                 update_frequency_validator,
                                 toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'access_level': [toolkit.get_validator('ignore_missing'),
                             access_level_validator,
                             toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'exemption': [toolkit.get_validator('ignore_missing'),
                          exemption_validator,
                          toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'exemption_rationale': [toolkit.get_validator('ignore_missing'),
                                    toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'comments': [toolkit.get_validator('ignore_missing'),
                         toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'target_posting_date': [toolkit.get_validator('ignore_missing'),
                                    date_validator,
                                    toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'assessment_date': [toolkit.get_validator('ignore_missing'),
                                date_validator,
                                toolkit.get_converter('convert_to_extras')]
        })

        # Submission Tracking Fields

        schema.update({
            'submission_type': [toolkit.get_validator('ignore_missing'),
                                submission_type_validator,
                                toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'submission_status': [toolkit.get_validator('ignore_missing'),
                                  submission_status_validator,
                                  toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'rush': [toolkit.get_validator('boolean_validator'),
                     toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'issues': [toolkit.get_validator('boolean_validator'),
                       toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'submission_comments': [toolkit.get_validator('ignore_missing'),
                                    toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'submission_communication_plan': [toolkit.get_validator('ignore_missing'),
                                              toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'submission_recieved_date': [toolkit.get_validator('ignore_missing'),
                                         date_validator,
                                         toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'submission_service_standard_date': [toolkit.get_validator('ignore_missing'),
                                                 date_validator,
                                                 toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'plain_language_start_date': [toolkit.get_validator('ignore_missing'),
                                          date_validator,
                                          toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'plain_language_end_date': [toolkit.get_validator('ignore_missing'),
                                        date_validator,
                                        toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'final_review_date': [toolkit.get_validator('ignore_missing'),
                                  date_validator,
                                  toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'with_co_date': [toolkit.get_validator('ignore_missing'),
                             date_validator,
                             toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'met_service_standard': [toolkit.get_validator('boolean_validator'),
                                     toolkit.get_converter('convert_to_extras')]
        })

        # Archive Tracking Fields

        schema.update({
            'removed': [toolkit.get_validator('boolean_validator'),
                        toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'removal_rationale': [toolkit.get_validator('ignore_missing'),
                                  toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'date_removed': [toolkit.get_validator('ignore_missing'),
                             date_validator,
                             toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'forwarding_url': [toolkit.get_validator('ignore_missing'),
                               toolkit.get_converter('convert_to_extras')]
        })

        # Data Quality Fields

        schema.update({
            'meets_update_frequency': [toolkit.get_validator('boolean_validator'),
                                       toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'technical_documents': [toolkit.get_validator('ignore_missing'),
                                    toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'broken_links': [toolkit.get_validator('boolean_validator'),
                             toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'open_access': [toolkit.get_validator('boolean_validator'),
                            toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'machine_readable': [toolkit.get_validator('ignore_missing'),
                                 machine_readable_validator,
                                 toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'postal_code_format': [toolkit.get_validator('ignore_missing'),
                                   toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'fiscal_year_format': [toolkit.get_validator('ignore_missing'),
                                   toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'date_format': [toolkit.get_validator('ignore_missing'),
                            toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'time_series': [toolkit.get_validator('ignore_missing'),
                            time_series_validator,
                            toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'good_file_name': [toolkit.get_validator('ignore_missing'),
                               good_file_name_validator,
                               toolkit.get_converter('convert_to_extras')]
        })

        schema.update({
            'last_updated_in_catalogue': [toolkit.get_validator('ignore_missing'),
                                          date_validator,
                                          toolkit.get_converter('convert_to_extras')]
        })

        return schema

    def create_package_schema(self):
        # Get the default schema.
        schema = super(ExtrafieldsPlugin, self).create_package_schema()
        # Add custom field(s).
        schema = self._modify_package_schema(schema)
        return schema

    def update_package_schema(self):
        # Get the default schema.
        schema = super(ExtrafieldsPlugin, self).update_package_schema()
        # Add custom field(s).
        schema = self._modify_package_schema(schema)
        return schema

    def show_package_schema(self):
        schema = super(ExtrafieldsPlugin, self).show_package_schema()
        schema.update({
            'node_id': [toolkit.get_converter('convert_from_extras'),
                        toolkit.get_validator('ignore_missing'),
                        toolkit.get_validator('int_validator')]
        })

        schema.update({
            'technical_title': [toolkit.get_converter('convert_from_extras'),
                                toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'short_description': [toolkit.get_converter('convert_from_extras'),
                                  toolkit.get_validator('not_empty')]
        })

        schema.update({
            'maintainer_branch': [toolkit.get_converter('convert_from_extras'),
                                  toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'data_range_start': [toolkit.get_converter('convert_from_extras'),
                                 date_validator,
                                 toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'data_range_end': [toolkit.get_converter('convert_from_extras'),
                               date_validator,
                               toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'data_birth_date': [toolkit.get_converter('convert_from_extras'),
                                date_validator,
                                toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'opened_date': [toolkit.get_converter('convert_from_extras'),
                            date_validator,
                            toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'dataset_published_date': [toolkit.get_converter('convert_from_extras'),
                                       date_validator,
                                       toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'contains_geographic_markers': [toolkit.get_converter('convert_from_extras'),
                                            toolkit.get_validator('boolean_validator')]
        })

        schema.update({
            'geographic_coverage': [toolkit.get_converter('convert_from_extras'),
                                    toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'update_frequency': [toolkit.get_converter('convert_from_extras'),
                                 update_frequency_validator,
                                 toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'access_level': [toolkit.get_converter('convert_from_extras'),
                             access_level_validator,
                             toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'exemption': [toolkit.get_converter('convert_from_extras'),
                          exemption_validator,
                          toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'exemption_rationale': [toolkit.get_converter('convert_from_extras'),
                                    toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'comments': [toolkit.get_converter('convert_from_extras'),
                         toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'target_posting_date': [toolkit.get_converter('convert_from_extras'),
                                    date_validator,
                                    toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'assessment_date': [toolkit.get_converter('convert_from_extras'),
                                date_validator,
                                toolkit.get_validator('ignore_missing')]
        })

        # Submission Tracking Fields

        schema.update({
            'submission_type': [toolkit.get_converter('convert_from_extras'),
                                submission_type_validator,
                                toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'submission_status': [toolkit.get_converter('convert_from_extras'),
                                  submission_status_validator,
                                  toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'rush': [toolkit.get_converter('convert_from_extras'),
                     toolkit.get_validator('boolean_validator')]
        })

        schema.update({
            'issues': [toolkit.get_converter('convert_from_extras'),
                       toolkit.get_validator('boolean_validator')]
        })

        schema.update({
            'submission_comments': [toolkit.get_converter('convert_from_extras'),
                                    toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'submission_communication_plan': [toolkit.get_converter('convert_from_extras'),
                                              toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'submission_recieved_date': [toolkit.get_converter('convert_from_extras'),
                                         date_validator,
                                         toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'submission_service_standard_date': [toolkit.get_converter('convert_from_extras'),
                                                 date_validator,
                                                 toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'plain_language_start_date': [toolkit.get_converter('convert_from_extras'),
                                          date_validator,
                                          toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'plain_language_end_date': [toolkit.get_converter('convert_from_extras'),
                                        date_validator,
                                        toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'final_review_date': [toolkit.get_converter('convert_from_extras'),
                                  date_validator,
                                  toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'with_co_date': [toolkit.get_converter('convert_from_extras'),
                             date_validator,
                             toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'met_service_standard': [toolkit.get_converter('convert_from_extras'),
                                     toolkit.get_validator('boolean_validator')]
        })

        # Archive Tracking Fields

        schema.update({
            'removed': [toolkit.get_converter('convert_from_extras'),
                        toolkit.get_validator('boolean_validator')]
        })

        schema.update({
            'removal_rationale': [toolkit.get_converter('convert_from_extras'),
                                  toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'date_removed': [toolkit.get_converter('convert_from_extras'),
                             date_validator,
                             toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'forwarding_url': [toolkit.get_converter('convert_from_extras'),
                               toolkit.get_validator('ignore_missing')]
        })

        # Data Quality Fields

        schema.update({
            'meets_update_frequency': [toolkit.get_converter('convert_from_extras'),
                                       toolkit.get_validator('boolean_validator')]
        })

        schema.update({
            'technical_documents': [toolkit.get_converter('convert_from_extras'),
                                    toolkit.get_validator('boolean_validator')]
        })

        schema.update({
            'broken_links': [toolkit.get_converter('convert_from_extras'),
                             toolkit.get_validator('boolean_validator')]
        })

        schema.update({
            'open_access': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('boolean_validator')]
        })

        schema.update({
            'machine_readable': [toolkit.get_converter('convert_from_extras'),
                                 machine_readable_validator,
                                 toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'postal_code_format': [toolkit.get_converter('convert_from_extras'),
                                   toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'fiscal_year_format': [toolkit.get_converter('convert_from_extras'),
                                   toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'date_format': [toolkit.get_converter('convert_from_extras'),
                            toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'time_series': [toolkit.get_converter('convert_from_extras'),
                            time_series_validator,
                            toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'good_file_name': [toolkit.get_converter('convert_from_extras'),
                               good_file_name_validator,
                               toolkit.get_validator('ignore_missing')]
        })

        schema.update({
            'last_updated_in_catalogue': [toolkit.get_converter('convert_from_extras'),
                                          date_validator,
                                          toolkit.get_validator('ignore_missing')]
        })

        return schema

    def is_fallback(self):
       # Register as default this plugin as the default handler for
       # packages not handled by other IDatasetForm plugins.
       return True

    def package_types(self):
        # Register as the default for all package types.
        # e.g. package type is none so go to default (above).
        return []
