# coding=utf-8
import json
import datetime
import re
import logging
import requests
import html2text
import lxml.etree
from hashlib import sha1
import traceback
import uuid

import six
from ckan import model
from ckan import logic
from ckan import plugins as p
from ckanext.harvest.model import HarvestObject, HarvestObjectExtra
from ckanext.harvest.harvesters import HarvesterBase

from ckanext.ontario_theme import helpers as ontario_theme_helpers
import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)

blacklist_url = "https://services9.arcgis.com/a03W7iZ8T3s5vB7p/ArcGIS/rest/services/odc_sync_blacklist_vw/FeatureServer/0/query?where=1%3D1&outFields=geohub_dataset_url&f=json"

restricted_tags = {
    "MNRFNHICClassifiedData": {
        "access_instructions" : {
            "en": "Email the Natural Heritage Information Centre or phone us at 705-755-2159 to inquire about a Sensitive Data Use Licence.",
            "fr": "Veuillez envoyer un courriel au Centre d'information sur le patrimoine naturel ou communiquer avec nous par téléphone au numéro 705 755-2159 pour demander une convention de droits d'utilisation de données sensibles."
        },
        "exemption" : "security",
        "exemption_rationale": {
            "en": "Potential for deliberate harm to critical infrastructure (some data include sensitive values or locations of at-risk species)",
            "fr": "Des dommages pourraient délibérément être causés à l’infrastructure essentielle (certaines données incluent des valeurs sensibles ou l’emplacement d’espèces en péril)"
        }
    },
    "RUL": {
        "exemption":"security",
        "exemption_rationale": {
            "en": "Potential for deliberate harm to critical infrastructure (some data include sensitive values or locations of at-risk species). Data subject to existing licensing agreement.",
            "fr": "Des dommages pourraient délibérément être causés à l’infrastructure essentielle (certaines données incluent des valeurs sensibles ou l’emplacement d’espèces en péril). Les données sont assujetties à un contrat de licence existant."
        } 
    },
    "OGDE": {
        "exemption": "security",
        "exemption_rationale": {
            "en": "Potential for deliberate harm to critical infrastructure (some data include sensitive values or locations of at-risk species). Data subject to existing licensing agreement.",
            "fr": "Des dommages pourraient délibérément être causés à l’infrastructure essentielle (certaines données incluent des valeurs sensibles ou l’emplacement d’espèces en péril). Les données sont assujetties à un contrat de licence existant."
        },  
        "access_instructions": {
            "en": "Complete and sign the [OGDE Membership Application Form](https://www.sdc.gov.on.ca/sites/MNRF-PublicDocs/EN/CMID/LIO-OGDE-MembershipForm.pdf) and submit it to the Ontario Ministry of Natural Resources and Forestry.",
            "fr": "[Remplir le formulaire](https://www.sdc.gov.on.ca/sites/MNRF-PublicDocs/EN/CMID/LIO-OGDE-MembershipForm.pdf) and submit it to the Ontario Ministry of Natural Resources and Forestry."
        }  
    },
    "OntarioParcel": {
        "exemption": "legal",
        "exemption_rationale": {
            "en": "Subject to other restrictions, do not have the right to release publicly (tri-party commercial product).",
            "fr": "Sous réserve d’autres restrictions, il est interdit de publier les données publiquement (produit commercial tripartite)."
        } 
    }
}

class OntarioGeohubHarvester(HarvesterBase):

    force_import = False
    # modified from the DCATHarvester harvester from https://github.com/ckan/ckanext-dcat

    def _get_content_and_type(self, url, harvest_job, page=1,
                              content_type=None):
        '''
        Gets the content and type of the given url.
        :param url: a web url (starting with http) or a local path
        :param harvest_job: the job, used for error reporting
        :param page: adds paging to the url
        :param content_type: will be returned as type
        :return: a tuple containing the content and content-type
        '''
        try:

            log.debug('Getting file %s', url)

            # get the `requests` session object
            session = requests.Session()

            r = session.get(url, stream=True)
            content = r.content

            if not six.PY2:
                content = content.decode('utf-8')

            if content_type is None and r.headers.get('content-type'):
                content_type = r.headers.get('content-type').split(";", 1)[0]

            return content, content_type

        except requests.exceptions.HTTPError as error:
            msg = 'Could not get content from %s. Server responded with %s %s'\
                % (url, error.response.status_code, error.response.reason)
            self._save_gather_error(msg, harvest_job)
            return None, None
        except requests.exceptions.ConnectionError as error:
            msg = '''Could not get content from %s because a
                                connection error occurred. %s''' % (url, error)
            self._save_gather_error(msg, harvest_job)
            return None, None
        except requests.exceptions.Timeout as error:
            msg = 'Could not get content from %s because the connection timed'\
                ' out.' % url
            self._save_gather_error(msg, harvest_job)
            return None, None

    def _get_object_extra(self, harvest_object, key):
        '''
        Helper function for retrieving the value from a harvest object extra,
        given the key
        '''
        for extra in harvest_object.extras:
            if extra.key == key:
                return extra.value
        return None

    def _get_package_name(self, harvest_object, title):

        package = harvest_object.package
        if package is None or package.title != title:
            name = self._gen_new_name(title)
            if not name:
                raise Exception(
                    'Could not generate a unique name from the title or the '
                    'GUID. Please choose a more unique title.')
        else:
            name = package.name

        return name

    def get_original_url(self, harvest_object_id):
        obj = model.Session.query(HarvestObject). \
            filter(HarvestObject.id == harvest_object_id).\
            first()
        if obj:
            return obj.source.url
        return None

    def _read_datasets_from_db(self, guid):
        '''
        Returns a database result of datasets matching the given guid.
        '''

        datasets = model.Session.query(model.Package.id) \
                                .join(model.PackageExtra) \
                                .filter(model.PackageExtra.key == 'guid') \
                                .filter(model.PackageExtra.value == guid) \
                                .filter(model.Package.state == 'active') \
                                .all()
        return datasets

    def _get_existing_dataset(self, guid):
        '''
        Checks if a dataset with a certain guid extra already exists
        Returns a dict as the ones returned by package_show
        '''

        datasets = self._read_datasets_from_db(guid)

        if not datasets:
            return None
        elif len(datasets) > 1:
            log.error('Found more than one dataset with the same guid: {0}'
                      .format(guid))

        return p.toolkit.get_action('package_show')({}, {'id': datasets[0][0]})


    def _make_package_dict(self, geohub_dict, harvest_object):
        english_xml = english_metadata_xml_response(geohub_dict['identifier'])
        french_xml = french_metadata_xml_response(geohub_dict['identifier']) 

        package_dict = {
            "id": identifier_from_url_with_index(geohub_dict['identifier']), # Use geohub ID.
            "url": geohub_dict["landingPage"],
            "license_id": "other-open", 
            "title_translated": {
                "en": geohub_dict["title"],
                "fr": french_title(french_xml)
            },
            "notes_translated": {
                "en": html2text.html2text(geohub_dict["description"]),
                "fr": html2text.html2text(french_notes(french_xml))
            },
            "keywords": {
                "en": ontario_theme_helpers.remove_odd_chars_from_keywords(geohub_dict["keyword"]) + ['ontario-geohub'],
                "fr": ontario_theme_helpers.remove_odd_chars_from_keywords(french_keywords(french_xml)) + ['ontario-geohub']
            },
            "opened_date": ontario_theme_helpers.date_parse(geohub_dict["issued"], '%Y-%m-%dT%H:%M:%S.%fZ'),
            "current_as_of": ontario_theme_helpers.date_parse(geohub_dict["modified"], '%Y-%m-%dT%H:%M:%S.%fZ'),
            "maintainer_translated": {
                "en" : "Land Information Ontario",
                "fr" : "Information sur les terres de l'Ontario"
            },
            "maintainer_email": "lio@ontario.ca",
            "access_level": "open",
            "resources": build_resources(geohub_dict['distribution'],
                                         identifier_from_url(geohub_dict['identifier']),
                                         english_xml,
                                         geohub_dict['landingPage']),
            "update_frequency": "other",
            "exemption": "none",
            "exemption_rationale": {
                "en": "",
                "fr": ""
            },
            "name": ontario_theme_helpers.name_cleaner(geohub_dict["title"]),
            "private": False,
            "state": "active",
            "groups": [{'name': 'ontario-geohub'}] # optional
        }

        if package_dict["notes_translated"]["en"] == "" and get_backup_description_from_xml(english_xml):
            package_dict["notes_translated"]["en"] = get_backup_description_from_xml(english_xml)

        # get license
        # license = get_license_from_xml(english_xml)
        if 'open data' in package_dict['keywords']['en']:
            package_dict["license_id"] = "OGL-ON-1.0"
            package_dict['keywords']['en'].remove('open data')

        for restricted_tag in restricted_tags:
            if restricted_tag in package_dict['keywords']['en']:
                package_dict['access_level'] = "restricted"
                package_dict["license_id"] = restricted_tag.lower()  
                package_dict.update(restricted_tags[restricted_tag])                                  
                break

        geohub_update_frequency = extract_update_frequency(package_dict['notes_translated']['en'])
        if geohub_update_frequency:
            package_dict['update_frequency'] = update_frequencies[geohub_update_frequency]

        # get maintainer name and maintainer email
        geohub_contact_info = extract_contact_info(package_dict['notes_translated']['en'])
        if geohub_contact_info:
                geohub_fr_contact_info = extract_fr_contact_info(package_dict['notes_translated']['fr'])
                package_dict['maintainer_email'] = geohub_contact_info['maintainer_email']
                package_dict['maintainer_translated']['en'] = geohub_contact_info['maintainer_name']

                if "maintainer_branch" in geohub_contact_info:
                    package_dict['maintainer_branch'] = {
                        'en' : geohub_contact_info['maintainer_branch']  
                    }
                if geohub_fr_contact_info:
                    package_dict['maintainer_translated']['fr'] = geohub_fr_contact_info['maintainer_name']
                    if "maintainer_branch" in geohub_fr_contact_info:
                        package_dict['maintainer_branch']['fr'] = geohub_fr_contact_info['maintainer_branch']                
                else: 
                    package_dict['maintainer_translated']['fr'] = package_dict['maintainer_translated']['en']
                    
                if not package_dict.get("owner_org", False) and 'ministry' in geohub_contact_info:
                    package_dict['owner_org'] = get_org_id(geohub_contact_info['ministry'])
        else:

            contact = extract_ontario_email(package_dict['notes_translated']['en'])
            if contact:
                package_dict['maintainer_email'] = contact.strip()
                if geohub_dict["contactPoint"]["fn"]:
                    package_dict['maintainer_translated']['en'] = geohub_dict["contactPoint"]["fn"]
                elif package_dict['maintainer_email'].replace("@ontario.ca","").find(".") == -1:
                    package_dict['maintainer_translated']['en'] = package_dict['maintainer_email'].replace("@ontario.ca","").strip()
                else:
                    package_dict['maintainer_translated']['en'] = get_ontario_employee_name(package_dict['maintainer_email'])
                package_dict['maintainer_translated']['fr'] = package_dict['maintainer_translated']['en']


        # first, check whether the ministry is in the metadata
        if not package_dict.get("owner_org", False):
            ministry = get_ministry_from_xml(english_xml)
            if ministry:
                package_dict['owner_org'] = get_org_id(ministry) 
            # if it isn't there, look in the description for ministry names           
            else:
                # extract ministry
                ministry = extract_ministry(package_dict['notes_translated']['en'], package_dict['maintainer_email'])
                if ministry:
                    package_dict['owner_org'] = get_org_id(ministry)
                else:
                    ministry = publisher_ministry(geohub_dict)
                    if ministry:
                        package_dict['owner_org'] = get_org_id(ministry)
                    else:
                        package_dict['owner_org'] = get_org_id("natural-resources-and-forestry")

        return package_dict


    def geohub_identifier_from_url(self, identifier_url):
        '''Returns a string id with the layer index if it exists.
        '''
        identifier = identifier_url.split('/')[-1] # keep layer index.
        return identifier

    def has_french(self, identifier_url):
        '''Returns boolean.
        '''

        identifier = self.geohub_identifier_from_url(identifier_url)
        french_xml = french_metadata_xml_response(identifier) 

        if french_notes(french_xml) == "Placeholder":
            return False
        else:
            return True

    def hubtype_table(self, identifier_url):
        '''Returns boolean.
        If hubtype_table returns true, skip the record.
        hubtype: "table" ignore it.  These are "sub-sets" of existing datasets.
        relations will be in the description for now anyway. 
        This value is only available through the geohub api and requires its own call.
        '''
        is_table = False

        identifier = self.geohub_identifier_from_url(identifier_url)
        geohub_endpoint = "https://geohub.lio.gov.on.ca/api/v3/datasets/{}".format(identifier)
        geohub_response = requests.get(geohub_endpoint)
        hubType = geohub_response.json()["data"]["attributes"]["hubType"]

        if hubType == "Table":
            is_table = True

        return is_table

    def info(self):
        return {
            'name': 'ontario_geohub',
            'title': 'Ontario Geohub',
            'description': 'Harvester for Ontario Geohub'
        }


    def _get_blacklist(self):
        blacklist_response = requests.get(blacklist_url)
        return list(map(lambda x: x['attributes']['geohub_dataset_url'], blacklist_response.json()['features']))

    def _get_guids_and_datasets(self, content):

        blacklist = self._get_blacklist()

        doc = json.loads(content)

        if isinstance(doc, list):
            # Assume a list of datasets
            datasets = doc
        elif isinstance(doc, dict):
            datasets = doc.get('dataset', [])
        else:
            raise ValueError('Wrong JSON object')

        for dataset in datasets:

            as_string = json.dumps(dataset)

            # Get identifier
            guid = dataset.get('identifier')

            if not guid:
                # This is bad, any ideas welcomed
                guid = sha1(as_string).hexdigest()

            if guid not in blacklist and not self.hubtype_table(guid) and self.has_french(guid):
                yield guid, as_string

    def fetch_stage(self, harvest_object):
        return True

    def _get_package_dict(self, harvest_object):

        content = harvest_object.content

        geohub_dict = json.loads(content)

        package_dict = self._make_package_dict(geohub_dict,
                                                harvest_object)

        return package_dict, geohub_dict


    def gather_stage(self, harvest_job):
        log.debug('In DCATJSONHarvester gather_stage')

        ids = []

        # Get the previous guids for this source
        query = \
            model.Session.query(HarvestObject.guid, HarvestObject.package_id) \
            .filter(HarvestObject.current == True) \
            .filter(HarvestObject.harvest_source_id == harvest_job.source.id)
        guid_to_package_id = {}

        for guid, package_id in query:
            guid_to_package_id[guid] = package_id

        guids_in_db = list(guid_to_package_id.keys())

        guids_in_source = []

        # Get file contents
        url = harvest_job.source.url

        previous_guids = []
        page = 1
        while True:

            try:
                content, content_type = \
                    self._get_content_and_type(url, harvest_job, page)
            except requests.exceptions.HTTPError as error:
                if error.response.status_code == 404:
                    if page > 1:
                        # Server returned a 404 after the first page, no more
                        # records
                        log.debug('404 after first page, no more pages')
                        break
                    else:
                        # Proper 404
                        msg = 'Could not get content. Server responded with ' \
                            '404 Not Found'
                        self._save_gather_error(msg, harvest_job)
                        return None
                else:
                    # This should never happen. Raising just in case.
                    raise

            if not content:
                return None

            try:

                batch_guids = []
                for guid, as_string in self._get_guids_and_datasets(content):

                    log.debug('Got identifier: {0}'
                              .format(guid.encode('utf8')))
                    batch_guids.append(guid)

                    if guid not in previous_guids:

                        if guid in guids_in_db:
                            # actually, does dataset need to be updated?


                            # Dataset needs to be updated
                            obj = HarvestObject(
                                guid=guid, job=harvest_job,
                                package_id=guid_to_package_id[guid],
                                content=as_string,
                                extras=[HarvestObjectExtra(key='status',
                                                           value='change')])
                        else:
                            # Dataset needs to be created
                            obj = HarvestObject(
                                guid=guid, job=harvest_job,
                                content=as_string,
                                extras=[HarvestObjectExtra(key='status',
                                                           value='new')])
                        obj.save()
                        ids.append(obj.id)

                if len(batch_guids) > 0:
                    guids_in_source.extend(set(batch_guids)
                                           - set(previous_guids))
                else:
                    log.debug('Empty document, no more records')
                    # Empty document, no more ids
                    break

            except ValueError as e:
                msg = 'Error parsing file: {0}'.format(str(e))
                self._save_gather_error(msg, harvest_job)
                return None

            if sorted(previous_guids) == sorted(batch_guids):
                # Server does not support pagination or no more pages
                log.debug('Same content, no more pages')
                break

            page = page + 1

            previous_guids = batch_guids

        # Check datasets that need to be deleted
        guids_to_delete = set(guids_in_db) - set(guids_in_source)
        for guid in guids_to_delete:
            obj = HarvestObject(
                guid=guid, job=harvest_job,
                package_id=guid_to_package_id[guid],
                extras=[HarvestObjectExtra(key='status', value='delete')])
            ids.append(obj.id)
            model.Session.query(HarvestObject).\
                filter_by(guid=guid).\
                update({'current': False}, False)
            obj.save()

        return ids


    def import_stage(self, harvest_object):
        log.debug('In Ontario Geohub Harvester import_stage')
        if not harvest_object:
            log.error('No harvest object received')
            return False

        if self.force_import:
            status = 'change'
        else:
            status = self._get_object_extra(harvest_object, 'status')

        if status == 'delete':
            # Don't delete package quite yet. we'll have to manually delete it later
            context = {'model': model, 'session': model.Session,
                       'user': self._get_user_name()}

            p.toolkit.get_action('package_delete')(
                context, {'id': harvest_object.package_id})
            log.info('Deleted package {0} with guid {1}'
                     .format(harvest_object.package_id, harvest_object.guid))

            # what we need here is something to notify opendata@ontario.ca that we're deleting 
            return True

        if harvest_object.content is None:
            self._save_object_error(
                'Empty content for object %s' % harvest_object.id,
                harvest_object, 'Import')
            return False

        # Get the last harvested object (if any)
        previous_object = model.Session.query(HarvestObject) \
            .filter(HarvestObject.guid == harvest_object.guid) \
            .filter(HarvestObject.current == True) \
            .first()

        # Flag previous object as not current anymore
        if previous_object and not self.force_import:
            previous_object.current = False
            previous_object.add()


        package_dict, geohub_dict = self._get_package_dict(harvest_object)
        if not package_dict:
            return False


        if not package_dict.get('name'):
            package_dict['name'] = \
                self._get_package_name(harvest_object, package_dict['title_translated']['en'])

        # copy across resource ids from the existing dataset, otherwise they'll
        # be recreated with new ids

        if status == 'change':
            existing_dataset = self._get_existing_dataset(harvest_object.guid)
            if existing_dataset:
                copy_across_resource_ids(existing_dataset, package_dict)


        # Unless already set by an extension, get the owner organization (if
        # any) from the harvest source dataset
        
        context = {
            'user': self._get_user_name(),
            'return_id_only': True,
            'ignore_auth': True,
        }

        # Flag this object as the current one
        harvest_object.current = True
        harvest_object.add()

        try:
            if status == 'new':
                package_schema = logic.schema.default_create_package_schema()
                context['schema'] = package_schema

                # We need to explicitly provide a package 

                package_dict['id'] = self.geohub_identifier_from_url(geohub_dict['identifier'])
                if 'extras' not in package_dict:
                    package_dict['extras'] = []    
                package_dict['extras'].append(
                    { 
                        "key": "guid",
                        "value": geohub_dict['identifier']
                    })
                package_schema['id'] = [unicode]

                # Save reference to the package on the object
                harvest_object.package_id = package_dict['id']
                harvest_object.add()

                # Defer constraints and flush so the dataset can be indexed with
                # the harvest object id (on the after_show hook from the harvester
                # plugin)
                model.Session.execute(
                    'SET CONSTRAINTS harvest_object_package_id_fkey DEFERRED')
                model.Session.flush()

            elif status == 'change':
                package_dict['id'] = harvest_object.package_id

            if status in ['new', 'change']:
                action = 'package_create' if status == 'new' else 'package_update'
                message_status = 'Created' if status == 'new' else 'Updated'

                package_id = p.toolkit.get_action(action)(context, package_dict)
                log.info('%s dataset with id %s', message_status, package_id)

        except Exception as e:
            dataset = json.loads(harvest_object.content)
            dataset_name = dataset.get('name', '')

            self._save_object_error('Error importing dataset %s: %r / %s' % (dataset_name, e, traceback.format_exc()), harvest_object, 'Import')
            return False

        finally:
            model.Session.commit()

        return True


def copy_across_resource_ids(existing_dataset, harvested_dataset):
    '''Compare the resources in a dataset existing in the CKAN database with
    the resources in a freshly harvested copy, and for any resources that are
    the same, copy the resource ID into the harvested_dataset dict.
    '''
    # take a copy of the existing_resources so we can remove them when they are
    # matched - we don't want to match them more than once.
    existing_resources_still_to_match = \
        [r for r in existing_dataset.get('resources')]

    # we match resources a number of ways. we'll compute an 'identity' of a
    # resource in both datasets and see if they match.
    # start with the surest way of identifying a resource, before reverting
    # to closest matches.
    resource_identity_functions = [
        lambda r: r['uri'],  # URI is best
        lambda r: (r['url'], r['title'], r['format']),
        lambda r: (r['url'], r['title']),
        lambda r: r['url'],  # same URL is fine if nothing else matches
    ]

    for resource_identity_function in resource_identity_functions:
        # calculate the identities of the existing_resources
        existing_resource_identities = {}
        for r in existing_resources_still_to_match:
            try:
                identity = resource_identity_function(r)
                existing_resource_identities[identity] = r
            except KeyError:
                pass

        # calculate the identities of the harvested_resources
        for resource in harvested_dataset.get('resources'):
            try:
                identity = resource_identity_function(resource)
            except KeyError:
                identity = None
            if identity and identity in existing_resource_identities:
                # we got a match with the existing_resources - copy the id
                matching_existing_resource = \
                    existing_resource_identities[identity]
                resource['id'] = matching_existing_resource['id']
                # make sure we don't match this existing_resource again
                del existing_resource_identities[identity]
                existing_resources_still_to_match.remove(
                    matching_existing_resource)
        if not existing_resources_still_to_match:
            break

today = datetime.datetime.now()
today_iso = today.strftime("%Y-%m-%d")

# pattens for digging around in the ontario geohub description
geohub_contact_pattern = re.compile("\*\*Contact(?:[\*\s\n]*)([a-zA-Z0-9&\(\)\/\. \-,\s\n@ \]\[]*)(?:\s*)(?:\n*)\[([\na-zA-Z0-9\.]*@[oO]ntario.ca)\]")
geohub_fr_contact_pattern = re.compile(u"\*\*Personne-resource(?:[\*\s\n]*)([\u00A0-\u017Fa-zA-Z0-9&\(\)\/\. \-,\s\n@ \]\[]*)(?:\s*)(?:\n*)\[([\na-zA-Z0-9\.]*@[oO]ntario.ca)\]")
ontario_email_pattern = re.compile("[a-zA-Z0-9\.]*@[oO]ntario.ca")
iso_date_pattern = re.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}")
geohub_update_frequency_pattern = re.compile("\*\*Maintenance and Update Frequency(?:[\s\n]*)\*\*(?:[\s\n]*)([a-zA-Z0-9 ]*):")

''' calls_to_infogo hold previous calls to infogo in the same harvest/session
        so that we don't make multiples of the same call
'''
calls_to_infogo = {}

''' ministries is used to look for mention of ministries in the body of the english 
        description to determine what ministry the dataset belongs to.
'''
ministries = {
    "Ontario Ministry of Natural Resources and Forestry" : "northern-development-mines-natural-resources-and-forestry",
    #"Ontario Ministry of Natural Resources" : "natural-resources-and-forestry",
    "Ontario Ministry of Children, Community and Social Services" : "children-community-and-social-services",
    "Ontario Ministry of Health" : "health",
    "Ontario Ministry of Long-term care" : "long-term-care",
    "Ontario Ministry of Government and Consumer Services" : "government-and-consumer-services",
    "Ontario Ministry of Environment, Conservation and Parks" : "environment-conservation-and-parks",
    "Ontario Ministry of Energy, Northern Development and Mines" : "northern-development-mines-natural-resources-and-forestry",
    "Ontario Ministry of Municipal Affairs and Housing" : "municipal-affairs-and-housing",
    "Ontario Ministry of Education" : "education",
    "Ontario Ministry of Agriculture Food and Rural Affairs" : "agriculture-food-and-rural-affairs",
    "Ontario Ministry of Transportation" : "transportation"
}

''' geohub_metadata_ministry_names maps the terms that show up in geohub's
        metadata to the corresponding organization_name in the catalogue
'''
geohub_metadata_ministry_names = {
    "Ontario Ministry of Natural Resources and Forestry" : "northern-development-mines-natural-resources-and-forestry",
    "Ontario Ministry of Agriculture, Food and Rural Affairs" : "agriculture-food-and-rural-affairs",
    "Ontario Ministry of the Environment, Conservation and Parks" : "environment-conservation-and-parks",
    "Ontario Ministry of Transportation" : "transportation",
    "Ontario Ministry of Health" : "health",
    "Ontario Ministry of Education" : "education",
    "Ontario Ministry of Municipal Affairs and Housing" : "municipal-affairs-and-housing",
    "Ontario Ministry of Natural Resources and Forestry - Provincial Mapping Unit" : "northern-development-mines-natural-resources-and-forestry",
    "Ontario Ministry of Indigenous Affairs": "indigenous-affairs",
    "Ontario Ministry of Energy, Northern Development and Mines" : "northern-development-mines-natural-resources-and-forestry"    
}

''' infogo_ministry_names maps the ministry labels in infogo to the 
        corresponding organization_name in the catalogue
'''
infogo_ministry_names = {
    "Agriculture, Food and Rural Affairs" : "agriculture-food-and-rural-affairs",
    "Attorney General" : "attorney-general",
    "Cabinet Office" : "cabinet-office",
    "Children, Community and Social Services" : "children-community-and-social-services",
    "Colleges and Universities" : "colleges-and-universities",
    "Economic Development, Job Creation and Trade" : "economic-development-job-creation-and-trade",
    "Education" : "education",
    "Energy, Northern Development and Mines" : "northern-development-mines-natural-resources-and-forestry",
    "Environment, Conservation and Parks" : "environment-conservation-and-parks",
    "Finance" : "finance",
    "Francophone Affairs" : "francophone-affairs",
    "Government and Consumer Services" : "government-and-consumer-services",
    "Health" : "health",
    "Heritage, Sport, Tourism and Culture Industries" : "heritage-sport-tourism-and-culture-industries",
    "Indigenous Affairs" : "indigenous-affairs",
    "Infrastructure" : "infrastructure",
    "Intergovernmental Affairs" : "intergovernmental-affairs",
    "Labour, Training and Skills Development" : "labour-training-and-skills-development",
    "Long-Term Care" : "long-term-care",
    "Municipal Affairs and Housing" : "municipal-affairs-and-housing",
    "Natural Resources and Forestry" : "northern-development-mines-natural-resources-and-forestry",
    "Seniors and Accessibility" : "seniors-and-accessibility",
    "Solicitor General" : "solicitor-general",
    "Transportation" : "transportation",
    "Treasury Board Secretariat" : "treasury-board-secretariat"
}

publisher_ministries = {
    "Ontario Ministry of Agriculture, Food and Rural Affairs" : "agriculture-food-and-rural-affairs",
    "Ontario Ministry of Natural Resources and Forestry" : "northern-development-mines-natural-resources-and-forestry",
    "OMAFRA" : "agriculture-food-and-rural-affairs",
    "Ontario Ministry of Energy, Northern Development and Mines" : "northern-development-mines-natural-resources-and-forestry",
    "Ontario Ministry of Municipal Affairs and Housing" : "municipal-affairs-and-housing",
    "Ontario Ministry of the Environment, Conservation and Parks" : "environment-conservation-and-parks",
    "Ontario Ministry of Natural Resources and Forestry - Provincial Mapping Unit" : "northern-development-mines-natural-resources-and-forestry",
    "Ontario Ministry of Health" : "health",
    "Ontario Ministry of Education" : "education",
    "Ontario Ministry of Indigenous Affairs" : "indigenous-affairs",
    "Ontario Ministry of Northern Development, Mines, Natural Resources and Forestry" : "northern-development-mines-natural-resources-and-forestry",
    "Ontario Ministry of Transportation" : "transportation"
}


def get_org_id(organization_name):  
    ''' return the local org id that matches the organization name
    '''   
    org = model.Group.by_name(organization_name)
    if org:
        return org.id
    return False


def call_to_infogo(email):
    if email not in calls_to_infogo:
        infogo_request = requests.get("http://www.infogo.gov.on.ca/infogo/v1/individuals/search?&keywords={}".format(email))
        calls_to_infogo[email] = infogo_request.json()
    return calls_to_infogo[email]

''' update_frequencies is all the update frequencies that appear in the
        description of a dataset on geohub mapped to catalogue update frequency values 
'''
update_frequencies = {
    "Irregular": "periodically",
    "Continual": "current",
    "Annually": "yearly",
    "Unknown": "other",
    "Weekly": "weekly",
    "Monthly": "monthly",
    "Fortnightly": "fortnightly",
    "Quarterly": "quarterly",
    "Biannually": "biannually",
    "As needed": "as_required",
    "On going": "as_required",
    "Not planned": "never",
    "As Needed": "as_required"
}

def extract_update_frequency(description):
    '''
    Geohub records often have an update frequency in their description.

    It looks like this:

    Maintenance and Update Frequency
    As needed: data is updated as deemed necessary

    We're using regular expressions to peel out any update frequency in the english description
    '''
    search_results = geohub_update_frequency_pattern.findall(description)
    if len(search_results) > 0:
        return search_results[0].strip()
    else:
        return None


geohub_description_fr_ministry_names = {
    "Ministère des Richesses naturelles et des Forêts de l'Ontario": "natural-resources-and-forestry",
    "Ministère de l'Agriculture, de l'Alimentation et des Affaires rurales de l'Ontario": "agriculture-food-and-rural-affairs",
    "Ministère des Richesses naturelles et des Forêts": "natural-resources-and-forestry",
    "Ministère de l’Environnement, de la Protection de la nature et des Parcs de l'Ontario": "environment-conservation-and-parks",    
    "Ministère de l’Environnement, de la Protection de la nature et des Parcs": "environment-conservation-and-parks",
    "Ministère des Richesses naturelles": "natural-resources-and-forestry",
    "Ministère de l’Énergie, Développement du Nord et Mines": "energy-northern-development-and-mines"
}


def extract_fr_contact_info(description):
    ''' In order to get maintainer_name in french (we already know email and ministry),
            we extract french contact info (then strip out email and ministry and use
            the rest as the maintainer name)

    '''
    search_results = geohub_contact_pattern.findall(description)
    if len(search_results) > 0:
        contact_info = search_results[0]
        # split into maintainer name, ministry, branch, email
        contact_info_dict = {
            "maintainer_email" : contact_info[1]
        }
        non_email_contact_info = contact_info[0].replace("\n"," ").replace("  "," ")
        for ministry in geohub_description_fr_ministry_names.keys():
            ministry_pattern = re.compile("("+ministry+"[\s\n-,.]*)")
            look_for_ministry = ministry_pattern.findall(non_email_contact_info, re.IGNORECASE)
            if len(look_for_ministry) > 0:
                ministry_result = look_for_ministry[0]
                # there's a ministry name in there. let's take it out and use the rest as a maintainer name
                non_email_contact_info = non_email_contact_info.replace(ministry_result[0], "").strip()
                contact_info_dict['ministry'] = geohub_description_fr_ministry_names[ministry.strip()]
                break
            if non_email_contact_info.lower().find("direction") != -1:
                contact_info_chunks = non_email_contact_info.split(",")
                for chunk in contact_info_chunks:
                    if chunk.lower().find("direction") != -1:
                       contact_info_dict['maintainer_branch'] = chunk
                       break  
        contact_info_dict['maintainer_name'] = non_email_contact_info.strip()
        if contact_info_dict['maintainer_name'][-1] in ["-",","]:
            contact_info_dict['maintainer_name'] = contact_info_dict['maintainer_name'][:-1].strip() 
        return contact_info_dict
    else:
        return None


geohub_description_ministry_names = {
    "Ontario Ministry of Natural Resources and Forestry": "natural-resources-and-forestry",
    "Ontario Ministry of Agriculture, Food and Rural Affairs": "agriculture-food-and-rural-affairs",
    "Ontario Ministry of the Environment, Conservation and Parks": "environment-conservation-and-parks",
    "Ontario Ministry of Natural Resources": "natural-resources-and-forestry",
    "Ministry of Natural Resources and Forestry": "natural-resources-and-forestry",
    "Ministry of the Environment Conservation and Parks": "environment-conservation-and-parks",
    "Ministry of the Environment, Conservation and Parks": "environment-conservation-and-parks",
    "Ministry of Energy, Northern Development and Mines": "energy-northern-development-and-mines",
    "Ministry of Environment, Conservation and Parks" : "environment-conservation-and-parks",
    "Ministry of Health and Long-Term Care (MOHLTC)": "health"
}


def extract_contact_info(description):
    search_results = geohub_contact_pattern.findall(description)
    if len(search_results) > 0:
        contact_info = search_results[0]
        # split into maintainer name, ministry, branch, email
        contact_info_dict = {
            "maintainer_email" : contact_info[1].strip()
        }
        non_email_contact_info = contact_info[0].replace("\n"," ").replace("  "," ")
        for ministry in geohub_description_ministry_names.keys():
            ministry_pattern = re.compile("("+ministry+"[\s\n-,.]*)")
            look_for_ministry = ministry_pattern.findall(non_email_contact_info, re.IGNORECASE)
            if len(look_for_ministry) > 0:
                # there's a ministry name in there. let's take it out and use the rest as a maintainer name
                non_email_contact_info = non_email_contact_info.replace(look_for_ministry[0], "").strip()
                contact_info_dict['ministry'] = geohub_description_ministry_names[ministry.strip()]
                break
            if non_email_contact_info.lower().find("branch") != -1:
                contact_info_chunks = non_email_contact_info.split(",")
                for chunk in contact_info_chunks:
                    if chunk.lower().find("branch") != -1:
                       contact_info_dict['maintainer_branch'] = chunk
                       break  
        contact_info_dict['maintainer_name'] = non_email_contact_info.strip()
        if contact_info_dict['maintainer_name'][-1] in ["-",","]:
            contact_info_dict['maintainer_name'] = contact_info_dict['maintainer_name'][:-1].strip()
        return contact_info_dict
    else:
        return None


def extract_date(date_str):
    search_results = iso_date_pattern.findall(date_str)
    if len(search_results) > 0:
        return search_results[0]
    else:
        return None


def publisher_ministry(geohub_dict):
    if "publisher" in geohub_dict:
        if geohub_dict['publisher'].get("name", False) in publisher_ministries:
            return publisher_ministries[geohub_dict['publisher']['name']]
    return False

def extract_ministry(description, email):
    for ministry_search_text, ministry_name in ministries.items():
        if description.find(ministry_search_text):
            return ministry_name

    infogo_response = call_to_infogo(email)
    if 'individuals' in infogo_response:
        for individual_record in infogo_response['individuals']:
            if individual_record['topOrgName'] in infogo_ministry_names:
                return infogo_ministry_names[individual_record['topOrgName']]
    else:
        return "natural-resources-and-forestry"


def extract_ontario_email(description):
    search_results = ontario_email_pattern.findall(description)
    if len(search_results) > 0:
        return search_results[0]
    else:
        return None


def get_ontario_employee_name(email):
    return " ".join(list(map(lambda x: x.capitalize(), re.sub(r'[0-9]+', '', email).replace("@ontario.ca","").split(".", 1))))
    # request timing out right now. reenable this later
    infogo_response = call_to_infogo(email)
    if infogo_response['total'] > 0:
        calls_to_infogo[email] = infogo_response
        return " ".join(list(map(lambda x: infogo_response['individuals'][0][x] if x in infogo_response['individuals'][0] else "", ["firstname", "middleName","lastName"])))
    else:
        return " ".join(list(map(lambda x: x.capitalize(), re.sub(r'[0-9]+', '', email).replace("@ontario.ca","").split(".", 1))))


def french_notes(french_xml):
    '''Returns the french notes from the xml response.
    <dataIdInfo><idAbs>
    '''
    french_notes_text = 'Placeholder'

    root = french_xml
    #root = lxml.etree.fromstring(french_xml.content)
    french_notes_element = root.xpath("//dataIdInfo/idAbs")
    if french_notes_element:
        french_notes_text = french_notes_element[0].text

    return french_notes_text


def french_title(french_xml):
    '''Returns the french title from the xml response.
    <dataIdInfo><idCitation><resTitle>
    '''
    french_title_text = 'Placeholder'

    root = french_xml
    #root = lxml.etree.fromstring(french_xml.content)
    french_title_element = root.xpath("//dataIdInfo/idCitation/resTitle")
    if french_title_element:
        french_title_text = french_title_element[0].text

    return french_title_text


def french_keywords(french_xml):
    '''Returns array of french keywords from the xml response.
    searchKeys matches data.json keywords that are used for english record.
    '''

    french_keywords = []

    root = french_xml
    #root = lxml.etree.fromstring(french_xml.content)
    french_keywords_element = root.xpath("//searchKeys")
    if french_keywords_element:
        for keyword in french_keywords_element[0]:
            french_keywords.append(keyword.text)
      
    return french_keywords


def get_license_from_xml(root):
    '''Returns the license for that dataset.
    '''
    license_path = root.xpath("//dataIdInfo/resConst/LegConsts/useLimit")
    if license_path:
        license_text = license_path[0].text
        return license_text
    return False

def get_backup_description_from_xml(root):
    '''Returns the revise date (comparable to data_range_end) for that dataset.
    '''
    desc_path = root.xpath("//dataIdInfo/idPurp")
    if desc_path:
        desc_text = desc_path[0].text
        if desc_text:
            return desc_text
    return False

def get_revise_date_from_xml(root):
    '''Returns the revise date (comparable to data_range_end) for that dataset.
    '''
    revise_date_path = root.xpath("//dataIdInfo/idCitation/date/reviseDate")
    if revise_date_path:
        revise_date_text = revise_date_path[0].text
        revise_date = extract_date(revise_date_text)
        if revise_date:
            return revise_date
    return False


def get_create_date_from_xml(root):
    '''Returns the create date (comparable to data_range_start) for that dataset.
    '''
    create_date_path = root.xpath("//dataIdInfo/idCitation/date/createDate")
    if create_date_path:
        create_date_text = create_date_path[0].text
        create_date = extract_date(create_date_text)
        if create_date:
            return create_date
    return False


def get_ministry_from_xml(root):
    '''Returns the license for that dataset.
    '''
    ministry_path = root.xpath("//dataIdInfo/idCitation/citRespParty/rpOrgName")
    if ministry_path:
        ministry = ministry_path[0].text
        if ministry in geohub_metadata_ministry_names:
            return geohub_metadata_ministry_names[ministry]
    return False

def get_file_type(resource):
    '''
        Returns the file format of a resource.
    '''
    if 'format' in resource:
        return resource['format']
    elif 'mediaType' in resource:
        return resource['mediaType']
    elif resource.get("accessURL", False):
        import urlparse, os
        path = urlparse.urlparse(resource.get("accessURL", False)).path
        ext = os.path.splitext(path)[1]
        return ext
    return False

def build_resources(distribution, id, english_xml, dataset_url):
    ''' Harvest all resources/files for the dataset
    '''
    metadata_titles = ["ArcGIS Hub Dataset","Esri Rest API"]
    resources = []

    for resource in distribution:
        resource_dict = { 
                    "name_translated": {
                        "en": resource["title"],
                        "fr": resource["title"]
                    },
                    "type": 'data',
                    "url": resource.get("accessURL", "") }
        revise_date = get_revise_date_from_xml(english_xml)
        if revise_date:
            resource_dict['data_last_updated'] = revise_date
            resource_dict['data_range_end'] = revise_date
        create_date = get_create_date_from_xml(english_xml)
        if create_date:
            resource_dict['data_range_start'] = create_date
        file_type = get_file_type(resource)
        if file_type:
            resource_dict['format'] = file_type
        if resource["title"] in metadata_titles:
            resource_dict['type'] = "metadata"
        if resource["title"] is None:
            resource_dict['name_translated'] = {
                "en": "Resource",
                "fr": "Ressource"
                }
        resources.append(
                    resource_dict
                  ) # Some resources are missing links


    # Add in the metadata URLs
    resources.append(
                  { 
                    "name_translated": {
                        "en": "Metadata in ISO 19115 NAP Format",
                        "fr": "Métadonnées dans ISO 19115"
                        },
                    "type": 'technical_document',
                    "format": "html",
                    "url": "https://www.arcgis.com/sharing/rest/content/items/{}/info/metadata/metadata.xml?format=default&output=html".format(id) })
    resources.append(
                  { 
                    "name_translated": {
                        "en": "Metadata in Full Esri Format",
                        "fr": "Métadonnées au format ESRI"
                      },
                    "type": 'technical_document',
                    "format": "xml",
                    "url": metadata_url(id) })

    # Include resources from XML, putting them first.
    additional_resources = additional_resources_from_xml(english_xml)
    resource_links = list(map(lambda x: x['url'], resources))
    for r in additional_resources:
        if r['url'] not in resource_links:
            resources.append(r)

    return resources


def geohub_french_id_from_xml(english_id):
    '''Return the french id from the english xml or empty string if not record.
    It's only available in the ?format=default version, so a seperate call.
    '''

    # Prime for no French ID.
    geohub_french_record_id_text = ''

    # Get resources from XML.
    metadata_xml_request = requests.get(metadata_url(english_id))
    # parse the response.
    root = lxml.etree.fromstring(metadata_xml_request.content)

    # Get the element then grab the text.
    
    # this works if using xml?format=default which I thought I had to use to access the ID value but turns out I don't. this also required namespacing.
    #geohub_french_record_id_element = root.xpath("//default:MD_Identifier[default:authority/default:CI_Citation/default:title/gco:CharacterString/text() = 'Ontario GeoHub French Record ID']/default:code/gco:CharacterString", namespaces=ns)
    geohub_french_record_id_element = root.xpath("//citId[identAuth/resTitle/text() = 'Ontario GeoHub French Record ID']/identCode")
    if geohub_french_record_id_element:
        geohub_french_record_id_text = geohub_french_record_id_element[0].text

    return geohub_french_record_id_text



def identifier_from_url(identifier_url):
    '''Accepts a string of the identifier URL that's part of data.json for 
    each dataset/record, and parses into just ID.
    '''
    # ID is at the end but sometimes there's extra bits we dont want that are
    # the underlying layer index.
    identifier = identifier_url.split('/')[-1].split('_')[0]
    return identifier


def identifier_from_url_with_index(identifier_url):
    '''Returns a string id with the layer index if it exists.
    '''
    identifier = identifier_url.split('/')[-1] # keep layer index.
    return identifier

def metadata_url(id):
    '''Returns a url for the metadata XML.
    '''
    return "https://www.arcgis.com/sharing/rest/content/items/{}/info/metadata/metadata.xml".format(id)


def additional_resources_from_xml(root):
    '''Returns array of dicts for additional resources.
    '''
    additional_resources = []
    for onLineSrc in root.iter('onLineSrc'):
        # Some datasets/records don't have additional resources so setting 
        # default values. They seem to use the data source instead without a name.
        additional_resources.append(
            {"url": onLineSrc.findtext('linkage'),
             "name_translated": {
                "en": onLineSrc.findtext('orName',
                                        default=onLineSrc.findtext('linkage')),
                "fr": onLineSrc.findtext('orName',
                                        default=onLineSrc.findtext('linkage'))
            },
             "type": 'data'}
            )
    return additional_resources

def english_metadata_xml_response(english_identifier):
    '''Returns the english metadata xml
    '''

    english_id = identifier_from_url(english_identifier)
    english_metadata_url = metadata_url(english_id)
    metadata_xml_request = requests.get(english_metadata_url)
    # parse the response to get the additional resources.
    root = lxml.etree.fromstring(metadata_xml_request.content)
    return root

def french_metadata_xml_response(english_identifier):
    '''Returns the french metadata xml.
    To build this we need to grab the french values for some fields. Easiest
    so far is to loop over english and make a call to the matching french
    record. This will be used for a few payload values so calling once here.
    '''

    english_id = identifier_from_url(english_identifier)
    french_id = geohub_french_id_from_xml(english_id)
    french_id = identifier_from_url(french_id)
    french_metadata_xml_url = metadata_url(french_id)
    # Now can make request for xml.
    french_xml_response = requests.get(french_metadata_xml_url)

    try:
        # TODO: fix bug.  if geohub_french_id_from_xml: continue on, else abort french and use defaults. in some cases there is an ID but the request fails (outdated data I think). In this case it tries to parse the html I think and uses the defaults (den-site is an example).
        # TODO: Error handle for non-existent French record.
        french_xml_root = lxml.etree.fromstring(french_xml_response.content)
    except lxml.etree.XMLSyntaxError as e:
        logging.warning('Exception raised. Cannot parse response for english_id: {} and french_id: {}, likely not XML. Using empty root element instead. {}'
            .format(english_id, french_id, repr(e)))
        # Create an empty root element 
        french_xml_root = lxml.etree.Element("root")

    return french_xml_root