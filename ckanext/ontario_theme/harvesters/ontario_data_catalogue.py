# -*- coding: utf-8 -*-

import six
import requests 

from ckan import model
from ckan.model import Session
from ckanext.harvest.harvesters.ckanharvester import CKANHarvester

from ckan import plugins as p
from ckan.logic.schema import default_create_package_schema
from ckan.lib.navl.validators import ignore_missing, ignore
from sqlalchemy import exists
from sqlalchemy.sql import update, bindparam

import logging
log = logging.getLogger(__name__)

class OntarioDataCatalogueHarvester(CKANHarvester):

    def info(self):
        return {
            'name': 'ontario_data_catalogue',
            'title': 'Ontario Data Catalogue',
            'description': 'Harvester for Ontario Data Catalogue' +
                           'to pull into the internal data catalogue.'
        }

    def gather_stage(self, harvest_job):
        # make sure we have all the right organizations

        url = harvest_job.source.url     

        session = requests.Session()
        r = session.get("{}/api/action/organization_list".format(url))
        if r.json()["success"]:
            remote_organizations = r.json()['result']
            local_organizations = model.Group.all("organization")
            local_organization_names = [org.name for org in local_organizations]
            for remote_org in remote_organizations:
                if remote_org not in local_organization_names:
                    context = {
                        'model': model,
                        'session': Session,
                        'user': self._get_user_name(),
                        'ignore_auth': True,
                    }
                    session = requests.Session()
                    r = session.get("{}/api/action/organization_show?id={}".format(url, remote_org))
                    if r.json()["success"]:
                        remote_organization = r.json()['result']
                        new_package = p.toolkit.get_action("organization_create")(context, remote_organization) 

        return CKANHarvester.gather_stage(self, harvest_job)

    def _create_or_update_package(self, package_dict, harvest_object,
                                  package_dict_form='rest'):
        '''
        Creates a new package or updates an existing one according to the
        package dictionary provided.
        '''
        assert package_dict_form in ('rest', 'package_show')
        try:
            # Change default schema
            schema = default_create_package_schema()
            schema['id'] = [ignore_missing, six.text_type]
            schema['__junk'] = [ignore]

            # Check API version
            if self.config:
                try:
                    api_version = int(self.config.get('api_version', 2))
                except ValueError:
                    raise ValueError('api_version must be an integer')
            else:
                api_version = 2

            user_name = self._get_user_name()
            context = {
                'model': model,
                'session': Session,
                'user': user_name,
                'api_version': api_version,
                'schema': schema,
                'ignore_auth': True,
            }

            if self.config and self.config.get('clean_tags', False):
                tags = package_dict.get('tags', [])
                package_dict['tags'] = self._clean_tags(tags)

            # Check if package exists
            try:
                # _find_existing_package can be overridden if necessary
                existing_package_dict = self._find_existing_package(package_dict)

                # In case name has been modified when first importing. See issue #101.
                package_dict['name'] = existing_package_dict['name']

                # Check modified date
                if 'metadata_modified' not in package_dict or \
                   package_dict['metadata_modified'] > existing_package_dict.get('metadata_modified') or package_dict['name'] == "status-of-covid-19-cases-in-ontario-by-public-health-unit-phu" or package_dict['id'] == 'ecb75ea0-8b72-4f46-a14a-9bd54841d6ab':
                    log.info('Package with GUID %s exists and needs to be updated' % harvest_object.guid)
                    # Update package
                    context.update({'id': package_dict['id']})
                    package_dict.setdefault('name',
                                            existing_package_dict['name'])

                    '''
                    	what we want to do here is
                    		- not overwrite maintainer name or maintainer email or maintainer branch with blank information
                    		- not include resources because it will overwrite the existing resources
                            - match owner_org
                            - not overwrite all keywords (just add)
                    '''

                    package_dict['keywords'] = {
                        "en" : list(set(existing_package_dict['keywords']['en'] + package_dict['keywords']['en'])),
                        "fr" : list(set(existing_package_dict['keywords']['fr'] + package_dict['keywords']['fr']))
                    }
                    package_dict['owner_org'] = package_dict['organization']['name']
                    package_dict['harvester'] = "ontario-data-catalogue"
                    if package_dict.get("maintainer_email", "") == "":
                    	del package_dict['maintainer_email']
                    if "maintainer_translated" in package_dict:
                        if package_dict['maintainer_translated'].get("en","") == "" and package_dict['maintainer_translated'].get("fr","") == "":
                    	    del package_dict['maintainer_translated']
                        elif package_dict['maintainer_translated'].get("en","") != "" and package_dict['maintainer_translated'].get("fr","") == "":
                            package_dict['maintainer_translated']['fr'] = package_dict['maintainer_translated']['en'] 
                        elif package_dict['maintainer_translated'].get("en","") == "" and package_dict['maintainer_translated'].get("fr","") != "":
                            package_dict['maintainer_translated']['en'] = package_dict['maintainer_translated']['fr'] 
                    if "maintainer_branch" in package_dict:
                    	if package_dict['maintainer_branch'].get("en","") == "" and package_dict['maintainer_branch'].get("fr","") == "":
                    		del package_dict['maintainer_branch']

                    if 'resources' in package_dict:
                        for resource in package_dict['resources']:
                            resource.update({"harvested_resource" : True})
                            resource_context = {
                                'model': model,
                                'session': Session,
                                'user': user_name,
                                'api_version': api_version,
                                'id' : resource['id'],
                                'ignore_auth': True,
                            }
                            p.toolkit.get_action("resource_patch" if resource['id'] in list(map(lambda x: x["id"], existing_package_dict["resources"])) else "resource_create")(resource_context, resource)
                        list_of_remote_resources = list(map(lambda x: x["id"],package_dict["resources"]))
                        for resource in list(filter(lambda x: x["harvested_resource"] == True, existing_package_dict["resources"])):
                            # if there's a harvested resource locally that isn't in the latest harvested list of resources, delete it
                            if resource['id'] not in list_of_remote_resources:
                                resource_context = {
                                    'model': model,
                                    'session': Session,
                                    'user': user_name,
                                    'api_version': api_version,
                                    'id' : resource['id'],
                                    'ignore_auth': True,
                                }
                                p.toolkit.get_action("resource_delete")(resource_context, { 'id' : resource['id']})

                        del package_dict['resources']
                    new_package = p.toolkit.get_action("package_patch")(context, package_dict)

                else:
                    log.info('No changes to package with GUID %s, skipping...' % harvest_object.guid)
                    # NB harvest_object.current/package_id are not set
                    return 'unchanged'

                # Flag the other objects linking to this package as not current anymore
                from ckanext.harvest.model import harvest_object_table
                conn = Session.connection()
                u = update(harvest_object_table)\
                    .where(harvest_object_table.c.package_id == bindparam('b_package_id')) \
                    .values(current=False)
                conn.execute(u, b_package_id=new_package['id'])

                # Flag this as the current harvest object

                harvest_object.package_id = new_package['id']
                harvest_object.current = True
                harvest_object.save()

            except p.toolkit.ObjectNotFound:
                # Package needs to be created

                # Get rid of auth audit on the context otherwise we'll get an
                # exception
                context.pop('__auth_audit', None)

                # Set name for new package to prevent name conflict, see issue #117
                if package_dict.get('name', None):
                    package_dict['name'] = self._gen_new_name(package_dict['name'])
                else:
                    package_dict['name'] = self._gen_new_name(package_dict['title'])

                log.info('Package with GUID %s does not exist, let\'s create it' % harvest_object.guid)
                harvest_object.current = True
                harvest_object.package_id = package_dict['id']
                # Defer constraints and flush so the dataset can be indexed with
                # the harvest object id (on the after_show hook from the harvester
                # plugin)
                harvest_object.add()

                model.Session.execute('SET CONSTRAINTS harvest_object_package_id_fkey DEFERRED')
                model.Session.flush()

                package_dict['owner_org'] = package_dict['organization']['name']
                package_dict['harvester'] = "ontario-data-catalogue"
                for resource in package_dict['resources']:
                    resource.update({"harvested_resource" : True})

                if package_dict.get("maintainer_email", "") == "":
                    package_dict['maintainer_email'] = "opendata@ontario.ca"
                if "maintainer_translated" in package_dict:
                    if package_dict['maintainer_translated'].get("en","") == "" and package_dict['maintainer_translated'].get("fr","") == "":
                        package_dict['maintainer_translated'] = {
                            "en" : "Open Data",
                            "fr" : "Données ouvertes"
                        }
                    elif package_dict['maintainer_translated'].get("en","") != "" and package_dict['maintainer_translated'].get("fr","") == "":
                        package_dict['maintainer_translated']['fr'] = package_dict['maintainer_translated']['en'] 
                    elif package_dict['maintainer_translated'].get("en","") == "" and package_dict['maintainer_translated'].get("fr","") != "":
                        package_dict['maintainer_translated']['en'] = package_dict['maintainer_translated']['fr'] 
                else: 
                    package_dict['maintainer_translated'] = {
                        "en" : "Open Data",
                        "fr" : "Données ouvertes"
                    }
                new_package = p.toolkit.get_action(
                    'package_create' if package_dict_form == 'package_show'
                    else 'package_create_rest')(context, package_dict)

            Session.commit()

            return True

        except p.toolkit.ValidationError as e:
            log.exception(e)
            self._save_object_error('Invalid package with GUID %s: %r' % (harvest_object.guid, e.error_dict),
                                    harvest_object, 'Import')
        except Exception as e:
            log.exception(e)
            self._save_object_error('%r' % e, harvest_object, 'Import')

        return None