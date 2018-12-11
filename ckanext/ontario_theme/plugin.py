import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import config

from flask import Blueprint, make_response
from flask import render_template, render_template_string

import ckanapi_exporter.exporter as exporter

def help():
    '''New help page for site.
    '''
    return render_template('home/help.html')

def csv_dump():
    '''The pattern allows you to go deeper into the nested structures.
    `["^title_translated$", "en"]` grabs the english title_translated value.
    It doesn't seem to handle returning a dict such as 
    `{'en': 'english', 'fr': 'french'}`.
    Exporting resource metadata is limited. It combines resource values into single 
    comma seperated string.
    deduplicate needed to be "true" not true.
    '''
    columns = {
                "Title EN": {
                    "pattern": ["^title_translated$", "^en$"]
                },
                "Title FR": {
                    "pattern": ["^title_translated$", "^fr$"]
                },
                "Notes EN": {
                    "pattern": ["^notes_translated$", "^en$"]
                },
                "Notes FR": {
                    "pattern": ["^notes_translated$", "^fr$"]
                },
                "Met Service Standard": {
                    "pattern": "^met_service_standard$"
                },
                "License Title": {
                    "pattern": "^license_title$"
                },
                "Technical Documents": {
                    "pattern": "^technical_documents$"
                },
                "Contains geopgrapic markers": {
                    "pattern": "^contains_geographic_markers$"
                },
                "Maintainer Branch EN": {
                    "pattern": ["^maintainer_branch$", "^en$"]
                },
                "Maintainer Branch FR": {
                    "pattern": ["^maintainer_branch$", "^fr$"]
                },
                "Keywords EN": {
                    "pattern": ["^keywords$", "^en$"]
                },
                "Keywords FR": {
                    "pattern": ["^keywords$", "^fr$"]
                },
                "Broken Links": {
                    "pattern": "^broken_links$"
                },
                "Id": {
                    "pattern": "^id$"
                },
                "Metadata Created": {
                    "pattern": "^metadata_created$"
                },
                "Open Access": {
                    "pattern": "^open_access$"
                },
                "Removed": {
                    "pattern": "^removed$"
                },
                "Metadata Modified": {
                    "pattern": "^metadata_modified$"
                },
                "Meets Update Frequency": {
                    "pattern": "^meets_update_frequency$"
                },
                "Comments EN": {
                    "pattern": ["^comments$", "^en$"]
                },
                "Comments FR": {
                    "pattern": ["^comments$", "^fr$"]
                },
                "Access Level": {
                    "pattern": "^access_level$"
                },
                "Data Range End": {
                    "pattern": "^data_range_end$"
                },
                "Exemption Rationale EN": {
                    "pattern": ["^exemption_rationale$", "^en$"]
                },
                "Exemption Rationale FR": {
                    "pattern": ["^exemption_rationale$", "^fr$"]
                },
                "Issues": {
                    "pattern": "^issues$"
                },
                "Short Description EN": {
                    "pattern": ["^short_description$", "^en$"]
                },
                "Short Description FR": {
                    "pattern": ["^short_description$", "^fr$"]
                },
                "Type": {
                    "pattern": "^type$"
                },
                "Resources Format": {
                    "pattern": ["^resources$", "^format$"],
                    "deduplicate": "true"
                },
                "Num Resources": {
                    "pattern": "^num_resources$"
                },
                "Tags": {
                    "pattern": ["^tags$", "^name$"],
                    "deduplicate": "true"
                },
                "Data Range Start": {
                    "pattern": "^data_range_start$"
                },
                "State": {
                    "pattern": "^state$"
                },
                "License Id": {
                    "pattern": "^license_id$"
                },
                "Exemption": {
                    "pattern": "^exemption$"
                },
                "Submission Comments EN": {
                    "pattern": ["^submission_comments$", "^en$"]
                },
                "Submission Comments FR": {
                    "pattern": ["^submission_comments$", "^fr$"]
                },
                "Geographic Coverage EN": {
                    "pattern": ["^geographic_coverage$", "^en$"]
                },
                "Geographic Coverage FR": {
                    "pattern": ["^geographic_coverage$", "^fr$"]
                },
                "Rush": {
                    "pattern": "^rush$"
                },
                "Organization Title": {
                    "pattern": ["^organization$", "^title$"]
                },
                "Submission Communication Plan EN": {
                    "pattern": ["^submission_communication_plan$", "^en$"]
                },
                "Submission Communication Plan FR": {
                    "pattern": ["^submission_communication_plan$", "^fr$"]
                },
                "Name": {
                    "pattern": "^name$"
                },
                "Is Open": {
                    "pattern": "^isopen$"
                },
                "URL": {
                    "pattern": "^url$"
                },
                "Technical Title EN": {
                    "pattern": ["^technical_title$", "^en$"]
                },
                "Technical Title FR": {
                    "pattern": ["^technical_title$", "^fr$"]
                },
                "Node Id": {
                    "pattern": "^node_id$"
                },
                "Removal Rationale EN": {
                    "pattern": ["^removal_rationale$", "^en$"]
                },
                "Removal Rationale FR": {
                    "pattern": ["^removal_rationale$", "^fr$"]
                },
                "Update Frequency": {
                    "pattern": "^update_frequency$"
                }
              }

    site_url = config.get('ckan.site_url')
    csv_string = exporter.export(site_url, columns)
    resp = make_response(csv_string, 200)
    resp.headers['Content-Type'] = b'text/csv; charset=utf-8'
    resp.headers['Content-disposition'] = (b'attachment; filename="output.csv"')
    return resp

class OntarioThemePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'ontario_theme')
        # Uncomment these to use bootstrap 2 theme and comment out
        # the above template and resource directories.
        # toolkit.add_template_directory(config_, 'templates-bs2')
        # toolkit.add_resource('fanstatic-bs2', 'ontario_theme')

    # IBlueprint

    def get_blueprint(self):
        '''Return a Flask Blueprint object to be registered by the app.
        '''

        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates'
        # Add url rules to Blueprint object.
        rules = [
            (u'/help', u'help', help), 
            (u'/dataset/csv_dump', u'csv_dump', csv_dump)
        ]
        for rule in rules:
            blueprint.add_url_rule(*rule)

        return blueprint
